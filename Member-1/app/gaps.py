"""Decide what is still missing with plain rules (never the LLM).

Order matters: the first missing field is the one we ask about next.
"""
from __future__ import annotations

import re
from datetime import date

from .schemas import Claim, Loss

# Extra fields each loss type needs before the claim can be filed.
LOSS_REQUIRED: dict[str, list[str]] = {
    "house": ["house_kind", "damage_level", "amount_inr"],
    "shop": ["damage_level", "amount_inr"],
    "crop": ["crop_name", "area_acres", "amount_inr"],
    "livestock": ["animal", "count", "amount_inr"],
    "vehicle": ["vehicle_kind", "amount_inr"],
    "belongings": ["amount_inr"],
    "injury": [],
    "death": [],
    "other": ["description", "amount_inr"],
}

PHONE_RE = re.compile(r"^[6-9]\d{9}$")


def clean_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    return digits if PHONE_RE.match(digits) else None


def valid_date(value: str | None) -> bool:
    if not value:
        return False
    try:
        d = date.fromisoformat(value)
    except ValueError:
        return False
    return date(2000, 1, 1) <= d <= date.today()


def _loss_missing(i: int, loss: Loss) -> list[str]:
    out = []
    for f in LOSS_REQUIRED.get(loss.type, ["amount_inr"]):
        val = getattr(loss, f)
        if val is None or val == "" or (isinstance(val, (int, float)) and val <= 0):
            out.append(f"losses[{i}].{f}")
    return out


def missing_fields(claim: Claim) -> list[str]:
    missing: list[str] = []
    if not claim.claimant.name:
        missing.append("claimant.name")
    if not claim.disaster_type:
        missing.append("disaster_type")
    if not claim.losses:
        missing.append("losses")
    else:
        for i, loss in enumerate(claim.losses):
            missing.extend(_loss_missing(i, loss))
    if not claim.location.village:
        missing.append("location.village")
    if not claim.location.district:
        missing.append("location.district")
    if not claim.location.state:
        missing.append("location.state")
    if not valid_date(claim.incident_date):
        missing.append("incident_date")
    if not clean_phone(claim.claimant.phone):
        missing.append("claimant.phone")
    return missing
