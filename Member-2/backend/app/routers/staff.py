"""Officials' view of a claim (X-Staff-Key). Includes what claimants do not see, such as
photos already used in another claim."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Claim, audit
from ..schemas import StaffClaimOut
from ..security import staff_member

router = APIRouter(prefix="/staff", tags=["staff"])


def _staff_out(claim: Claim) -> StaffClaimOut:
    out = StaffClaimOut.model_validate(claim)
    out.pdf_url = f"/claims/{claim.id}/pdf" if claim.pdf_path else None
    return out


@router.get("/claims", response_model=list[StaffClaimOut])
async def list_claims_for_staff(status: str | None = Query(None, max_length=20),
                                limit: int = Query(100, ge=1, le=500),
                                staff: str = Depends(staff_member),
                                db: AsyncSession = Depends(get_db)):
    """The officials' queue: submitted claims, newest first (drafts are not shown)."""
    q = select(Claim).where(Claim.status != "Draft")
    if status:
        q = q.where(Claim.status == status)
    claims = (await db.scalars(q.order_by(Claim.submitted_at.desc()).limit(limit))).all()
    audit(db, None, "claims_listed", actor=f"staff:{staff}", count=len(claims))
    await db.commit()
    return [_staff_out(c) for c in claims]


@router.get("/claims/{claim_id}", response_model=StaffClaimOut)
async def get_claim_for_staff(claim_id: str, staff: str = Depends(staff_member),
                              db: AsyncSession = Depends(get_db)):
    claim = await db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    audit(db, claim.id, "claim_viewed", actor=f"staff:{staff}")
    await db.commit()
    return _staff_out(claim)
