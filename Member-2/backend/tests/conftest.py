"""Shared fixtures. Members 1 and 3 are mocked at the HTTP level with respx."""
import os
import tempfile

from cryptography.fernet import Fernet

DB_FILE = f"{tempfile.mkdtemp()}/test.db"
STORAGE = tempfile.mkdtemp()
STAFF_KEY = "test-staff-key-0123456789abcdef"
os.environ.update({
    "APP_ENV": "development",
    "MOCK_SERVICES": "false",
     "MOCK_MEMBER1": "false",
    "MOCK_MEMBER3": "false",
    "DATABASE_URL": f"sqlite:///{DB_FILE}",
    "STORAGE_DIR": STORAGE,
    "STORAGE_ENCRYPTION_KEY": Fernet.generate_key().decode(),
    "STAFF_API_KEYS": f"officer-test:{STAFF_KEY}",
    "MEMBER1_AI_URL": "http://member1.test",
    "MEMBER3_VERIFY_URL": "http://member3.test",
})

import httpx  # noqa: E402
import pytest  # noqa: E402
import respx  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.security import limiter  # noqa: E402
from app.services import integrations  # noqa: E402

limiter.enabled = False   # test_security.py turns it on for the rate-limit test
STAFF = {"X-Staff-Key": STAFF_KEY}
CONSENT = {"consent": True, "consent_text_version": "v1"}

# Member 1's POST /v1/claim/turn answer (Member-1/app/schemas.py TurnResponse).
AI_RESPONSE = {
    "transcript": "Amar naam Rina Das. Bonnay amar kancha bari puro bheshe geche, "
                  "duto goru mara geche, ar ek bigha dhan nosto. Aadhaar card harie geche.",
    "claim": {
        "schema_version": "1.0", "session_id": "x", "language": "bn", "status": "incomplete",
        "claimant": {"name": "Rina Das", "phone": None},
        "location": {"village": "Gosaba", "district": "South 24 Parganas",
                     "state": "West Bengal", "pincode": None},
        "disaster_type": "flood", "incident_date": None,
        "losses": [
            {"type": "house", "house_kind": "kutcha", "damage_level": "destroyed"},
            {"type": "livestock", "animal": "cow", "count": 2},
            {"type": "crop", "crop_name": "paddy", "area_acres": 0.33, "damage_level": "destroyed"},
            {"type": "belongings", "description": "clothes and utensils"},
        ],
        "documents_lost": ["aadhaar"],
        "field_confidence": {}, "transcripts": [],
    },
    "missing_fields": ["incident_date", "claimant.phone"],
    "next_question": {"field": "incident_date", "text": "On which date did the flood reach your house?",
                      "text_en": "On which date did the flood reach your house?"},
    "status": "incomplete",
}
# After member1_adapter: house 120000 + 2 cows * 37500 + paddy 0.33 acre = 0.134 ha * 8500
# (= 1139) + clothing 2500 + utensils 2500
AI_TOTAL = 120000 + 75000 + 1139 + 2500 + 2500

VERIFY_RESPONSE = {"damage_detected": True, "damage_score": 0.8, "gps_ok": True,
                   "timestamp_ok": True, "duplicate": False, "notes": []}


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    monkeypatch.setattr(integrations, "BACKOFF_SECONDS", 0)


@pytest.fixture
def services():
    """Member 1 and 3 answering normally. Tests can change `services.m1` / `services.m3`."""
    with respx.mock(assert_all_called=False) as mock:
        mock.m1 = mock.post("http://member1.test/v1/claim/turn").respond(json=AI_RESPONSE)
        mock.m3 = mock.post("http://member3.test/verify").respond(json=VERIFY_RESPONSE)
        mock.m1_health = mock.get("http://member1.test/health").respond(json={"ok": True})
        mock.m3_health = mock.get("http://member3.test/health").respond(json={"ok": True})
        yield mock


@pytest.fixture
def client(services):
    with TestClient(app) as c:
        yield c


DOWN = httpx.ConnectError("connection refused")


def new_claim(client, language="bn") -> tuple[str, dict]:
    """Create a claim; returns (claim id, headers carrying its X-Claim-Token)."""
    r = client.post("/claims", json={"language": language, **CONSENT})
    assert r.status_code == 201, r.text
    return r.json()["id"], {"X-Claim-Token": r.json()["claim_token"]}


COMPLETE_FIELDS = {"phone": "9800000000", "date_of_incident": "2026-11-15"}
JPEG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
WEBM = b"\x1a\x45\xdf\xa3fake-webm-audio"


def submitted_claim(client) -> tuple[str, dict]:
    """A claim filled by Member 1 (mocked), completed on the review screen and submitted."""
    cid, h = new_claim(client)
    r = client.post(f"/claims/{cid}/audio", headers=h,
                    files={"audio": ("a.webm", WEBM, "audio/webm")})
    assert r.status_code == 200, r.text
    assert client.patch(f"/claims/{cid}", headers=h,
                        json={"fields": COMPLETE_FIELDS}).status_code == 200
    r = client.post(f"/claims/{cid}/submit", headers=h)
    assert r.status_code == 200, r.text
    return cid, h
