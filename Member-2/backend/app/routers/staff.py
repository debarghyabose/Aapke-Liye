"""Officials' view of a claim (X-Staff-Key). Includes what claimants do not see, such as
photos already used in another claim."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Claim, audit
from ..schemas import StaffClaimOut
from ..security import staff_member
from ..services import integrations

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
    out = [_staff_out(c) for c in claims]
    # Vulnerable households first (stable sort keeps newest-first inside each group).
    out.sort(key=lambda c: not any(c.vulnerability_flags.values()))
    return out


@router.get("/claims/{claim_id}", response_model=StaffClaimOut)
async def get_claim_for_staff(claim_id: str, staff: str = Depends(staff_member),
                              db: AsyncSession = Depends(get_db)):
    claim = await db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    audit(db, claim.id, "claim_viewed", actor=f"staff:{staff}")
    await db.commit()
    return _staff_out(claim)


@router.get("/dashboard/{view}")
async def dashboard_for_staff(view: str, cell_km: float | None = Query(None, gt=0.1, le=50),
                              staff: str = Depends(staff_member)):
    """Member 3's live map data for the officials' screen: claim points, damage heatmap,
    satellite flood extent, fraud flags. Shows exact household locations, so staff only."""
    if view not in integrations.DASHBOARD_VIEWS:
        raise HTTPException(404, "Unknown dashboard view")
    try:
        return await integrations.dashboard(view, {"cell_km": cell_km} if cell_km else None)
    except integrations.ServiceUnavailable:
        raise HTTPException(503, "Map data is not available right now")
