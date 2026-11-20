"""
Claim tracking. Member 4 owns this per the work split; it is included so the
demo works end to end. If Member 4 ships their own version, delete this file and
its include_router line in main.py, and point them at the claims/claim_status_events tables.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AuditLog, Claim, StatusEvent
from ..schemas import STATUSES, StatusUpdate

router = APIRouter(prefix="/status", tags=["tracking"])


@router.get("/{claim_id}")
def get_status(claim_id: str, db: Session = Depends(get_db)):
    claim = db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    return {"claim_id": claim.id, "status": claim.status, "updated_at": claim.updated_at,
            "timeline": [{"status": e.status, "note": e.note, "at": e.at} for e in claim.history]}


@router.put("/{claim_id}")
def put_status(claim_id: str, body: StatusUpdate, db: Session = Depends(get_db)):
    if body.status not in STATUSES:
        raise HTTPException(422, f"status must be one of {STATUSES}")
    claim = db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    claim.status = body.status
    db.add(StatusEvent(claim_id=claim.id, status=body.status, note=body.note))
    db.add(AuditLog(claim_id=claim.id, action="status_changed", detail={"status": body.status}))
    db.commit()
    return get_status(claim_id, db)
