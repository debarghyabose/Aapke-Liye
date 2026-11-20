"""Advanced fraud checks: same house (photo GPS) and same person (phone number)."""
import sqlite3
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import config, store, sync, verify
from app.duplicates import DuplicateIndex
from app.main import app
from app.schemas import DamageResult

client = TestClient(app)
T = datetime(2026, 11, 5, 10, 0)
M10 = 0.00009  # about 10 m of latitude


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    sync.dup_index = DuplicateIndex()
    monkeypatch.setattr(verify, "assess_damage", lambda p: DamageResult(
        type="house", severity=0.8, description="x", real_photo=True))


def send(photo, claim_id, **data):
    data = {k: str(v) for k, v in {"claim_id": claim_id, **data}.items() if v is not None}
    r = client.post("/verify", files={"photo": ("p.jpg", photo, "image/jpeg")}, data=data)
    assert r.status_code == 200, r.text
    return r.json()


def fraud_types():
    return [(i["type"], i["claim_id"]) for i in client.get("/dashboard/fraud-flags").json()["items"]]


# ---------------------------------------------------------------- same house

def test_different_photo_same_spot_other_claim_is_flagged(photo_factory):
    send(photo_factory(seed=1, lat=22.57, lon=88.36, taken_at=T), "AL-1")
    body = send(photo_factory(seed=2, lat=22.57 + M10, lon=88.36, taken_at=T), "AL-2")
    assert body["duplicate"] is False  # not the same photo...
    assert any("possibly the same house" in n and "AL-1" in n for n in body["notes"])  # ...but same spot
    item = next(i for i in client.get("/dashboard/fraud-flags").json()["items"] if i["type"] == "possible_same_house")
    assert item["claim_id"] == "AL-2" and item["other_claim_id"] == "AL-1"
    assert 5 < item["distance_m"] < 15
    flags = {f["properties"]["claim_id"]: f["properties"]["flags"]
             for f in client.get("/dashboard/claims.geojson").json()["features"]}
    assert "possible_same_house" in flags["AL-2"] and "possible_same_house" not in flags["AL-1"]


def test_far_apart_is_not_flagged(photo_factory):
    send(photo_factory(seed=3, lat=22.57, lon=88.36, taken_at=T), "AL-1")
    body = send(photo_factory(seed=4, lat=22.57 + 10 * M10, lon=88.36, taken_at=T), "AL-2")  # ~100 m
    assert not any("same house" in n for n in body["notes"])


def test_second_photo_of_same_claim_is_not_flagged(photo_factory):
    send(photo_factory(seed=5, lat=22.57, lon=88.36, taken_at=T), "AL-1")
    body = send(photo_factory(seed=6, lat=22.57 + M10, lon=88.36, taken_at=T), "AL-1")
    assert not any("same house" in n for n in body["notes"])


def test_phone_location_only_is_not_used_for_same_house(photo_factory):
    """An NGO worker uploading for many families from one camp: no EXIF GPS, same phone GPS."""
    send(photo_factory(seed=7), "AL-1", lat=22.57, lon=88.36)
    body = send(photo_factory(seed=8), "AL-2", lat=22.57, lon=88.36)
    assert not any("same house" in n for n in body["notes"])


def test_exact_same_photo_is_a_duplicate_not_also_same_house(photo_factory):
    photo = photo_factory(seed=9, lat=22.57, lon=88.36, taken_at=T)
    send(photo, "AL-1")
    body = send(photo, "AL-2")
    assert body["duplicate"] is True
    assert not any("same house" in n for n in body["notes"])


# ---------------------------------------------------------------- same person (phone)

def test_phone_on_many_claims_is_flagged(photo_factory, monkeypatch):
    monkeypatch.setattr(config, "PHONE_MAX_OTHER_CLAIMS_24H", 3)
    formats = ["9876543210", "+91 98765 43210", "098765-43210", "+919876543210"]
    for i, phone in enumerate(formats):  # 4 claims, same number written 4 ways
        body = send(photo_factory(seed=20 + i), f"AL-{i}", phone=phone)
        assert not any("phone number was used" in n for n in body["notes"])  # 0..3 others: fine
    body = send(photo_factory(seed=30), "AL-9", phone="98765 43210")      # 4 others: flagged
    assert any("used on 4 other claims" in n for n in body["notes"])
    assert ("phone_many_claims", "AL-9") in fraud_types()


def test_photos_without_phone_are_never_grouped(photo_factory, monkeypatch):
    monkeypatch.setattr(config, "PHONE_MAX_OTHER_CLAIMS_24H", 0)
    send(photo_factory(seed=40), "AL-1")
    body = send(photo_factory(seed=41), "AL-2")
    assert not any("phone number was used" in n for n in body["notes"])


def test_too_short_phone_is_ignored(photo_factory, monkeypatch):
    monkeypatch.setattr(config, "PHONE_MAX_OTHER_CLAIMS_24H", 0)
    send(photo_factory(seed=42), "AL-1", phone="12345")
    body = send(photo_factory(seed=43), "AL-2", phone="12345")
    assert not any("phone number was used" in n for n in body["notes"])


def test_phone_number_is_never_stored(photo_factory, tmp_path):
    send(photo_factory(seed=50), "AL-1", phone="+91 98765 43210")
    s = store.get_store()
    raw = sqlite3.connect(s._db.execute("PRAGMA database_list").fetchone()[2]).execute(
        "SELECT * FROM photo_checks").fetchall()
    assert "9876543210" not in repr(raw) and "98765" not in repr(raw)
    assert all("phone_hash" not in c for c in s.all_checks())          # not exposed to the dashboard
    assert "phone" not in repr(client.get("/dashboard/claims.geojson").json()).replace("phone_many_claims", "")


def test_fingerprint_is_keyed(tmp_path, monkeypatch):
    """Two databases (different keys) give different fingerprints for the same number."""
    monkeypatch.setattr(config, "PHONE_HASH_KEY", "")
    a = store.Store(str(tmp_path / "a.db")).phone_fingerprint("9876543210")
    b = store.Store(str(tmp_path / "b.db")).phone_fingerprint("9876543210")
    assert a and b and a != b
    again = store.Store(str(tmp_path / "a.db")).phone_fingerprint("+91-98765-43210")
    assert again == a  # key kept in the database, formats normalised


# ---------------------------------------------------------------- old databases

def test_old_database_gets_new_columns(tmp_path):
    path = str(tmp_path / "old.db")
    db = sqlite3.connect(path)
    db.executescript(store.SCHEMA.split("CREATE TABLE IF NOT EXISTS meta")[0])  # schema before this change
    db.execute("INSERT INTO photo_checks (claim_id, gps_ok, timestamp_ok, damage_type, severity, phash, notes, "
               "checked_at) VALUES ('AL-OLD', 1, 1, 'house', 0.5, '8f373714acfcf4d0', '[]', '2026-11-20T00:00:00+00:00')")
    db.commit()
    db.close()
    s = store.Store(path)
    old = s.all_checks()[0]
    assert old["claim_id"] == "AL-OLD" and old["nearby_claims"] == []
