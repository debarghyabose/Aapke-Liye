"""Combine every check into one trust score (0-100), flags and a status."""
from datetime import datetime, timezone

from app.schemas import Checks, VerificationResult, VerificationStatus


def score(claim_id: str, checks: Checks) -> VerificationResult:
    points, flags = 0, []

    if checks.duplicate_of:
        flags.append("duplicate")

    if checks.gps_in_zone is True:
        points += 35
    elif checks.gps_in_zone is False:
        flags.append("gps_outside_zone")
    else:
        points += 15
        flags.append("gps_missing")

    if checks.timestamp_valid is True:
        points += 25
    elif checks.timestamp_valid is False:
        flags.append("timestamp_invalid")
    else:
        points += 10
        flags.append("timestamp_missing")

    if checks.damage.type != "unknown":
        points += 20 + int(20 * checks.damage.severity)
    else:
        flags.append("damage_unassessed")

    points = max(0, min(100, points))

    if checks.duplicate_of:
        status = VerificationStatus.flagged
    elif points >= 70 and "gps_outside_zone" not in flags:
        status = VerificationStatus.auto_verified
    elif points >= 30:
        status = VerificationStatus.needs_review
    else:
        status = VerificationStatus.flagged

    return VerificationResult(
        claim_id=claim_id,
        trust_score=points,
        status=status,
        checks=checks,
        flags=flags,
        verified_at=datetime.now(timezone.utc),
    )
