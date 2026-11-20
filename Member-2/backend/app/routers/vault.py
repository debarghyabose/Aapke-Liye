"""
Document vault: a family saves its papers and a "before" photo of the house BEFORE a
disaster. POST /households returns a household_token, shown once, sent as the
X-Household-Token header (it works exactly like X-Claim-Token: wrong or missing -> 404).
A claim uses the vault through POST /claims/{id}/household.

DigiLocker (mock, clearly labelled "Demo"):
  1. GET /households/{id}/digilocker/start   (X-Household-Token) -> {"consent_url"}
  2. the app opens consent_url in the browser: a consent page with a "Demo" banner
  3. "Allow" -> GET /digilocker/callback -> sample Aadhaar + ration card added to the vault
     with source="digilocker_mock", then back to `return_to` (if it is an allowed origin)
"""
import html
import logging
from functools import lru_cache
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from .. import storage
from ..config import settings
from ..db import get_db
from ..models import Household, VaultDocument, audit
from ..schemas import UTCDateTime
from ..security import hash_token, household_for_owner, limiter, new_claim_token
from ..services import digilocker
from ..services.relief import load_proof_rules
from ..uploads import MB, sniff

log = logging.getLogger(__name__)
router = APIRouter(tags=["vault"])

MAX_DOC_BYTES = 10 * MB
MAX_DOCS_PER_HOUSEHOLD = 20
FORMATS = {"jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp",
           "pdf": "application/pdf"}
DEMO_BANNER = "Demo: DigiLocker mock"


@lru_cache
def vault_doc_types() -> frozenset[str]:
    """The document types in Member 5's proof_substitution.json, plus baseline_photo."""
    return frozenset(k for k, v in load_proof_rules().items() if isinstance(v, list)) | {
        "baseline_photo"}


class HouseholdCreated(BaseModel):
    household_id: str
    household_token: str = Field(description="Shown once. Send it as X-Household-Token. "
                                             "It cannot be recovered if lost.")


class VaultDocOut(BaseModel):
    id: int
    doc_type: str
    content_type: str
    source: str            # "upload" | "digilocker_mock" (show it as "DigiLocker (demo)")
    created_at: UTCDateTime
    file_url: str = ""

    model_config = {"from_attributes": True}


def _doc_out(d: VaultDocument) -> VaultDocOut:
    out = VaultDocOut.model_validate(d)
    out.file_url = f"/households/{d.household_id}/documents/{d.id}/file"
    return out


@router.post("/households", response_model=HouseholdCreated, status_code=201)
@limiter.limit(settings.rate_limit_create)
async def create_household(request: Request, db: AsyncSession = Depends(get_db)):
    token = new_claim_token()
    hh = Household(token_hash=hash_token(token), documents=[])
    db.add(hh)
    await db.flush()
    audit(db, None, "household_created", household_id=hh.id)
    await db.commit()
    return HouseholdCreated(household_id=hh.id, household_token=token)


@router.post("/households/{household_id}/documents", response_model=VaultDocOut,
             status_code=201)
@limiter.limit(settings.rate_limit_upload)
async def upload_document(request: Request, doc_type: str = Form(..., max_length=60),
                          file: UploadFile = File(...),
                          household: Household = Depends(household_for_owner),
                          db: AsyncSession = Depends(get_db)):
    """A photo or PDF of a document (JPEG, PNG, WebP or PDF, up to 10 MB), or a
    baseline_photo of the house/fields/livestock in normal times (image only)."""
    if doc_type not in vault_doc_types():
        raise HTTPException(422, f"doc_type must be one of {sorted(vault_doc_types())}")
    if len(household.documents) >= MAX_DOCS_PER_HOUSEHOLD:
        raise HTTPException(409, f"A vault can hold at most {MAX_DOCS_PER_HOUSEHOLD} documents")
    data = await file.read(MAX_DOC_BYTES + 1)
    if len(data) > MAX_DOC_BYTES:
        raise HTTPException(413, "The file is too large (max 10 MB)")
    fmt = "pdf" if data[:5] == b"%PDF-" else sniff(data)
    if fmt not in FORMATS or (doc_type == "baseline_photo" and fmt == "pdf"):
        raise HTTPException(415, "Upload a JPEG, PNG or WebP photo"
                                 + ("" if doc_type == "baseline_photo" else ", or a PDF"))
    doc = VaultDocument(doc_type=doc_type, path=await storage.save("vault", data),
                        content_type=FORMATS[fmt], source="upload",
                        filename_label=doc_type)   # never the client's filename
    household.documents.append(doc)
    await db.flush()
    audit(db, None, "vault_document_uploaded", household_id=household.id, doc_id=doc.id,
          doc_type=doc_type)
    await db.commit()
    return _doc_out(doc)


@router.get("/households/{household_id}/documents", response_model=list[VaultDocOut])
async def list_documents(household: Household = Depends(household_for_owner)):
    return [_doc_out(d) for d in household.documents]


@router.get("/households/{household_id}/documents/{doc_id}/file")
async def download_document(doc_id: int, household: Household = Depends(household_for_owner),
                            db: AsyncSession = Depends(get_db)):
    doc = next((d for d in household.documents if d.id == doc_id), None)
    if not doc:
        raise HTTPException(404, "Document not found")
    audit(db, None, "vault_document_viewed", household_id=household.id, doc_id=doc.id)
    await db.commit()
    return Response(await storage.read(doc.path), media_type=doc.content_type,
                    headers={"Cache-Control": "no-store"})


