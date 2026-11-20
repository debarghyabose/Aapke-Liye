"""Dashboard data (for Member 5), fed through /verify the way Member 2 calls it."""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import config, store, sync, verify
from app.duplicates import DuplicateIndex
from app.main import app
from app.schemas import DamageResult

client = TestClient(app)


def damage(type_="house", severity=0.8, real=True, sdrf="kutcha house fully damaged"):
    return DamageResult(type=type_, severity=severity, description="x", sdrf_category=sdrf, real_photo=real)


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    sync.dup_index = DuplicateIndex()
    monkeypatch.setattr(verify, "assess_damage", lambda p: damage())


def send(photo, claim_id, monkeypatch=None, result=None, **data):
    if result is not None:
        monkeypatch.setattr(verify, "assess_damage", lambda p: result)
    data = {k: str(v) for k, v in {"claim_id": claim_id, **data}.items() if v is not None}
    r = client.post("/verify", files={"photo": ("p.jpg", photo, "image/jpeg")}, data=data)
    assert r.status_code == 200, r.text
    return r.json()


def test_empty_dashboard():
    assert client.get("/dashboard/summary").json()["claims"] == 0
    assert client.get("/dashboard/claims.geojson").json() == {"type": "FeatureCollection", "features": []}
    assert client.get("/dashboard/fraud-flags").json() == {"count": 0, "items": []}


def test_claim_point_has_score_band_and_location(photo_factory):
    send(photo_factory(seed=1, lat=22.57, lon=88.36, taken_at=datetime(2026, 11, 5)), "AL-1")
    fc = client.get("/dashboard/claims.geojson").json()
    f = fc["features"][0]
    assert f["geometry"]["coordinates"] == pytest.approx([88.36, 22.57], abs=1e-3)
    p = f["properties"]
    assert p["claim_id"] == "AL-1"
    assert p["damage_score"] == 80 and p["severity_band"] == "severe"
    assert p["damage_types"] == ["house"] and p["gps_source"] == "exif"
    assert p["flags"] == []


def test_claim_with_several_photos_is_one_point_with_max_score(photo_factory, monkeypatch):
    send(photo_factory(seed=2, lat=22.57, lon=88.36), "AL-1", monkeypatch, damage(severity=0.3))
    send(photo_factory(seed=3), "AL-1", monkeypatch, damage("crop", 0.6, sdrf="crop loss above 33%"))
    features = client.get("/dashboard/claims.geojson").json()["features"]
    assert len(features) == 1
    p = features[0]["properties"]
    assert p["photos"] == 2 and p["damage_score"] == 60 and p["severity_band"] == "moderate"
    assert set(p["damage_types"]) == {"house", "crop"}
    assert "no_location" not in p["flags"]  # located by its first photo


def test_duplicate_pair_shows_in_fraud_queue(photo_factory):
    photo = photo_factory(seed=4, lat=22.57, lon=88.36)
    send(photo, "AL-1")
    send(photo, "AL-2")
    items = client.get("/dashboard/fraud-flags").json()["items"]
    dup = [i for i in items if i["type"] == "duplicate_photo"]
    assert len(dup) == 1
    assert dup[0]["claim_id"] == "AL-2" and dup[0]["other_claim_id"] == "AL-1"
    assert dup[0]["hash_distance"] == 0
    assert client.get("/dashboard/summary").json()["flags"]["duplicate_photo"] == 1


def test_gps_mismatch_and_fake_photo_flags(photo_factory, monkeypatch):
    send(photo_factory(seed=5, lat=22.57, lon=88.36), "AL-3", monkeypatch, damage(real=False), lat=22.95, lon=88.80)
    kinds = {i["type"]: i for i in client.get("/dashboard/fraud-flags").json()["items"]}
    assert kinds["gps_mismatch"]["distance_km"] > 50
    assert "not_genuine_photo" in kinds


def test_filters(photo_factory, monkeypatch):
    t = datetime(2026, 11, 5)
    send(photo_factory(seed=6, lat=22.57, lon=88.36, taken_at=t), "AL-1", monkeypatch, damage(severity=0.2))
    send(photo_factory(seed=7, lat=22.60, lon=88.40, taken_at=t), "AL-2", monkeypatch, damage(severity=0.9))
    high = client.get("/dashboard/claims.geojson", params={"min_score": 50}).json()["features"]
    assert [f["properties"]["claim_id"] for f in high] == ["AL-2"]
    assert client.get("/dashboard/claims.geojson", params={"flagged_only": True}).json()["features"] == []


def test_heatmap_groups_nearby_claims(photo_factory, monkeypatch):
    send(photo_factory(seed=8, lat=22.5700, lon=88.3600), "AL-1")
    send(photo_factory(seed=9, lat=22.5702, lon=88.3602), "AL-2", monkeypatch, damage(severity=0.4))
    send(photo_factory(seed=10, lat=22.70, lon=88.50), "AL-3")
    cells = client.get("/dashboard/heatmap.geojson", params={"cell_km": 1}).json()["features"]
    counts = sorted(c["properties"]["claims"] for c in cells)
    assert counts == [1, 2]
    two = next(c for c in cells if c["properties"]["claims"] == 2)["properties"]
    assert two["max_damage_score"] == 80 and two["weight"] == 1.2 and two["severe_claims"] == 1


def test_summary_counts(photo_factory, monkeypatch):
    send(photo_factory(seed=11, lat=22.57, lon=88.36), "AL-1")
    send(photo_factory(seed=12), "AL-2", monkeypatch, damage("none", 0.0, sdrf="not applicable"))
    s = client.get("/dashboard/summary").json()
    assert s["claims"] == 2 and s["photos"] == 2 and s["claims_without_location"] == 1
    assert s["by_severity"]["severe"] == 1 and s["by_severity"]["none"] == 1
    assert s["by_damage_type"] == {"house": 1}


def test_dashboard_key_required_when_set(monkeypatch):
    monkeypatch.setattr(config, "DASHBOARD_API_KEY", "secret-dashboard-key")
    for path in ("/dashboard/summary", "/dashboard/claims.geojson",
                 "/dashboard/heatmap.geojson", "/dashboard/fraud-flags"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers={"X-Dashboard-Key": "wrong"}).status_code == 401
        assert client.get(path, headers={"X-Dashboard-Key": "secret-dashboard-key"}).status_code == 200


def test_browser_dashboard_can_read_but_not_other_sites():
    """Member 5's dashboard (opened from a file: Origin null) may read /dashboard."""
    ok = client.get("/dashboard/summary", headers={"Origin": "null"})
    assert ok.headers.get("access-control-allow-origin") == "null"
    evil = client.get("/dashboard/summary", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in evil.headers
    pre = client.options("/dashboard/summary", headers={
        "Origin": "null", "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-Dashboard-Key"})
    assert pre.status_code == 200


def test_duplicates_survive_restart(photo_factory, tmp_path):
    """Fingerprints are saved, so a re-used photo is caught after the service restarts."""
    photo = photo_factory(seed=13)
    send(photo, "AL-1")
    sync.dup_index = DuplicateIndex()                       # simulate restart: memory wiped
    sync.dup_index.load(store.get_store().hashes())         # what startup does
    assert send(photo, "AL-2")["duplicate"] is True
