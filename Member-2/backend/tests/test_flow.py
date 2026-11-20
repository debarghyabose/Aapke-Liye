"""End-to-end demo flow with mocks: create -> audio -> photo -> edit -> submit -> PDF -> status."""
import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["STORAGE_DIR"] = tempfile.mkdtemp()
os.environ["MEMBER1_AI_URL"] = ""
os.environ["MEMBER3_VERIFY_URL"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.relief import calculate_relief  # noqa: E402

c = TestClient(app)


def test_full_flow():
    r = c.post("/claims", json={"language": "bn"})
    assert r.status_code == 201
    cid = r.json()["id"]

    r = c.post(f"/claims/{cid}/audio", files={"audio": ("a.webm", b"fake-audio")})
    assert r.status_code == 200
    body = r.json()
    assert body["fields"]["name"] == "Rina Das"
    assert "phone" in body["missing_fields"]
    # 120000 house + 2*37500 cows + crop 0.13ha*8500=1105 + clothing 2500
    assert body["relief"]["total"] == 120000 + 75000 + 1105 + 2500
    assert body["proof_suggestions"][0]["document"] == "aadhaar"

    img = b"\xff\xd8fake-jpeg-bytes"
    r = c.post(f"/claims/{cid}/photos", files={"photo": ("p.jpg", img)},
               data={"lat": "22.16", "lon": "88.80", "taken_at": "2026-11-20T10:00:00+05:30"})
    assert r.json()["photos"][0]["verification"]["duplicate"] is False
    r = c.post(f"/claims/{cid}/photos", files={"photo": ("p2.jpg", img)})
    assert r.json()["photos"][1]["verification"]["duplicate"] is True

    r = c.patch(f"/claims/{cid}", json={"fields": {"phone": "9800000000"}})
    assert "phone" not in r.json()["missing_fields"]

    r = c.post(f"/claims/{cid}/submit")
    assert r.json()["status"] == "Submitted" and r.json()["pdf_url"]

    r = c.get(f"/claims/{cid}/pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"

    r = c.put(f"/status/{cid}", json={"status": "Verified"})
    assert [e["status"] for e in r.json()["timeline"]] == ["Draft", "Submitted", "Verified"]


def test_relief_rules():
    out = calculate_relief([
        {"category": "crop", "item": "irrigated", "quantity": 5, "damage_percent": 50},
        {"category": "crop", "item": "rainfed", "quantity": 1, "damage_percent": 20},
        {"category": "livestock", "item": "poultry", "quantity": 500},
        {"category": "boat", "item": "unknown"},
    ])
    amounts = [ln["amount"] for ln in out["lines"]]
    assert amounts == [34000, 0, 10000]   # capped at 2 ha; below 33%; poultry cap
    assert out["total"] == 44000 and len(out["unmatched"]) == 1


def test_errors():
    assert c.post("/claims", json={"language": "xx"}).status_code == 422
    assert c.get("/claims/NOPE").status_code == 404
    cid = c.post("/claims", json={"language": "en"}).json()["id"]
    assert c.post(f"/claims/{cid}/submit").status_code == 422  # no name yet
