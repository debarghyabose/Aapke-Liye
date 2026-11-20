"""
DEVELOPMENT-ONLY stand-ins for Member 1 and Member 3.

Used only when MOCK_SERVICES=true. The app refuses to start with MOCK_SERVICES=true when
APP_ENV=production, so these answers can never reach a real claimant.
"""


def process_audio(language: str) -> dict:
    return {
        "transcript": "[DEV MOCK] No speech recognition was run.",
        "fields": {
            "name": "Dev Mock Applicant", "village": "Mockpur", "district": "Test District",
            "state": "West Bengal", "disaster_type": "flood",
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
        "follow_up_questions": ["[DEV MOCK] What is your phone number?",
                                "[DEV MOCK] On which date did the disaster reach your house?"],
    }


def verify_photo(lat, lon, taken_at) -> dict:
    return {"damage_detected": True, "damage_score": 0.8,
            "gps_ok": lat is not None and lon is not None,
            "timestamp_ok": taken_at is not None,
            "duplicate": False, "notes": ["[DEV MOCK] no real verification was run"]}


def compare_photos() -> dict:
    return {"same_property": True, "damage_score": 70, "level": "severe",
            "damaged_items": ["[DEV MOCK] roof"], "reason": "[DEV MOCK] no real comparison was run",
            "confidence": 0.5, "needs_human_review": True}
