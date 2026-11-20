"""
Claim tracking. GET needs the claimant's X-Claim-Token; PUT is staff-only (X-Staff-Key).
Member 4 owns tracking per the work split and can read the claims and
claim_status_events tables.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Claim, StatusEvent, audit
from ..schemas import STAFF_TRANSITIONS, STATUSES, StatusOut, StatusUpdate
from ..security import claim_for_claimant, staff_member

router = APIRouter(prefix="/status", tags=["tracking"])
log = logging.getLogger(__name__)


def _status(claim: Claim) -> StatusOut:
    return StatusOut(claim_id=claim.id, status=claim.status, updated_at=claim.updated_at,
                     timeline=claim.history)


@router.get("/{claim_id}", response_model=StatusOut)
async def get_status(claim: Claim = Depends(claim_for_claimant),
                     db: AsyncSession = Depends(get_db)):
    audit(db, claim.id, "status_viewed")
    await db.commit()
    return _status(claim)


@router.put("/{claim_id}", response_model=StatusOut,
            responses={409: {"description": "Transition not allowed from the current status"}})
async def put_status(claim_id: str, body: StatusUpdate, staff: str = Depends(staff_member),
                     db: AsyncSession = Depends(get_db)):
    if body.status not in STATUSES:
        raise HTTPException(422, f"status must be one of {STATUSES}")
    claim = await db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    previous = claim.status
    allowed = STAFF_TRANSITIONS.get(previous, set())
    if body.status not in allowed:
        raise HTTPException(409, f"Cannot change status from {previous} to {body.status}. "
                                 f"Allowed: {', '.join(sorted(allowed)) or 'none'}")
    claim.status = body.status
    claim.history.append(StatusEvent(status=body.status, note=body.note))
    audit(db, claim.id, "status_changed", actor=f"staff:{staff}", old=previous, new=body.status)
    await db.commit()
    log.info("status changed", extra={"claim_id": claim.id, "staff": staff,
                                      "old": previous, "new": body.status})
    return _status(claim)
