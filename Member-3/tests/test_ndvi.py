"""Crop before/after check (Sentinel-2 NDVI), with a fake satellite source: offline, instant."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import config, ndvi, sync, verify
from app.duplicates import DuplicateIndex
from app.main import app
from app.schemas import DamageResult

client = TestClient(app)
T = datetime(2019, 5, 4, 9, 0)


class FakeSentinel:
    """Returns `before` for the 2-4 months window and `after` for the window around the photo."""

    def __init__(self, before, after, fail=False):
        self.before, self.after, self.fail, self.calls = before, after, fail, []

    def best(self, lat, lon, start, end, radius_m):
        self.calls.append((start, end))
        if self.fail:
            raise ConnectionError("offline")
        return self.before if end < T - timedelta(days=30) else self.after


def reading(ndvi_value, date, water=0.0):
    return {"ndvi": ndvi_value, "date": date, "water": water, "scene": "S2A_TEST"}


@pytest.fixture
def crop(monkeypatch):
    sync.dup_index = DuplicateIndex()
    monkeypatch.setattr(config, "NDVI_ENABLED", True)
    monkeypatch.setattr(config, "DISASTER_START", datetime(2019, 4, 1))  # photos here are from 2019
    monkeypatch.setattr(verify, "assess_damage", lambda p: DamageResult(
        type="crop", severity=0.7, description="Flattened paddy.", real_photo=True))

    def install(before, after, fail=False):
        src = FakeSentinel(before, after, fail)
        ndvi.set_source(src)
        return src

    yield install
    ndvi.set_source(None)


def send(photo, claim_id="AL-CROP", **data):
    data = {k: str(v) for k, v in {"claim_id": claim_id, **data}.items() if v is not None}
    r = client.post("/verify", files={"photo": ("p.jpg", photo, "image/jpeg")}, data=data)
    assert r.status_code == 200, r.text
    return r.json()


def claim_props():
    return client.get("/dashboard/claims.geojson").json()["features"][0]["properties"]


# ---------------------------------------------------------------- interpretation

@pytest.mark.parametrize("before, after, status, words", [
    (reading(0.72, "2019-03-20"), reading(0.31, "2019-05-08"), "vegetation_loss", "consistent with crop damage"),
    (reading(0.68, "2019-03-20"), reading(-0.1, "2019-05-08", water=0.8), "water_after", "under water"),
    (reading(0.18, "2019-03-20"), reading(0.15, "2019-05-08"), "little_vegetation_before", "check that a crop was growing"),
    (reading(0.70, "2019-03-20"), reading(0.66, "2019-05-08"), "no_change", "about the same"),
    (None, reading(0.3, "2019-05-08"), "no_clear_image", "no clear image before"),
    (reading(0.7, "2019-03-20"), None, "no_clear_image", "no clear image after"),
])
def test_interpret(before, after, status, words):
    r = ndvi.interpret(before, after)
    assert r["status"] == status and words in r["note"]


def test_coarse_box_hides_exact_field():
    box = ndvi.Sentinel2.coarse_box(19.8571, 85.8123)
    assert box == [85.75, 19.75, 86.0, 20.0]  # ~25 km cell, not the field


# ---------------------------------------------------------------- /verify integration

def test_crop_photo_gets_before_after_on_dashboard(crop, photo_factory):
    src = crop(reading(0.72, "2019-03-20"), reading(0.30, "2019-05-08"))
    body = send(photo_factory(seed=1, lat=19.86, lon=85.81, taken_at=T))
    assert any("Satellite crop check (Sentinel-2" in n and "started" in n for n in body["notes"])
    sat = claim_props()["crop_satellite"]
    assert sat["status"] == "vegetation_loss" and sat["before"] == 0.72 and sat["after"] == 0.30
    assert sat["date_before"] == "2019-03-20" and sat["date_after"] == "2019-05-08"
    (b_start, b_end), (a_start, a_end) = src.calls
    assert (T - b_start).days == 120 and (T - b_end).days == 45      # 2-4 months before
    assert (T - a_start).days == 10 and (a_end - T).days == 7         # around the photo


def test_unchanged_field_goes_to_fraud_queue(crop, photo_factory):
    crop(reading(0.70, "2019-03-20"), reading(0.69, "2019-05-08"))
    send(photo_factory(seed=2, lat=19.86, lon=85.81, taken_at=T))
    assert "crop_unchanged_after" in claim_props()["flags"]
    item = next(i for i in client.get("/dashboard/fraud-flags").json()["items"] if i["type"] == "crop_satellite_mismatch")
    assert item["ndvi_before"] == 0.70 and item["ndvi_after"] == 0.69 and "about the same" in item["action"]


def test_no_check_for_house_phone_gps_or_missing_time(crop, photo_factory, monkeypatch):
    src = crop(reading(0.7, "2019-03-20"), reading(0.3, "2019-05-08"))
    send(photo_factory(seed=3), "AL-A", lat=19.86, lon=85.81, taken_at="2019-05-04T03:30:00Z")  # phone GPS only
    send(photo_factory(seed=4, lat=19.86, lon=85.81), "AL-B")                                   # no capture time
    monkeypatch.setattr(verify, "assess_damage", lambda p: DamageResult(type="house", severity=0.8, real_photo=True))
    send(photo_factory(seed=5, lat=19.86, lon=85.81, taken_at=T), "AL-C")                       # not a crop
    assert src.calls == []


def test_disabled_does_nothing(crop, photo_factory, monkeypatch):
    src = crop(reading(0.7, "2019-03-20"), reading(0.3, "2019-05-08"))
    monkeypatch.setattr(config, "NDVI_ENABLED", False)
    body = send(photo_factory(seed=6, lat=19.86, lon=85.81, taken_at=T))
    assert src.calls == [] and not any("Sentinel-2" in n for n in body["notes"])


def test_image_service_down_is_recorded_not_crashed(crop, photo_factory):
    crop(None, None, fail=True)
    send(photo_factory(seed=7, lat=19.86, lon=85.81, taken_at=T))
    sat = claim_props()["crop_satellite"]
    assert sat["status"] == "error" and "could not reach" in sat["note"]


def test_after_window_never_starts_before_the_disaster(crop, photo_factory, monkeypatch):
    """Photo 2 days after the cyclone: the 'after' image must be from after the cyclone."""
    monkeypatch.setattr(config, "DISASTER_START", datetime(2019, 5, 3))
    src = crop(reading(0.7, "2019-03-20"), reading(0.3, "2019-05-08"))
    send(photo_factory(seed=8, lat=19.86, lon=85.81, taken_at=datetime(2019, 5, 5, 9, 0)))
    after_start = src.calls[1][0]
    assert after_start == datetime(2019, 5, 3)
