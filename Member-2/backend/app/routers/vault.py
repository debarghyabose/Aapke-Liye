"""
Vault APIs: household registration and document storage.
X-Household-Token works exactly like X-Claim-Token (shown once, cannot be recovered).
"""
import hashlib
import hmac

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from .. import storage
from ..db import get_db
from ..models import Household, VaultDocument, VAULT_DOC_TYPES, audit, now
from ..security import hash_token, limiter, new_claim_token
from ..uploads import PHOTO, read_upload, Kind, MB, sniff

router = APIRouter(tags=["vault"])

# Allow any binary upload for documents (PDF, images, etc.)
DOC_UPLOAD = Kind("document", 10 * MB,
                  frozenset({"application/pdf", "image/jpeg", "image/jpg", "image/png",
                             "image/webp", "application/octet-stream"}),
                  {"jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp",
                   "pdf": "application/pdf"})


def _sniff_doc(data: bytes) -> tuple[str, str]:
    """Detect format, returning (format, content_type). Falls back to PDF for unknown."""
    fmt = sniff(data)
    if fmt and fmt in DOC_UPLOAD.formats:
        return fmt, DOC_UPLOAD.formats[fmt]
    # Check for PDF
    if data[:5] == b"%PDF-":
        return "pdf", "application/pdf"
    # Fallback: treat as generic binary (octet-stream)
    return "bin", "application/octet-stream"


async def household_by_token(household_id: str,
                              x_household_token: str | None = Header(None),
                              db: AsyncSession = Depends(get_db)) -> Household:
    """The household, if X-Household-Token matches. Otherwise 404."""
    hh = await db.get(Household, household_id)
    if not hh or not x_household_token or not hmac.compare_digest(
            hh.token_hash, hash_token(x_household_token)):
        raise HTTPException(404, "Household not found")
    return hh


class HouseholdCreated(BaseModel):
    id: str
    household_token: str = Field(description="Shown once. Send it as X-Household-Token.")


class VaultDocOut(BaseModel):
    id: int
    doc_type: str
    filename_label: str
    content_type: str
    source: str

    model_config = {"from_attributes": True}


@router.post("/households", response_model=HouseholdCreated, status_code=201)
@limiter.limit("10/minute")
async def create_household(request: Request, db: AsyncSession = Depends(get_db)):
    token = new_claim_token()
    hh = Household(token_hash=hash_token(token))
    db.add(hh)
    await db.flush()
    audit(db, None, "household_created", actor="claimant", household_id=hh.id)
    await db.commit()
    return HouseholdCreated(id=hh.id, household_token=token)


@router.post("/households/{household_id}/documents", response_model=VaultDocOut, status_code=201)
@limiter.limit("30/minute")
async def upload_document(
    request: Request,
    doc_type: str = Form(..., max_length=60),
    file: UploadFile = File(...),
    household: Household = Depends(household_by_token),
    db: AsyncSession = Depends(get_db),
):
    if doc_type not in VAULT_DOC_TYPES:
        raise HTTPException(422, f"doc_type must be one of {sorted(VAULT_DOC_TYPES)}")
    # Read the file (up to 10 MB)
    data = await file.read(10 * MB + 1)
    if len(data) > 10 * MB:
        raise HTTPException(413, "Document is too large (max 10 MB)")
    if not data:
        raise HTTPException(422, "File is empty")
    _fmt, content_type = _sniff_doc(data)
    # For baseline_photo, validate it's actually an image
    if doc_type == "baseline_photo":
        fmt = sniff(data)
        if fmt not in PHOTO.formats:
            raise HTTPException(415, "baseline_photo must be an image (JPEG, PNG, or WebP)")
        content_type = PHOTO.formats[fmt]
    path = await storage.save("vault", data)
    label = f"{doc_type}_{household.id[:8]}"  # safe label, never client filename
    doc = VaultDocument(
        household_id=household.id, doc_type=doc_type, filename_label=label,
        path=path, content_type=content_type,
    )
    household.documents.append(doc)
    await db.flush()
    audit(db, None, "vault_document_uploaded", actor="claimant",
          household_id=household.id, doc_id=doc.id, doc_type=doc_type)
    await db.commit()
    return VaultDocOut.model_validate(doc)


@router.get("/households/{household_id}/documents", response_model=list[VaultDocOut])
async def list_documents(household: Household = Depends(household_by_token),
                         db: AsyncSession = Depends(get_db)):
    return [VaultDocOut.model_validate(d) for d in household.documents]


@router.delete("/households/{household_id}/documents/{doc_id}", status_code=204)
async def delete_document(doc_id: int,
                          household: Household = Depends(household_by_token),
                          db: AsyncSession = Depends(get_db)):
    doc = next((d for d in household.documents if d.id == doc_id), None)
    if not doc:
        raise HTTPException(404, "Document not found")
    await storage.delete(doc.path)
    await db.delete(doc)
    audit(db, None, "vault_document_deleted", actor="claimant",
          household_id=household.id, doc_id=doc.id, doc_type=doc.doc_type)
    await db.commit()


# ── DigiLocker (mock) ──────────────────────────────────────────────────────

@router.get("/households/{household_id}/digilocker/start")
async def digilocker_start(household: Household = Depends(household_by_token),
                           db: AsyncSession = Depends(get_db)):
    """Begin the DigiLocker consent flow. Mock mode shows a demo banner."""
    from ..services import digilocker
    return await digilocker.start(household.id)


@router.get("/digilocker/callback")
@limiter.limit("10/minute")
async def digilocker_callback(request: Request, household_id: str,
                               x_household_token: str | None = Header(None),
                               db: AsyncSession = Depends(get_db)):
    """Complete DigiLocker consent: adds sample docs to the vault with source=digilocker_mock."""
    hh = await db.get(Household, household_id)
    if not hh or not x_household_token or not hmac.compare_digest(
            hh.token_hash, hash_token(x_household_token)):
        raise HTTPException(404, "Household not found")
    from ..services import digilocker
    docs = await digilocker.callback(hh.id)
    added = []
    for doc_info in docs:
        path = await storage.save("vault", doc_info["data"])
        label = f"{doc_info['doc_type']}_digilocker_demo"
        vd = VaultDocument(
            household_id=hh.id, doc_type=doc_info["doc_type"],
            filename_label=label, path=path,
            content_type=doc_info["content_type"],
            source=doc_info["source"],
        )
        hh.documents.append(vd)
        await db.flush()
        added.append(VaultDocOut.model_validate(vd))
    audit(db, None, "digilocker_callback", actor="claimant",
          household_id=hh.id, doc_types=[d.doc_type for d in added])
    await db.commit()
    return {"banner": "Demo: DigiLocker mock", "documents_added": added}
