from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import sync
from app.duplicates import DuplicateIndex
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    sync.results.clear()
    sync.dup_index = DuplicateIndex()


def post(uuid, photo, phone="9000000001", **extra):
    return client.post(
        "/sync",
        data={"client_uuid": uuid, "phone": phone, **extra},
        files=[("photos", ("p.jpg", photo, "image/jpeg"))],
    )


def test_retry_is_idempotent(photo_factory):
    photo = photo_factory(seed=1, lat=22.57, lon=88.36, taken_at=datetime(2026, 11, 5))
    first = post("uuid-1", photo).json()
    again = post("uuid-1", photo).json()
    assert first == again
    assert len(sync.results) == 1


def test_resent_photo_with_new_uuid_is_flagged(photo_factory):
    photo = photo_factory(seed=2, lat=22.57, lon=88.36, taken_at=datetime(2026, 11, 5))
    post("uuid-1", photo)
    second = post("uuid-2", photo, phone="9000000009").json()
    assert second["status"] == "flagged"
    assert second["checks"]["duplicate_of"] == "uuid-1"


def test_gps_outside_zone_not_auto_verified(photo_factory):
    photo = photo_factory(seed=3, lat=28.61, lon=77.20, taken_at=datetime(2026, 11, 5))
    body = post("uuid-3", photo).json()
    assert body["checks"]["gps_in_zone"] is False
    assert body["status"] != "auto_verified"
    assert "gps_outside_zone" in body["flags"]


def test_device_gps_used_when_exif_missing(photo_factory):
    body = post("uuid-4", photo_factory(seed=4), device_lat="22.57", device_lon="88.36").json()
    assert body["checks"]["gps_in_zone"] is True
    assert "exif_gps_missing" in body["flags"]


def test_get_verification(photo_factory):
    post("uuid-5", photo_factory(seed=5))
    assert client.get("/claims/uuid-5/verification").status_code == 200
    assert client.get("/claims/nope/verification").status_code == 404
