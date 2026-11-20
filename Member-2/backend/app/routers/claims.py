"""
Claimant APIs. Every call except POST /claims needs the X-Claim-Token header returned
by POST /claims; a wrong or missing token gives 404.
"""
import hashlib

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from .. import storage
from ..config import SUPPORTED_LANGUAGES, settings
from ..db import get_db
from ..models import AudioRecording, Claim, Photo, StatusEvent, audit, now
from ..schemas import (ClaimCreate, ClaimCreated, ClaimFields, ClaimFieldsUpdate, ClaimOut,
                       iso_utc)
from ..security import claim_for_claimant, hash_token, limiter, new_claim_token
from ..services import integrations
from ..services.integrations import ServiceUnavailable
from ..services.pdf_builder import build_claim_pdf
from ..services.relief import calculate_relief, suggest_proofs
from ..services.validation import normalize_phone, parse_taken_at, submission_problems
from ..uploads import AUDIO, MAX_PHOTOS_PER_CLAIM, PHOTO, read_upload

router = APIRouter(prefix="/claims", tags=["claims"])

AI_DOWN = ("We could not process your recording right now. It has been saved safely; "
           "please try again in a few minutes.")
VERIFY_DOWN = ("Photo checking is not available right now. Your photo is saved and "
               "can be checked again later.")
EXT = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mpeg": "mp3", "audio/wav": "wav",
       "audio/mp4": "m4a", "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def _out(claim: Claim) -> ClaimOut:
    out = ClaimOut.model_validate(claim)
    out.pdf_url = f"/claims/{claim.id}/pdf" if claim.pdf_path else None
    return out


def _require_draft(claim: Claim):
    if claim.status != "Draft":
        raise HTTPException(409, "This claim has been submitted and can no longer be changed")


def _refresh_derived(claim: Claim):
    """Recompute relief amount and proof suggestions whenever fields change."""
    claim.relief = calculate_relief(claim.fields.get("losses", []))
    claim.proof_suggestions = suggest_proofs(claim.fields.get("documents_lost", []))


def _clean_ai_fields(raw: dict) -> dict:
    """Keep the known fields from Member 1 that pass validation. Empty values and invalid
    ones are skipped, so they stay missing and the Review screen can fill them."""
    clean = {}
    for key, value in raw.items():
        if key not in ClaimFields.model_fields or value in (None, "", []):
            continue
        try:
            clean.update(ClaimFields.model_validate({key: value})
                         .model_dump(mode="json", exclude_unset=True))
        except ValidationError:
            pass
    return clean


def _apply_ai(claim: Claim, ai: dict):
    """Merge Member 1's answer into the claim. A later recording fills gaps; nulls never
    overwrite what is already known."""
    claim.fields = {**(claim.fields or {}), **_clean_ai_fields(ai.get("fields") or {})}
    claim.transcript = ai.get("transcript") or claim.transcript
    claim.missing_fields = [m for m in ai.get("missing_fields", []) if not claim.fields.get(m)]
    claim.follow_up_questions = ai.get("follow_up_questions", []) if claim.missing_fields else []
    claim.disaster_type = claim.fields.get("disaster_type") or claim.disaster_type
    _refresh_derived(claim)


async def _process_pending_audio(db: AsyncSession, claim: Claim):
    """Send every unprocessed recording to Member 1, oldest first. On failure the
    recordings stay pending and a 503 is returned; POST /audio/retry tries again."""
    for rec in [r for r in claim.recordings if r.status == "pending"]:
        try:
            data = await storage.read(rec.path)
            ai = await integrations.process_audio(
                data, f"recording.{EXT[rec.content_type]}", rec.content_type, claim.language)
        except ServiceUnavailable as e:
            audit(db, claim.id, "audio_processing_failed", recording_id=rec.id, error=str(e))
            await db.commit()
            raise HTTPException(503, AI_DOWN, headers={"Retry-After": "60"})
        _apply_ai(claim, ai)
        rec.status = "processed"
        audit(db, claim.id, "audio_processed", recording_id=rec.id)
    await db.commit()


