"""
Claimant APIs for Aapke Liye
"""
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse

from .. import ai_service, config, entitlement, id_gen, image_storage, legal_templates, pdf_generator, proofs, vision_service
from ..db import db
from ..schemas import ClaimCreate, ClaimFieldsUpdate, ClaimText, HouseholdLink

log = logging.getLogger(__name__)

router = APIRouter(prefix="/claims", tags=["claims"])


def _get_claim_with_auth(claim_id: str, x_claim_token: Optional[str] = Header(None)) -> Dict[str, Any]:
    claim = db.get_claim(claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    token_hash = claim.get("token_hash")
    if token_hash and x_claim_token:
        if not id_gen.verify_token(x_claim_token, token_hash):
            raise HTTPException(403, "Invalid claim token")
    return claim


def _recalculate_claim(claim: Dict[str, Any]):
    fields = claim.get("fields", {})
    losses = fields.get("losses", [])
    crop_insured = fields.get("crop_insured", False)
    is_hilly = fields.get("is_hilly", False)
    claim["relief"] = entitlement.calculate_relief(losses, crop_insured, is_hilly)

    vault_docs = {d.get("doc_type") for d in claim.get("documents_in_vault", [])}
    lost_docs = [d for d in fields.get("documents_lost", []) if d not in vault_docs]
    claim["proof_suggestions"] = proofs.suggest_proofs(lost_docs)


@router.post("", status_code=201)
async def create_claim(body: ClaimCreate):
    token = id_gen.new_token()
    token_hash = id_gen.hash_token(token)
    claim_id = id_gen.generate_claim_id()
    now_iso = datetime.now(timezone.utc).isoformat()

    claim_data = {
        "id": claim_id,
        "token_hash": token_hash,
        "language": body.language,
        "disaster_type": body.disaster_type,
        "consent_text_version": body.consent_text_version,
        "consent_given_at": now_iso,
        "status": "Draft",
        "transcript": "",
        "fields": {
            "disaster_type": body.disaster_type,
            "losses": [],
            "documents_lost": [],
            "vulnerability": [],
        },
        "missing_fields": ["name", "phone", "village", "district", "state", "losses"],
        "follow_up_questions": [],
        "relief": None,
        "proof_suggestions": [],
        "photos": [],
        "recordings": [],
        "documents_in_vault": [],
        "history": [{"status": "Draft", "note": "Claim initialized", "at": now_iso}],
        "created_at": now_iso,
        "updated_at": now_iso,
        "submitted_at": None,
    }

    _recalculate_claim(claim_data)
    db.save_claim(claim_id, claim_data)
    db.log_audit(claim_id, "claim_created", actor="claimant")

    return {**claim_data, "claim_token": token}


@router.get("/{claim_id}")
async def get_claim(claim_id: str, x_claim_token: Optional[str] = Header(None)):
    claim = _get_claim_with_auth(claim_id, x_claim_token)
    return claim


@router.post("/{claim_id}/audio")
async def upload_audio(
    claim_id: str,
    audio: UploadFile = File(...),
    x_claim_token: Optional[str] = Header(None),
):
    claim = _get_claim_with_auth(claim_id, x_claim_token)
    if claim.get("status") != "Draft":
        raise HTTPException(409, "Claim has already been submitted")

    audio_bytes = await audio.read()
    content_type = audio.content_type or "audio/webm"
    language = claim.get("language", "en")

    # Transcribe and extract using Gemini 3.5 Flash Multimodal
    result = await ai_service.process_audio_claim(
        audio_bytes, content_type, language, existing_fields=claim.get("fields")
    )

    claim["transcript"] = result.get("transcript") or claim.get("transcript")
    claim["fields"] = result.get("fields", claim.get("fields"))
    claim["missing_fields"] = result.get("missing_fields", [])
    claim["follow_up_questions"] = result.get("follow_up_questions", [])
    if claim["fields"].get("disaster_type"):
        claim["disaster_type"] = claim["fields"]["disaster_type"]

    _recalculate_claim(claim)
    claim["recordings"].append({
        "id": len(claim["recordings"]) + 1,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "status": "processed",
    })

    db.save_claim(claim_id, claim)
    db.log_audit(claim_id, "audio_processed", bytes=len(audio_bytes))
    return claim


@router.post("/{claim_id}/text")
async def send_text(
    claim_id: str,
    body: ClaimText,
    x_claim_token: Optional[str] = Header(None),
):
    claim = _get_claim_with_auth(claim_id, x_claim_token)
    if claim.get("status") != "Draft":
        raise HTTPException(409, "Claim has already been submitted")

    language = claim.get("language", "en")
    result = await ai_service.process_text_claim(
        body.text, language, existing_fields=claim.get("fields")
    )

    prior = claim.get("transcript", "")
    claim["transcript"] = f"{prior}\n{body.text}".strip() if prior else body.text
    claim["fields"] = result.get("fields", claim.get("fields"))
    claim["missing_fields"] = result.get("missing_fields", [])
    claim["follow_up_questions"] = result.get("follow_up_questions", [])
    if claim["fields"].get("disaster_type"):
        claim["disaster_type"] = claim["fields"]["disaster_type"]

    _recalculate_claim(claim)
    db.save_claim(claim_id, claim)
    db.log_audit(claim_id, "text_processed", chars=len(body.text))
    return claim


@router.post("/{claim_id}/photos")
async def upload_photo(
    claim_id: str,
    photo: UploadFile = File(...),
    lat: Optional[float] = Form(None),
    lon: Optional[float] = Form(None),
    taken_at: Optional[str] = Form(None),
    x_claim_token: Optional[str] = Header(None),
):
    claim = _get_claim_with_auth(claim_id, x_claim_token)
    if claim.get("status") != "Draft":
        raise HTTPException(409, "Claim has already been submitted")

    photo_bytes = await photo.read()
    digest = vision_service.hash_photo(photo_bytes)

    # Check for duplicate within claim
    for p in claim.get("photos", []):
        if p.get("sha256") == digest:
            return claim

    # Check cross-claim duplicate
    dup_claim = db.find_duplicate_photo(digest, current_claim_id=claim_id)

    # Extract EXIF if not provided
    exif_lat, exif_lon, exif_time = vision_service.extract_exif_metadata(photo_bytes)
    final_lat = lat if lat is not None else exif_lat
    final_lon = lon if lon is not None else exif_lon
    final_time = taken_at or exif_time or datetime.now(timezone.utc).isoformat()

    # Save image (Cloudinary or local)
    url, path = await image_storage.storage_service.save_image(
        photo_bytes, photo.filename or "photo.jpg", photo.content_type or "image/jpeg"
    )

    # Gemini Vision Analysis
    verification = await vision_service.verify_damage_photo(
        photo_bytes, photo.content_type or "image/jpeg", disaster_type=claim.get("disaster_type") or "disaster"
    )
    verification["duplicate"] = dup_claim is not None
    verification["gps_ok"] = final_lat is not None and final_lon is not None
    verification["timestamp_ok"] = final_time is not None

    photo_record = {
        "id": len(claim.get("photos", [])) + 1,
        "sha256": digest,
        "lat": final_lat,
        "lon": final_lon,
        "taken_at": final_time,
        "url": url,
        "path": path,
        "duplicate_of_claim_id": dup_claim,
        "verification": verification,
    }

    claim["photos"].append(photo_record)
    db.save_claim(claim_id, claim)
    db.log_audit(claim_id, "photo_uploaded", photo_id=photo_record["id"], damage=verification.get("damage_level"))
    return claim


@router.post("/{claim_id}/photos/{photo_id}/reverify")
async def reverify_photo(
    claim_id: str,
    photo_id: int,
    x_claim_token: Optional[str] = Header(None),
):
    claim = _get_claim_with_auth(claim_id, x_claim_token)
    photo = next((p for p in claim.get("photos", []) if p.get("id") == photo_id), None)
    if not photo:
        raise HTTPException(404, "Photo not found")

    photo_bytes = await image_storage.storage_service.read_file(photo["path"])
    verification = await vision_service.verify_damage_photo(
        photo_bytes, disaster_type=claim.get("disaster_type") or "disaster"
    )
    photo["verification"].update(verification)
    photo["verification"]["status"] = "complete"

    db.save_claim(claim_id, claim)
    return claim


@router.post("/{claim_id}/household")
async def link_household(
    claim_id: str,
    body: HouseholdLink,
    x_claim_token: Optional[str] = Header(None),
    x_household_token: Optional[str] = Header(None),
):
    claim = _get_claim_with_auth(claim_id, x_claim_token)
    household = db.get_household(body.household_id)
    if not household:
        raise HTTPException(404, "Household not found")

    claim["household_id"] = household.get("household_id")
    claim["fields"]["household_id"] = household.get("household_id")
    claim["documents_in_vault"] = [
        {"document": d.get("doc_type"), "source": d.get("source")}
        for d in household.get("documents", [])
    ]

    # Before / After photo comparison if baseline photo exists in vault
    baseline = next((d for d in household.get("documents", []) if d.get("doc_type") == "baseline_photo"), None)
    if baseline:
        try:
            base_bytes = await image_storage.storage_service.read_file(baseline.get("file_url"))
            for p in claim.get("photos", []):
                p_bytes = await image_storage.storage_service.read_file(p.get("path"))
                comp = await vision_service.compare_photos(base_bytes, baseline.get("content_type", "image/jpeg"), p_bytes, "image/jpeg")
                p["verification"]["before_after"] = comp
        except Exception as e:
            log.warning("Before/after comparison skipped: %s", e)

    _recalculate_claim(claim)
    db.save_claim(claim_id, claim)
    db.log_audit(claim_id, "household_linked", household_id=body.household_id)
    return claim


@router.patch("/{claim_id}")
async def update_fields(
    claim_id: str,
    body: ClaimFieldsUpdate,
    x_claim_token: Optional[str] = Header(None),
):
    claim = _get_claim_with_auth(claim_id, x_claim_token)
    if claim.get("status") != "Draft":
        raise HTTPException(409, "Claim has already been submitted")

    updates = body.fields.model_dump(exclude_unset=True)
    claim["fields"].update(updates)
    claim["missing_fields"] = [m for m in claim.get("missing_fields", []) if claim["fields"].get(m) in (None, "", [])]

    if claim["fields"].get("disaster_type"):
        claim["disaster_type"] = claim["fields"]["disaster_type"]

    _recalculate_claim(claim)
    db.save_claim(claim_id, claim)
    db.log_audit(claim_id, "fields_updated", fields=list(updates.keys()))
    return claim


@router.post("/{claim_id}/submit")
async def submit_claim(
    claim_id: str,
    x_claim_token: Optional[str] = Header(None),
):
    claim = _get_claim_with_auth(claim_id, x_claim_token)
    if claim.get("status") != "Draft":
        return claim

    now_iso = datetime.now(timezone.utc).isoformat()
    claim["status"] = "Submitted"
    claim["submitted_at"] = now_iso
    claim["history"].append({"status": "Submitted", "note": "Claim submitted with digital declaration", "at": now_iso})

    _recalculate_claim(claim)

    # Generate official PDF
    try:
        pdf_bytes = pdf_generator.generate_claim_pdf(claim)
        pdf_path = config.STORAGE_DIR / f"relief-claim-{claim_id}.pdf"
        pdf_path.write_bytes(pdf_bytes)
        claim["pdf_url"] = f"/claims/{claim_id}/pdf"
        claim["pdf_path"] = str(pdf_path)
    except Exception as e:
        log.error("PDF generation failed: %s", e)

    db.save_claim(claim_id, claim)
    db.log_audit(claim_id, "claim_submitted", relief_total=claim.get("relief", {}).get("total", 0))
    return claim


@router.get("/{claim_id}/pdf")
async def get_claim_pdf(claim_id: str, x_claim_token: Optional[str] = Header(None)):
    claim = db.get_claim(claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")

    pdf_path = claim.get("pdf_path")
    if pdf_path and Path(pdf_path).exists():
        pdf_bytes = Path(pdf_path).read_bytes()
    else:
        pdf_bytes = pdf_generator.generate_claim_pdf(claim)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="relief-claim-{claim_id}.pdf"'},
    )


@router.post("/{claim_id}/documents/{doc_type}")
async def draft_document(
    claim_id: str,
    doc_type: str,
    x_claim_token: Optional[str] = Header(None),
):
    claim = _get_claim_with_auth(claim_id, x_claim_token)
    escalation = legal_templates.get_escalation_status(claim)
    draft = legal_templates.draft_legal_document(doc_type, claim, extra={"days_pending": escalation["days_pending"]})
    return draft


@router.get("/{claim_id}/escalation")
async def get_escalation(claim_id: str, x_claim_token: Optional[str] = Header(None)):
    claim = _get_claim_with_auth(claim_id, x_claim_token)
    return legal_templates.get_escalation_status(claim)