@router.delete("/households/{household_id}/documents/{doc_id}", status_code=204)
async def delete_document(doc_id: int, household: Household = Depends(household_for_owner),
                          db: AsyncSession = Depends(get_db)):
    """Deletes the record AND the encrypted file. Claims already submitted keep their PDF."""
    doc = next((d for d in household.documents if d.id == doc_id), None)
    if not doc:
        raise HTTPException(404, "Document not found")
    household.documents.remove(doc)    # delete-orphan removes the row
    await storage.delete(doc.path)
    audit(db, None, "vault_document_deleted", household_id=household.id, doc_id=doc_id,
          doc_type=doc.doc_type)
    await db.commit()
    return Response(status_code=204)


# ── DigiLocker (mock) ────────────────────────────────────────────────────────

def _allowed_return(url: str | None) -> str | None:
    """Only send the browser back to the app's own origins (no open redirect)."""
    if url and any(url == o or url.startswith(o.rstrip("/") + "/")
                   for o in settings.cors_origins):
        return url
    return None


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>body{{font-family:system-ui,sans-serif;margin:0;background:#f4f6fb;color:#1b1b1b}}
.demo{{background:#b00020;color:#fff;text-align:center;padding:12px;font-weight:700;font-size:18px}}
main{{max-width:460px;margin:24px auto;background:#fff;border-radius:12px;padding:24px;
box-shadow:0 2px 8px #0002}}h1{{font-size:22px;color:#1d3c8f}}li{{margin:6px 0}}
a.btn{{display:inline-block;padding:14px 22px;border-radius:8px;text-decoration:none;
font-weight:700;margin:8px 8px 0 0;min-height:20px}}.allow{{background:#1d3c8f;color:#fff}}
.deny{{background:#e4e7ef;color:#1b1b1b}}</style></head><body>
<div class="demo" role="alert">{DEMO_BANNER}. Not the real DigiLocker. Sample documents only.</div>
<main>{body}</main></body></html>""", headers={"Cache-Control": "no-store"})


@router.get("/households/{household_id}/digilocker/start")
async def digilocker_start(return_to: str | None = None,
                           household: Household = Depends(household_for_owner)):
    """Step 1 (fetch with X-Household-Token). Open the returned consent_url in the browser."""
    state = digilocker.new_state(household.id, _allowed_return(return_to))
    return {"mode": settings.digilocker_mode, "demo": True, "banner": DEMO_BANNER,
            "consent_url": digilocker.authorization_url(state)}


@router.get("/digilocker/consent", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_upload)
async def digilocker_consent(request: Request, state: str = ""):
    """Step 2 (mock only): stands in for DigiLocker's own consent screen."""
    if not digilocker.peek_state(state):
        return _page("Link expired", "<h1>This link has expired</h1>"
                                     "<p>Go back to Aapke Liye and try again.</p>")
    allow = "/digilocker/callback?" + urlencode({"state": state, "code": digilocker.MOCK_CODE})
    deny = "/digilocker/callback?" + urlencode({"state": state, "error": "access_denied"})
    items = "".join(f"<li>{html.escape(d['name'])} (sample)</li>" for d in digilocker.MOCK_ISSUED)
    return _page("DigiLocker (demo) consent", f"""<h1>DigiLocker (demo)</h1>
<p><b>Aapke Liye</b> wants to save these documents in your family's vault:</p><ul>{items}</ul>
<a class="btn allow" href="{html.escape(allow)}">Allow</a>
<a class="btn deny" href="{html.escape(deny)}">Deny</a>""")


@router.get("/digilocker/callback")
@limiter.limit(settings.rate_limit_upload)
async def digilocker_callback(request: Request, state: str = "", code: str | None = None,
                              error: str | None = None, db: AsyncSession = Depends(get_db)):
    """Step 3: add the issued documents to the vault (source="digilocker_mock")."""
    entry = digilocker.pop_state(state)   # one use only
    hh = await db.get(Household, entry[0]) if entry else None
    if not hh:
        return _page("Link expired", "<h1>This link has expired</h1>"
                                     "<p>Go back to Aapke Liye and try again.</p>")
    return_to = entry[1]
    if error or not code:
        result = "denied"
    else:
        try:
            token = digilocker.exchange_code(code)
        except ValueError:
            raise HTTPException(400, "Invalid DigiLocker response") from None
        have = {d.doc_type for d in hh.documents if d.source == "digilocker_mock"}
        added = []
        for issued in digilocker.list_issued(token):
            if issued["doc_type"] in have:
                continue      # pulled before; don't store it twice
            data, content_type = digilocker.fetch_file(token, issued["uri"])
            hh.documents.append(VaultDocument(
                doc_type=issued["doc_type"], path=await storage.save("vault", data),
                content_type=content_type, source="digilocker_mock",
                filename_label=issued["doc_type"]))
            added.append(issued["doc_type"])
        audit(db, None, "digilocker_documents_added", household_id=hh.id, doc_types=added,
              mode=settings.digilocker_mode)
        await db.commit()
        result = "added"
    if return_to:
        sep = "&" if "?" in return_to else "?"
        return RedirectResponse(f"{return_to}{sep}digilocker={result}", status_code=303)
    if result == "denied":
        return _page("Not shared", "<h1>Nothing was shared</h1><p>You can close this page.</p>")
    return _page("Documents saved", "<h1>Saved in your vault</h1><p>The sample documents "
                 "(DigiLocker demo) are in your family's vault. You can close this page.</p>")
