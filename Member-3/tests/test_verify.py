"""POST /verify, called exactly the way Member 2's backend calls it
(Member-2/backend/app/services/integrations.py: verify_photo)."""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import sync, verify
from app.duplicates import DuplicateIndex
from app.main import app
from app.schemas import DamageResult

client = TestClient(app)
CONTRACT_KEYS = {"damage_detected", "damage_score", "gps_ok", "timestamp_ok", "duplicate", "notes"}
HOUSE = DamageResult(type="house", severity=0.8, description="Roof collapsed.",
                     sdrf_category="kutcha house fully damaged", real_photo=True)


@pytest.fixture(autouse=True)
def fresh_state(monkeypatch):
    sync.dup_index = DuplicateIndex()
    monkeypatch.setattr(verify, "assess_damage", lambda photo: HOUSE)


def call(photo, **data):
    """Same shape as Member 2: str() values, None fields left out."""
    data = {k: str(v) for k, v in data.items() if v is not None}
    return client.post("/verify", files={"photo": ("photo.jpg", photo, "image/jpeg")}, data=data)


def test_full_happy_path_matches_contract(photo_factory):
    photo = photo_factory(seed=1, lat=22.57, lon=88.36, taken_at=datetime(2026, 11, 5, 10, 0))
    r = call(photo, lat=22.57, lon=88.36, taken_at="2026-11-05T04:30:00+00:00", claim_id="AL-1")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == CONTRACT_KEYS
    assert body["damage_detected"] is True and body["damage_score"] == 0.8
    assert body["gps_ok"] is True and body["timestamp_ok"] is True
    assert body["duplicate"] is False
    assert "Suggested SDRF category: kutcha house fully damaged" in body["notes"]


def test_only_photo_is_required(photo_factory):
    body = call(photo_factory(seed=2)).json()
    assert body["gps_ok"] is False and body["timestamp_ok"] is False
    assert "No location available" in body["notes"]


def test_phone_location_used_when_exif_missing(photo_factory):
    body = call(photo_factory(seed=3), lat=22.57, lon=88.36, taken_at="2026-11-05T10:00:00Z").json()
    assert body["gps_ok"] is True and body["timestamp_ok"] is True
    assert "Photo has no GPS data; used the phone's location" in body["notes"]


def test_outside_zone(photo_factory):
    body = call(photo_factory(seed=4, lat=28.61, lon=77.20)).json()
    assert body["gps_ok"] is False
    assert "Location is outside the disaster area" in body["notes"]


def test_photo_gps_far_from_phone_gps_is_noted(photo_factory):
    photo = photo_factory(seed=5, lat=22.57, lon=88.36)
    body = call(photo, lat=22.90, lon=88.80).json()
    assert any("from the phone's reported location" in n for n in body["notes"])


def test_same_photo_on_another_claim_is_duplicate(photo_factory):
    photo = photo_factory(seed=6)
    assert call(photo, claim_id="AL-1").json()["duplicate"] is False
    assert call(photo, claim_id="AL-2").json()["duplicate"] is True


def test_same_claim_reupload_is_not_cross_claim_duplicate(photo_factory):
    photo = photo_factory(seed=7)
    call(photo, claim_id="AL-1")
    assert call(photo, claim_id="AL-1").json()["duplicate"] is False


def test_vision_temporarily_down_returns_503(monkeypatch, photo_factory):
    monkeypatch.setattr(verify, "assess_damage", lambda p: DamageResult(
        type="unknown", description="vision daily limit reached, retry later"))
    r = call(photo_factory(seed=8), claim_id="AL-1")
    assert r.status_code == 503
    # Not stored, so a later reverify is not flagged as a duplicate of itself elsewhere.
    assert sync.dup_index.find_photo(photo_factory(seed=8)) is None


def test_vision_not_configured_still_answers(monkeypatch, photo_factory):
    monkeypatch.setattr(verify, "assess_damage", lambda p: DamageResult(
        type="unknown", description="vision model not configured"))
    body = call(photo_factory(seed=9)).json()
    assert body["damage_detected"] is False and body["damage_score"] == 0.0
    assert "Damage not assessed: vision model not configured" in body["notes"]


def test_fake_photo_is_noted(monkeypatch, photo_factory):
    monkeypatch.setattr(verify, "assess_damage", lambda p: DamageResult(
        type="other", severity=0.0, real_photo=False, description="A drawing."))
    body = call(photo_factory(seed=10)).json()
    assert body["damage_detected"] is False
    assert any("may not be a genuine photo" in n for n in body["notes"])


def test_bad_inputs_are_422(photo_factory):
    assert call(photo_factory(seed=11), lat="abc").status_code == 422
    assert call(photo_factory(seed=11), taken_at="yesterday").status_code == 422
    assert client.post("/verify", files={"photo": ("p.jpg", b"", "image/jpeg")}).status_code == 422
