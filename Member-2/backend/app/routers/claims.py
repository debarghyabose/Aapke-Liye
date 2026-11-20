import hashlib
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import STORAGE_DIR, SUPPORTED_LANGUAGES
from ..db import get_db
from ..models import AuditLog, Claim, Photo, StatusEvent
from ..schemas import ClaimCreate, ClaimFieldsUpdate, ClaimOut
from ..services import integrations
from ..services.pdf_builder import build_claim_pdf
from ..services.relief import calculate_relief, suggest_proofs

router = APIRouter(prefix="/claims", tags=["claims"])


def _get(db: Session, claim_id: str) -> Claim:
    claim = db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(404, f"Claim {claim_id} not found")
    return claim


def _out(claim: Claim) -> ClaimOut:
    out = ClaimOut.model_validate(claim)
    out.pdf_url = f"/claims/{claim.id}/pdf" if claim.pdf_path else None
    return out


def _audit(db, claim_id, action, **detail):
    db.add(AuditLog(claim_id=claim_id, action=action, detail=detail))


def _refresh_derived(claim: Claim):
    """Recompute relief amount and proof suggestions whenever fields change."""
    claim.relief = calculate_relief(claim.fields.get("losses", []))
    claim.proof_suggestions = suggest_proofs(claim.fields.get("documents_lost", []))


@router.post("", response_model=ClaimOut, status_code=201)
def create_claim(body: ClaimCreate, db: Session = Depends(get_db)):
    if body.language not in SUPPORTED_LANGUAGES:
        raise HTTPException(422, f"language must be one of {SUPPORTED_LANGUAGES}")
    claim = Claim(language=body.language, disaster_type=body.disaster_type, fields={})
    db.add(claim)
    db.flush()
    db.add(StatusEvent(claim_id=claim.id, status="Draft"))
    _audit(db, claim.id, "claim_created", language=body.language)
    db.commit()
    return _out(claim)


@router.get("/{claim_id}", response_model=ClaimOut)
def get_claim(claim_id: str, db: Session = Depends(get_db)):
    return _out(_get(db, claim_id))


@router.post("/{claim_id}/audio", response_model=ClaimOut)
async def upload_audio(claim_id: str, audio: UploadFile = File(...), db: Session = Depends(get_db)):
    claim = _get(db, claim_id)
    data = await audio.read()
    path = STORAGE_DIR / "audio" / f"{claim.id}-{uuid.uuid4().hex[:6]}-{audio.filename}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

    try:
        ai = integrations.process_audio(data, audio.filename or "audio.webm", claim.language)
    except Exception as e:  # Member 1 down -> tell the frontend clearly
        raise HTTPException(502, f"AI service error: {e}")

    claim.transcript = ai.get("transcript")
    claim.fields = {**(claim.fields or {}), **ai.get("fields", {})}  # new answers fill gaps
    claim.missing_fields = ai.get("missing_fields", [])
    claim.follow_up_questions = ai.get("follow_up_questions", [])
    claim.disaster_type = claim.fields.get("disaster_type") or claim.disaster_type
    _refresh_derived(claim)
    _audit(db, claim.id, "audio_processed", file=path.name)
    db.commit()
    return _out(claim)


@router.post("/{claim_id}/photos", response_model=ClaimOut)
async def upload_photo(
    claim_id: str,
    photo: UploadFile = File(...),
    lat: float | None = Form(None),
    lon: float | None = Form(None),
    taken_at: str | None = Form(None),
    db: Session = Depends(get_db),
):
    claim = _get(db, claim_id)
    data = await photo.read()
    digest = hashlib.sha256(data).hexdigest()
    dup = db.scalar(select(Photo).where(Photo.sha256 == digest)) is not None

    path = STORAGE_DIR / "photos" / f"{claim.id}-{digest[:10]}{_ext(photo.filename)}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

    try:
        v = integrations.verify_photo(data, photo.filename or "photo.jpg", lat, lon, taken_at,
                                      claim.id, dup)
    except Exception as e:
        v = {"error": f"verification service error: {e}", "duplicate": dup}

    db.add(Photo(claim_id=claim.id, path=str(path), sha256=digest, lat=lat, lon=lon,
                 taken_at=taken_at, verification=v))
    _audit(db, claim.id, "photo_uploaded", sha256=digest, duplicate=dup)
    db.commit()
    db.refresh(claim)
    return _out(claim)


@router.patch("/{claim_id}", response_model=ClaimOut)
def update_fields(claim_id: str, body: ClaimFieldsUpdate, db: Session = Depends(get_db)):
    claim = _get(db, claim_id)
    claim.fields = {**(claim.fields or {}), **body.fields}
    claim.missing_fields = [m for m in claim.missing_fields if not claim.fields.get(m)]
    if not claim.missing_fields:
        claim.follow_up_questions = []
    _refresh_derived(claim)
    _audit(db, claim.id, "fields_edited", keys=list(body.fields))
    db.commit()
    return _out(claim)


@router.post("/{claim_id}/submit", response_model=ClaimOut)
def submit_claim(claim_id: str, db: Session = Depends(get_db)):
    claim = _get(db, claim_id)
    if not claim.fields.get("name"):
        raise HTTPException(422, "Cannot submit: applicant name is missing")
    _refresh_derived(claim)
    claim.pdf_path = str(build_claim_pdf(claim))
    if claim.status == "Draft":
        claim.status = "Submitted"
        db.add(StatusEvent(claim_id=claim.id, status="Submitted"))
    _audit(db, claim.id, "claim_submitted", total=claim.relief["total"])
    db.commit()
    db.refresh(claim)
    return _out(claim)


@router.get("/{claim_id}/pdf")
def download_pdf(claim_id: str, db: Session = Depends(get_db)):
    claim = _get(db, claim_id)
    if not claim.pdf_path:
        raise HTTPException(409, "PDF not generated yet; call /submit first")
    return FileResponse(claim.pdf_path, media_type="application/pdf",
                        filename=f"relief-claim-{claim.id}.pdf")


def _ext(name: str | None) -> str:
    return "." + name.rsplit(".", 1)[-1].lower() if name and "." in name else ".jpg"