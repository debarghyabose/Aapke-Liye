"""
Mesh Relay Intake and Verification Router
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from .. import id_gen, mesh_crypto
from ..db import db
from .claims import _recalculate_claim

log = logging.getLogger(__name__)
router = APIRouter(prefix="/mesh", tags=["mesh"])


@router.get("/public-key")
async def get_mesh_public_key():
    return mesh_crypto.mesh_engine.get_public_key_info()


@router.post("/envelopes")
async def submit_mesh_envelope(request: Request):
    envelope = await request.json()
    claim_id = envelope.get("claim_id")
    if not claim_id:
        raise HTTPException(400, "Missing claim_id in envelope")

    try:
        payload = mesh_crypto.mesh_engine.open_envelope(envelope)
    except Exception as e:
        log.error("Failed to decrypt mesh envelope: %s", e)
        raise HTTPException(400, f"Envelope integrity verification failed: {e}")

    now_iso = datetime.now(timezone.utc).isoformat()
    fields = payload.get("fields", {})

    # Create/update claim in Firestore
    claim_data = {
        "id": claim_id,
        "token_hash": id_gen.hash_token(id_gen.new_token()),
        "language": payload.get("language", "en"),
        "disaster_type": fields.get("disaster_type", "disaster"),
        "consent_text_version": payload.get("consent_text_version", "v1"),
        "consent_given_at": payload.get("created_at", now_iso),
        "status": "Submitted",
        "submitted_at": now_iso,
        "fields": fields,
        "missing_fields": [],
        "follow_up_questions": [],
        "photos": payload.get("photos", []),
        "recordings": [],
        "history": [
            {"status": "Draft", "note": "Created offline in disaster area", "at": payload.get("created_at", now_iso)},
            {"status": "Submitted", "note": "Delivered via store-and-forward mesh relay", "at": now_iso},
        ],
        "created_at": payload.get("created_at", now_iso),
        "updated_at": now_iso,
        "relayed_via_mesh": True,
    }

    _recalculate_claim(claim_data)
    db.save_claim(claim_id, claim_data)
    db.save_mesh_envelope(claim_id, envelope)

    # Sign Ed25519 receipt
    receipt = mesh_crypto.mesh_engine.sign_receipt(claim_id)
    db.save_mesh_receipt(claim_id, receipt)
    db.log_audit(claim_id, "mesh_claim_ingested", priority=envelope.get("priority", "normal"))

    return {
        "status": "delivered",
        "receipt": receipt,
    }


@router.get("/receipts/{claim_id}")
async def get_mesh_receipt(claim_id: str):
    receipt = db.get_mesh_receipt(claim_id)
    if not receipt:
        raise HTTPException(404, "No receipt found for this claim")
    return receipt
