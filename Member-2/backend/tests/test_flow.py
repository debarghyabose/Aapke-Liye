"""End-to-end flow with Members 1 and 3 mocked: create -> audio -> photo -> edit -> submit."""
import httpx

from app.config import settings
from app.services.relief import calculate_relief
from conftest import AI_RESPONSE, AI_TOTAL, COMPLETE_FIELDS, DOWN, JPEG, STAFF, WEBM, new_claim


def test_full_flow(client):
    cid, h = new_claim(client)

    r = client.post(f"/claims/{cid}/audio", headers=h,
                    files={"audio": ("a.webm", WEBM, "audio/webm;codecs=opus")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fields"]["name"] == "Rina Das"
    assert "phone" in body["missing_fields"]
    assert body["relief"]["total"] == AI_TOTAL
    assert body["proof_suggestions"][0]["document"] == "aadhaar"

    r = client.post(f"/claims/{cid}/photos", headers=h,
                    files={"photo": ("p.jpg", JPEG, "image/jpeg")},
                    data={"lat": "22.16", "lon": "88.80",
                          "taken_at": "2026-11-20T10:00:00+05:30"})
    assert r.json()["photos"][0]["verification"]["status"] == "complete"

    r = client.patch(f"/claims/{cid}", headers=h, json={"fields": COMPLETE_FIELDS})
    assert r.json()["missing_fields"] == [] and r.json()["follow_up_questions"] == []

    r = client.post(f"/claims/{cid}/submit", headers=h)
    assert r.json()["status"] == "Submitted" and r.json()["pdf_url"]

    r = client.get(f"/claims/{cid}/pdf", headers=h)
    assert r.status_code == 200 and r.content[:4] == b"%PDF"

    r = client.put(f"/status/{cid}", headers=STAFF, json={"status": "Verified"})
    assert [e["status"] for e in r.json()["timeline"]] == ["Draft", "Submitted", "Verified"]
    assert client.get(f"/status/{cid}", headers=h).json()["status"] == "Verified"


def test_member1_down_then_retry(client, services):
    cid, h = new_claim(client)
    good = services.m1.return_value
    services.m1.side_effect = DOWN

    r = client.post(f"/claims/{cid}/audio", headers=h, files={"audio": ("a.webm", WEBM, "audio/webm")})
    assert r.status_code == 503
    assert "saved" in r.json()["detail"]
    assert services.m1.call_count == 3          # 1 try + 2 retries
    recordings = client.get(f"/claims/{cid}", headers=h).json()["recordings"]
    assert [r["status"] for r in recordings] == ["pending"]   # audio kept for retry

    services.m1.side_effect = None
    services.m1.return_value = good
    r = client.post(f"/claims/{cid}/audio/retry", headers=h)
    assert r.status_code == 200
    assert r.json()["fields"]["name"] == "Rina Das"
    assert r.json()["recordings"][0]["status"] == "processed"
    assert client.post(f"/claims/{cid}/audio/retry", headers=h).status_code == 409


def test_member3_down_then_reverify(client, services):
    cid, h = new_claim(client)
    services.m3.side_effect = DOWN
    r = client.post(f"/claims/{cid}/photos", headers=h, files={"photo": ("p.jpg", JPEG, "image/jpeg")})
    assert r.status_code == 200                 # the claim is not blocked
    photo = r.json()["photos"][0]
    assert photo["verification"] == {"status": "pending"}

    url = f"/claims/{cid}/photos/{photo['id']}/reverify"
    assert client.post(url, headers=h).status_code == 503

    services.m3.side_effect = None
    r = client.post(url, headers=h)
    assert r.status_code == 200
    assert r.json()["photos"][0]["verification"]["status"] == "complete"


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


def test_errors(client):
    assert client.post("/claims", json={"language": "xx", "consent": True,
                                        "consent_text_version": "v1"}).status_code == 422
    cid, h = new_claim(client, "en")
    assert client.post(f"/claims/{cid}/submit", headers=h).status_code == 422  # no name yet


def test_member1_retries_5xx_then_succeeds(client, services):
    cid, h = new_claim(client)
    services.m1.side_effect = [httpx.Response(502), httpx.Response(503),
                               httpx.Response(200, json=AI_RESPONSE)]
    r = client.post(f"/claims/{cid}/audio", headers=h, files={"audio": ("a.webm", WEBM, "audio/webm")})
    assert r.status_code == 200 and services.m1.call_count == 3


def test_member1_4xx_is_not_retried(client, services):
    cid, h = new_claim(client)
    services.m1.respond(status_code=400)
    r = client.post(f"/claims/{cid}/audio", headers=h, files={"audio": ("a.webm", WEBM, "audio/webm")})
    assert r.status_code == 503 and services.m1.call_count == 1


def test_dev_mocks_answer_only_when_enabled(client, services, monkeypatch):
    monkeypatch.setattr(settings, "mock_services", True)
    cid, h = new_claim(client)
    r = client.post(f"/claims/{cid}/audio", headers=h, files={"audio": ("a.webm", WEBM, "audio/webm")})
    assert r.status_code == 200
    assert r.json()["transcript"].startswith("[DEV MOCK]")
    assert services.m1.call_count == 0          # no real call was made
