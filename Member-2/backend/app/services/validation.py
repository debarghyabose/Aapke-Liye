"""Checks run before a claim can be submitted, and input normalisation."""
import re
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
REQUIRED = ["name", "phone", "village", "district", "state", "date_of_incident", "losses"]


def normalize_phone(raw) -> str | None:
    """'+91 98000-00000', '09800000000', '9800000000' -> '9800000000'. None if invalid."""
    digits = re.sub(r"[\s\-().]", "", str(raw or ""))
    digits = re.sub(r"^(\+91|0091|91(?=\d{10}$)|0(?=\d{10}$))", "", digits)
    return digits if re.fullmatch(r"[6-9]\d{9}", digits) else None


def submission_problems(fields: dict) -> tuple[list[str], dict[str, str]]:
    """Returns (missing fields, {field: why it is invalid})."""
    missing = [k for k in REQUIRED if not fields.get(k)]
    invalid = {}
    if fields.get("phone") and not normalize_phone(fields["phone"]):
        invalid["phone"] = "Must be a 10-digit Indian mobile number"
    if d := fields.get("date_of_incident"):
        try:
            if date.fromisoformat(str(d)) > datetime.now(IST).date():
                invalid["date_of_incident"] = "Cannot be in the future"
        except ValueError:
            invalid["date_of_incident"] = "Must be a date like 2026-11-15"
    return missing, invalid


def parse_taken_at(value: str | None) -> datetime | None:
    """ISO 8601 from the phone -> aware UTC datetime. A time without an offset is
    taken as India time (IST). Raises ValueError if it is not a valid timestamp."""
    if not value:
        return None
    dt = datetime.fromisoformat(value.strip())
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(timezone.utc)
