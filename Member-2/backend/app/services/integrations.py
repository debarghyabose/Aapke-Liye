"""
Calls to teammates' services. If the URL env var is empty, a mock response is
returned so Member 4 can build the frontend before Members 1 and 3 are ready.

CONTRACTS (share these with the team):

Member 1  POST {MEMBER1_AI_URL}/process   multipart: audio=<file>, language=<code>
  -> {"transcript": str,
      "fields": {"name", "phone", "village", "district", "state", "disaster_type",
                 "date_of_incident", "losses": [{"category","item","quantity","damage_percent"}],
                 "documents_lost": [str], "bank_account_available": bool},
      "missing_fields": [str], "follow_up_questions": [str]}

Member 3  POST {MEMBER3_VERIFY_URL}/verify  multipart: photo=<file>, lat, lon, taken_at, claim_id
  -> {"damage_detected": bool, "damage_score": 0-1, "gps_ok": bool,
      "timestamp_ok": bool, "duplicate": bool, "notes": [str]}
"""
import httpx

from ..config import MEMBER1_AI_URL, MEMBER3_VERIFY_URL

TIMEOUT = httpx.Timeout(60.0)


def process_audio(audio: bytes, filename: str, language: str) -> dict:
    if not MEMBER1_AI_URL:
        return _mock_ai(language)
    r = httpx.post(f"{MEMBER1_AI_URL.rstrip('/')}/process",
                   files={"audio": (filename, audio)}, data={"language": language},
                   timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def verify_photo(photo: bytes, filename: str, lat, lon, taken_at, claim_id: str,
                 is_duplicate_locally: bool) -> dict:
    if not MEMBER3_VERIFY_URL:
        return {"damage_detected": True, "damage_score": 0.8,
                "gps_ok": lat is not None and lon is not None,
                "timestamp_ok": taken_at is not None,
                "duplicate": is_duplicate_locally, "notes": ["mock verification"]}
    r = httpx.post(f"{MEMBER3_VERIFY_URL.rstrip('/')}/verify",
                   files={"photo": (filename, photo)},
                   data={"lat": lat, "lon": lon, "taken_at": taken_at, "claim_id": claim_id},
                   timeout=TIMEOUT)
    r.raise_for_status()
    result = r.json()
    result["duplicate"] = result.get("duplicate") or is_duplicate_locally
    return result


def _mock_ai(language: str) -> dict:
    return {
        "transcript": "(mock) Amar naam Rina Das. Bonnay amar kancha bari puro bheshe geche, "
                      "duto goru mara geche, ar ek bigha dhan nosto. Aadhaar card harie geche.",
        "fields": {
            "name": "Rina Das", "phone": None, "village": "Gosaba", "district": "South 24 Parganas",
            "state": "West Bengal", "disaster_type": "flood", "date_of_incident": None,
            "losses": [
                {"category": "house", "item": "fully_damaged_plain", "quantity": 1},
                {"category": "livestock", "item": "milch_large", "quantity": 2},
                {"category": "crop", "item": "rainfed", "quantity": 0.13, "damage_percent": 100},
                {"category": "household", "item": "clothing", "quantity": 1},
            ],
            "documents_lost": ["aadhaar"],
            "bank_account_available": True,
        },
        "missing_fields": ["phone", "date_of_incident"],
        "follow_up_questions": ["What is your phone number?", "On which date did the flood reach your house?"],
        "language": language,
    }