async def _verify(claim: Claim, photo: Photo, data: bytes) -> dict:
    try:
        v = await integrations.verify_photo(
            data, f"photo.{EXT[photo.content_type]}", photo.content_type, photo.lat, photo.lon,
            iso_utc(photo.taken_at) if photo.taken_at else None, claim.id)
    except ServiceUnavailable:
        return {"status": "pending"}
    return {**v, "status": "complete"}


@router.post("", response_model=ClaimCreated, status_code=201)
@limiter.limit(settings.rate_limit_create)
async def create_claim(request: Request, body: ClaimCreate, db: AsyncSession = Depends(get_db)):
    if body.language not in SUPPORTED_LANGUAGES:
        raise HTTPException(422, f"language must be one of {SUPPORTED_LANGUAGES}")
    token = new_claim_token()
    claim = Claim(language=body.language, disaster_type=body.disaster_type, fields={},
                  token_hash=hash_token(token), consent_text_version=body.consent_text_version,
                  consent_given_at=now(), photos=[], recordings=[],
                  history=[StatusEvent(status="Draft")])
    db.add(claim)
    await db.flush()
    audit(db, claim.id, "claim_created", language=body.language,
          consent_text_version=body.consent_text_version)
    await db.commit()
    return ClaimCreated(**_out(claim).model_dump(), claim_token=token)


@router.get("/{claim_id}", response_model=ClaimOut)
async def get_claim(claim: Claim = Depends(claim_for_claimant),
                    db: AsyncSession = Depends(get_db)):
    audit(db, claim.id, "claim_viewed")
    await db.commit()
    return _out(claim)


@router.post("/{claim_id}/audio", response_model=ClaimOut,
             responses={503: {"description": "Member 1 unavailable; audio kept for retry"}})
@limiter.limit(settings.rate_limit_upload)
async def upload_audio(request: Request, audio: UploadFile = File(...),
                       claim: Claim = Depends(claim_for_claimant),
                       db: AsyncSession = Depends(get_db)):
    _require_draft(claim)
    data, content_type, _ = await read_upload(audio, AUDIO)
    rec = AudioRecording(path=await storage.save("audio", data), content_type=content_type)
    claim.recordings.append(rec)
    await db.flush()
    audit(db, claim.id, "audio_uploaded", recording_id=rec.id, bytes=len(data))
    await _process_pending_audio(db, claim)
    return _out(claim)


@router.post("/{claim_id}/audio/retry", response_model=ClaimOut,
             responses={503: {"description": "Member 1 still unavailable"}})
@limiter.limit(settings.rate_limit_upload)
async def retry_audio(request: Request, claim: Claim = Depends(claim_for_claimant),
                      db: AsyncSession = Depends(get_db)):
    _require_draft(claim)
    if not any(r.status == "pending" for r in claim.recordings):
        raise HTTPException(409, "No recording is waiting to be processed")
    audit(db, claim.id, "audio_retry_requested")
    await _process_pending_audio(db, claim)
    return _out(claim)


@router.post("/{claim_id}/photos", response_model=ClaimOut)
@limiter.limit(settings.rate_limit_upload)
async def upload_photo(
    request: Request,
    photo: UploadFile = File(...),
    lat: float | None = Form(None, ge=-90, le=90),
    lon: float | None = Form(None, ge=-180, le=180),
    taken_at: str | None = Form(None, max_length=40, examples=["2026-11-20T10:00:00+05:30"]),
    claim: Claim = Depends(claim_for_claimant),
    db: AsyncSession = Depends(get_db),
):
    _require_draft(claim)
    try:
        taken = parse_taken_at(taken_at)
    except ValueError:
        raise HTTPException(422, "taken_at must be an ISO 8601 timestamp") from None
    data, content_type, _ = await read_upload(photo, PHOTO)
    digest = hashlib.sha256(data).hexdigest()

    if any(p.sha256 == digest for p in claim.photos):   # the app retried the same upload
        audit(db, claim.id, "photo_upload_repeated")
        await db.commit()
        return _out(claim)
    if len(claim.photos) >= MAX_PHOTOS_PER_CLAIM:
        raise HTTPException(409, f"A claim can have at most {MAX_PHOTOS_PER_CLAIM} photos")

    other_claim = await db.scalar(select(Photo.claim_id).where(
        Photo.sha256 == digest, Photo.claim_id != claim.id).limit(1))
    p = Photo(path=await storage.save("photos", data), sha256=digest, content_type=content_type,
              lat=lat, lon=lon, taken_at=taken, duplicate_of_claim_id=other_claim)
    p.verification = await _verify(claim, p, data)
    claim.photos.append(p)
    await db.flush()
    audit(db, claim.id, "photo_uploaded", photo_id=p.id, verification=p.verification["status"],
          cross_claim_duplicate=other_claim is not None)
    await db.commit()
    return _out(claim)


