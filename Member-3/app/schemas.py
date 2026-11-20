"""The JSON contract shared with Member 2 (storage) and Member 5 (dashboard).

Agree on these fields with the team before changing them.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    auto_verified = "auto_verified"
    needs_review = "needs_review"
    flagged = "flagged"


class DamageResult(BaseModel):
    type: str = "unknown"  # house | crop | livestock | vehicle | other | none | unknown
    severity: float = Field(0.0, ge=0.0, le=1.0)
    description: str = ""
    sdrf_category: Optional[str] = None  # e.g. "pucca house fully damaged" (for Member 1)
    real_photo: Optional[bool] = None  # False = screenshot / stock / AI image


class Checks(BaseModel):
    gps_in_zone: Optional[bool] = None
    timestamp_valid: Optional[bool] = None
    damage: DamageResult = DamageResult()
    duplicate_of: Optional[str] = None
    satellite_match: Optional[bool] = None  # Phase 2


class VerificationResult(BaseModel):
    claim_id: str
    trust_score: int = Field(ge=0, le=100)
    status: VerificationStatus
    checks: Checks
    flags: list[str] = []
    verified_at: datetime
