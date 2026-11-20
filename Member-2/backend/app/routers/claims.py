"""
Claimant APIs. Every call except POST /claims needs the X-Claim-Token header returned
by POST /claims; a wrong or missing token gives 404.
"""
import hashlib
import logging

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from .. import storage
from ..config import SUPPORTED_LANGUAGES, settings
from ..db import get_db
from ..models import AudioRecording, AuditLog, Claim, Photo, StatusEvent, audit, now
from ..schemas import (ClaimCreate, ClaimCreated, ClaimFields, ClaimFieldsUpdate, ClaimOut,
                       ClaimText, HouseholdLink, iso_utc)
from ..security import (claim_for_claimant, hash_token, household_with_token, limiter,
                        new_claim_token)
from ..services import integrations, member1_adapter
from ..services.integrations import ServiceUnavailable
from ..services.pdf_builder import build_claim_pdf
from ..services.relief import calculate_relief, suggest_proofs
from ..services.validation import normalize_phone, parse_taken_at, submission_problems
from ..uploads import AUDIO, MAX_PHOTOS_PER_CLAIM, PHOTO, read_upload

log = logging.getLogger(__name__)

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
    """Recompute relief amount and proof suggestions whenever fields change. Documents the
    family saved in its vault are available, so they need no substitute proof."""
    claim.relief = calculate_relief(claim.fields.get("losses", []),
                                    claim.fields.get("crop_insured"),
                                    claim.fields.get("is_hilly"))
    in_vault = {d["document"] for d in claim.documents_in_vault}
    claim.proof_suggestions = suggest_proofs(
        [d for d in claim.fields.get("documents_lost") or [] if d not in in_vault])


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
    if ai.get("ai_state"):
        claim.ai_state = ai["ai_state"]
    _refresh_derived(claim)


async def _process_pending_audio(db: AsyncSession, claim: Claim):
    """Send every unprocessed recording to Member 1, oldest first. On failure the
    recordings stay pending and a 503 is returned; POST /audio/retry tries again."""
    for rec in [r for r in claim.recordings if r.status == "pending"]:
        try:
            data = await storage.read(rec.path)
            ai = await integrations.process_audio(
                data, f"recording.{EXT[rec.content_type]}", rec.content_type, claim.language,
                claim.id, claim.ai_state)
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
            iso_utc(photo.taken_at) if photo.taken_at else None, claim.id,
            # For Member 3's "one phone, many claims" check. Known once the voice claim is
            # processed; photos uploaded before that are sent without it.
            normalize_phone((claim.fields or {}).get("phone")))
    except ServiceUnavailable:
        return {"status": "pending"}
    return {**v, "status": "complete"}


async def _before_after(claim: Claim, photo: Photo, data: bytes) -> None:
    """If the family saved a baseline photo in its vault, ask Member 1 to compare it with this
    claim photo and keep the answer in photo.verification["before_after"]. Never fails the
    upload: if Member 1 is down the result is {"status": "unavailable"}."""
    baseline = next((d for d in (claim.household.documents if claim.household else [])
                     if d.doc_type == "baseline_photo"), None)
    if not baseline:
        return
    try:
        result = await integrations.compare_photos(
            await storage.read(baseline.path), baseline.content_type, data, photo.content_type,
            claim.fields.get("disaster_type") or claim.disaster_type)
        result = {**result, "status": "complete", "baseline_document_id": baseline.id}
    except Exception as e:   # ServiceUnavailable, bad reply, unreadable file ...
        log.warning("before/after comparison unavailable: %s", type(e).__name__)
        result = {"status": "unavailable"}
    photo.verification = {**(photo.verification or {}), "before_after": result}


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


@router.post("/{claim_id}/text", response_model=ClaimOut,
             responses={503: {"description": "Member 1 unavailable"}})
