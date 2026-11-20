"""Claim tokens (claimants), staff keys (officials) and per-IP rate limits."""
import hashlib
import hmac
import secrets

from fastapi import Depends, Header, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_db
from .models import Claim, Household

limiter = Limiter(key_func=get_remote_address)


def new_claim_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    # The token is 256 random bits, so a plain SHA-256 is enough (no salt/KDF needed).
    return hashlib.sha256(token.encode()).hexdigest()


async def claim_for_claimant(claim_id: str, x_claim_token: str | None = Header(None),
                             db: AsyncSession = Depends(get_db)) -> Claim:
    """The claim, if X-Claim-Token matches. Otherwise 404, so callers cannot tell
    whether a claim ID exists."""
    claim = await db.get(Claim, claim_id)
    if not claim or not x_claim_token or not hmac.compare_digest(
            claim.token_hash, hash_token(x_claim_token)):
        raise HTTPException(404, "Claim not found")
    return claim


def staff_member(x_staff_key: str | None = Header(None)) -> str:
    """The label of the matching STAFF_API_KEYS entry (logged in the audit trail)."""
    for label, key in settings.staff_api_keys.items():
        if x_staff_key and hmac.compare_digest(x_staff_key.encode(), key.encode()):
            return label
    raise HTTPException(401, "A valid X-Staff-Key header is required")


async def household_with_token(db: AsyncSession, household_id: str,
                               token: str | None) -> Household:
    """The household, if `token` matches its X-Household-Token. Otherwise 404."""
    hh = await db.get(Household, household_id)
    if not hh or not token or not hmac.compare_digest(hh.token_hash, hash_token(token)):
        raise HTTPException(404, "Household not found")
    return hh


async def household_for_owner(household_id: str, x_household_token: str | None = Header(None),
                              db: AsyncSession = Depends(get_db)) -> Household:
    return await household_with_token(db, household_id, x_household_token)