@router.post("/{claim_id}/photos/{photo_id}/reverify", response_model=ClaimOut,
             responses={503: {"description": "Member 3 still unavailable"}})
@limiter.limit(settings.rate_limit_upload)
async def reverify_photo(request: Request, photo_id: int,
                         claim: Claim = Depends(claim_for_claimant),
                         db: AsyncSession = Depends(get_db)):
    p = next((p for p in claim.photos if p.id == photo_id), None)
    if not p:
        raise HTTPException(404, "Photo not found")
    p.verification = await _verify(claim, p, await storage.read(p.path))
    audit(db, claim.id, "photo_reverified", photo_id=p.id,
          verification=p.verification["status"])
    await db.commit()
    if p.verification["status"] == "pending":
        raise HTTPException(503, VERIFY_DOWN, headers={"Retry-After": "60"})
    return _out(claim)


@router.patch("/{claim_id}", response_model=ClaimOut)
async def update_fields(body: ClaimFieldsUpdate, claim: Claim = Depends(claim_for_claimant),
                        db: AsyncSession = Depends(get_db)):
    _require_draft(claim)
    changes = body.fields.model_dump(mode="json", exclude_unset=True)
    claim.fields = {**(claim.fields or {}), **changes}
    claim.missing_fields = [m for m in claim.missing_fields if not claim.fields.get(m)]
    if not claim.missing_fields:
        claim.follow_up_questions = []
    _refresh_derived(claim)
    audit(db, claim.id, "fields_edited", keys=sorted(changes))
    await db.commit()
    return _out(claim)


@router.post("/{claim_id}/submit", response_model=ClaimOut)
async def submit_claim(claim: Claim = Depends(claim_for_claimant),
                       db: AsyncSession = Depends(get_db)):
    _require_draft(claim)
    missing, invalid = submission_problems(claim.fields)
    if missing or invalid:
        audit(db, claim.id, "submit_rejected", missing=missing, invalid=sorted(invalid))
        await db.commit()
        raise HTTPException(422, {"message": "Some details are missing or need correcting",
                                  "missing_fields": missing, "invalid_fields": invalid})
    claim.fields = {**claim.fields, "phone": normalize_phone(claim.fields["phone"])}
    _refresh_derived(claim)
    claim.status, claim.submitted_at = "Submitted", now()
    claim.history.append(StatusEvent(status="Submitted"))
    photos = {p.id: await storage.read(p.path) for p in claim.photos}
    pdf = await run_in_threadpool(build_claim_pdf, claim, photos)
    claim.pdf_path = await storage.save("pdfs", pdf)
    audit(db, claim.id, "claim_submitted", total=claim.relief["total"])
    await db.commit()
    return _out(claim)


@router.get("/{claim_id}/pdf")
async def download_pdf(claim: Claim = Depends(claim_for_claimant),
                       db: AsyncSession = Depends(get_db)):
    if not claim.pdf_path:
        raise HTTPException(409, "PDF not generated yet; call /submit first")
    pdf = await storage.read(claim.pdf_path)
    audit(db, claim.id, "pdf_downloaded")
    await db.commit()
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition":
                             f'attachment; filename="relief-claim-{claim.id}.pdf"',
                             "Cache-Control": "no-store"})