@limiter.limit(settings.rate_limit_upload)
async def send_text(request: Request, body: ClaimText,
                    claim: Claim = Depends(claim_for_claimant),
                    db: AsyncSession = Depends(get_db)):
    """A typed answer, a tapped suggested answer, or speech the phone already transcribed.
    Goes through Member 1's claim AI exactly like a voice note."""
    _require_draft(claim)
    try:
        ai = await integrations.process_text(body.text, claim.language, claim.id, claim.ai_state)
    except ServiceUnavailable as e:
        audit(db, claim.id, "text_processing_failed", error=str(e))
        await db.commit()
        raise HTTPException(503, AI_DOWN.replace("recording", "answer"),
                            headers={"Retry-After": "60"})
    _apply_ai(claim, ai)
    audit(db, claim.id, "text_processed", chars=len(body.text))
    await db.commit()
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
    await _before_after(claim, p, data)
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


@router.post("/{claim_id}/household", response_model=ClaimOut)
async def link_household(body: HouseholdLink, x_household_token: str | None = Header(None),
                         claim: Claim = Depends(claim_for_claimant),
                         db: AsyncSession = Depends(get_db)):
    """Use the family's document vault for this claim ("Use my household" on claim step 1).
    Needs both tokens, so nobody can attach another family's papers to their claim.
    Photos already on the claim are compared with the baseline photo now."""
    _require_draft(claim)
    claim.household = await household_with_token(db, body.household_id, x_household_token)
    for p in claim.photos:
        if "before_after" not in (p.verification or {}):
            await _before_after(claim, p, await storage.read(p.path))
    _refresh_derived(claim)
    audit(db, claim.id, "household_linked", household_id=claim.household.id,
          vault_documents=[d["document"] for d in claim.documents_in_vault])
    await db.commit()
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


@router.post("/{claim_id}/documents/{doc_type}",
             responses={503: {"description": "Member 1 unavailable"}})
@limiter.limit(settings.rate_limit_upload)
async def draft_document(request: Request, doc_type: str,
                         claim: Claim = Depends(claim_for_claimant),
                         db: AsyncSession = Depends(get_db)):
    """A ready-to-sign letter (Aadhaar / ration card / land record reissue, insurance notice,
    follow-up, grievance, RTI) filled from this claim with Member 5's legal templates."""
    if doc_type not in integrations.DOC_TYPES:
        raise HTTPException(404, "Unknown document type")
    m1_claim = member1_adapter.to_member1_claim(claim.id, claim.language, claim.fields or {},
                                                claim.ai_state)
    extra = {"claim_id": claim.id}
    if claim.submitted_at:
        extra["application_date"] = claim.submitted_at.strftime("%d-%m-%Y")
    if (claim.relief or {}).get("total"):
        extra["sdrf_estimate"] = f"Rs. {claim.relief['total']:,}"
    try:
        out = await integrations.draft_document(doc_type, m1_claim, extra)
    except ServiceUnavailable as e:
        audit(db, claim.id, "document_draft_failed", doc_type=doc_type, error=str(e))
        await db.commit()
        raise HTTPException(503, "Letter drafting is not available right now. Please try again.",
                            headers={"Retry-After": "60"})
    audit(db, claim.id, "document_drafted", doc_type=doc_type)
    await db.commit()
    return {"doc_type": doc_type, "title": out.get("title"), "text": out.get("text", ""),
            "missing_fields": out.get("missing_fields", [])}


ESCALATION_STEPS = ("followup_letter", "grievance", "rti_application")


@router.get("/{claim_id}/escalation")
async def escalation(claim: Claim = Depends(claim_for_claimant),
                     db: AsyncSession = Depends(get_db)):
    """Which letter to send next for a claim stuck without approval (Member 1's ladder:
    follow-up, then grievance, then RTI). Letters already drafted count as done."""
    if not claim.submitted_at or claim.status not in ("Submitted", "Verified"):
        return {"days_pending": 0, "next_step": None,
                "reason": "Only submitted claims waiting for approval are escalated"}
    submitted = claim.submitted_at
    if submitted.tzinfo is None:
        submitted = submitted.replace(tzinfo=now().tzinfo)
    days = (now() - submitted).days
    drafted = (await db.scalars(select(AuditLog.detail).where(
        AuditLog.claim_id == claim.id, AuditLog.action == "document_drafted"))).all()
    done = [s for s in ESCALATION_STEPS if any((d or {}).get("doc_type") == s for d in drafted)]
    try:
        out = await integrations.next_escalation(days, done)
    except ServiceUnavailable:
        raise HTTPException(503, "Escalation advice is not available right now")
    return {"days_pending": days, "steps_done": done, **out}
