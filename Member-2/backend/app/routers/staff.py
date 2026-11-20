"""Officials' view of a claim (X-Staff-Key). Includes what claimants do not see, such as
photos already used in another claim."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Claim, audit
from ..schemas import StaffClaimOut
from ..security import staff_member

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/claims/{claim_id}", response_model=StaffClaimOut)
async def get_claim_for_staff(claim_id: str, staff: str = Depends(staff_member),
                              db: AsyncSession = Depends(get_db)):
    claim = await db.get(Claim, claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    audit(db, claim.id, "claim_viewed", actor=f"staff:{staff}")
    await db.commit()
    out = StaffClaimOut.model_validate(claim)
    out.pdf_url = f"/claims/{claim.id}/pdf" if claim.pdf_path else None
    return out
