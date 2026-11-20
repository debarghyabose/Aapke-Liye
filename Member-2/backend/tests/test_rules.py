"""Phase 3: status machine, locking, submit validation, duplicates, losses, rules, UTC."""
import copy
import json
import re

import pytest

from app.services import relief
from app.services.validation import normalize_phone
from conftest import AI_RESPONSE, JPEG, STAFF, WEBM, new_claim, submitted_claim

UTC_Z = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z")


def test_status_machine(client):
    cid, _ = submitted_claim(client)
    put = lambda s: client.put(f"/status/{cid}", headers=STAFF, json={"status": s})  # noqa: E731
    assert put("Approved").status_code == 409            # must be Verified first
    assert put("Paid").status_code == 409
    assert put("Draft").status_code == 409
    assert put("Verified").status_code == 200
    assert put("Verified").status_code == 409            # no self-transition
    assert put("Approved").status_code == 200
    assert put("Rejected").status_code == 409            # only from Submitted/Verified
    assert put("Paid").status_code == 200
    assert put("Rejected").status_code == 409
    assert put("Bogus").status_code == 422


@pytest.mark.parametrize("start", ["Submitted", "Verified"])
def test_reject_allowed_from_submitted_or_verified(client, start):
    cid, _ = submitted_claim(client)
    if start == "Verified":
        client.put(f"/status/{cid}", headers=STAFF, json={"status": "Verified"})
    r = client.put(f"/status/{cid}", headers=STAFF, json={"status": "Rejected", "note": "dup"})
    assert r.status_code == 200 and r.json()["status"] == "Rejected"


def test_staff_cannot_move_a_draft(client):
    cid, _ = new_claim(client)
    r = client.put(f"/status/{cid}", headers=STAFF, json={"status": "Submitted"})
    assert r.status_code == 409


def test_edits_locked_after_submit(client):
    cid, h = submitted_claim(client)
    assert client.patch(f"/claims/{cid}", headers=h, json={"fields": {"name": "X"}}).status_code == 409
    assert client.post(f"/claims/{cid}/audio", headers=h,
                       files={"audio": ("a.webm", WEBM, "audio/webm")}).status_code == 409
    assert client.post(f"/claims/{cid}/photos", headers=h,
                       files={"photo": ("p.jpg", JPEG, "image/jpeg")}).status_code == 409
    assert client.post(f"/claims/{cid}/audio/retry", headers=h).status_code == 409
    assert client.post(f"/claims/{cid}/submit", headers=h).status_code == 409


def test_submit_lists_missing_fields(client):
    cid, h = new_claim(client)
    r = client.post(f"/claims/{cid}/submit", headers=h)
    assert r.status_code == 422
    assert r.json()["detail"]["missing_fields"] == [
        "name", "phone", "village", "district", "state", "date_of_incident", "losses"]

    client.patch(f"/claims/{cid}", headers=h, json={"fields": {
        "name": "Rina Das", "village": "Gosaba", "district": "South 24 Parganas",
        "state": "West Bengal", "phone": "12345", "date_of_incident": "2099-01-01",
        "losses": [{"category": "house", "item": "hut_damaged"}]}})
    detail = client.post(f"/claims/{cid}/submit", headers=h).json()["detail"]
    assert detail["missing_fields"] == []
    assert set(detail["invalid_fields"]) == {"phone", "date_of_incident"}


def test_submit_normalizes_phone(client):
    cid, h = new_claim(client)
    client.post(f"/claims/{cid}/audio", headers=h, files={"audio": ("a.webm", WEBM, "audio/webm")})
    client.patch(f"/claims/{cid}", headers=h, json={"fields": {
        "phone": "+91 98000-00000", "date_of_incident": "2026-11-15"}})
    r = client.post(f"/claims/{cid}/submit", headers=h)
    assert r.status_code == 200 and r.json()["fields"]["phone"] == "9800000000"


@pytest.mark.parametrize("raw, ok", [
    ("9800000000", True), ("+919800000000", True), ("09800000000", True),
    ("98000 00000", True), ("5800000000", False), ("980000000", False), ("abc", False)])
def test_phone_rule(raw, ok):
    assert (normalize_phone(raw) is not None) == ok


def test_patch_rejects_unknown_or_bad_fields(client):
    cid, h = new_claim(client)
    assert client.patch(f"/claims/{cid}", headers=h,
                        json={"fields": {"is_admin": True}}).status_code == 422
    assert client.patch(f"/claims/{cid}", headers=h, json={"fields": {"losses": [
        {"category": "house", "item": "hut_damaged", "quantity": "lots"}]}}).status_code == 422
    assert client.patch(f"/claims/{cid}", headers=h, json={"fields": {
        "date_of_incident": "yesterday"}}).status_code == 422


def test_same_claim_photo_retry_is_idempotent(client):
    cid, h = new_claim(client)
    first = client.post(f"/claims/{cid}/photos", headers=h,
                        files={"photo": ("p.jpg", JPEG + b"retry", "image/jpeg")}).json()
    again = client.post(f"/claims/{cid}/photos", headers=h,
                        files={"photo": ("p.jpg", JPEG + b"retry", "image/jpeg")})
    assert again.status_code == 200
    assert again.json()["photos"] == first["photos"]          # no second photo, no flag
    staff = client.get(f"/staff/claims/{cid}", headers=STAFF).json()
    assert staff["photos"][0]["duplicate_of_claim_id"] is None


def test_cross_claim_duplicate_is_for_officials_only(client):
    photo = JPEG + b"cross-claim"
    cid1, h1 = new_claim(client)
    cid2, h2 = new_claim(client)
    client.post(f"/claims/{cid1}/photos", headers=h1, files={"photo": ("p.jpg", photo, "image/jpeg")})
    r = client.post(f"/claims/{cid2}/photos", headers=h2,
                    files={"photo": ("p.jpg", photo, "image/jpeg")})
    victim_view = json.dumps(r.json())
    assert "duplicate" not in victim_view and cid1 not in victim_view

    staff = client.get(f"/staff/claims/{cid2}", headers=STAFF)
    assert staff.json()["photos"][0]["duplicate_of_claim_id"] == cid1
    assert client.get(f"/staff/claims/{cid2}").status_code == 401
    assert client.get(f"/staff/claims/{cid2}", headers=h2).status_code == 401


def test_unmatched_losses_are_reported(client, services):
    ai = copy.deepcopy(AI_RESPONSE)
    ai["claim"]["losses"].append({"type": "vehicle", "description": "trawler"})
    ai["claim"]["losses"].append({"type": "livestock", "animal": "elephant", "count": 1})
    services.m1.respond(json=ai)
    cid, h = new_claim(client)
    relief_out = client.post(f"/claims/{cid}/audio", headers=h,
                             files={"audio": ("a.webm", WEBM, "audio/webm")}).json()["relief"]
    reasons = [u["reason"] for u in relief_out["unmatched"]]
    assert reasons == ["Unknown category 'vehicle'", "Unknown item 'elephant' in 'livestock'"]
    assert len(relief_out["lines"]) == 5


def test_invalid_member1_fields_are_skipped_not_crashing(client, services):
    ai = copy.deepcopy(AI_RESPONSE)
    ai["claim"]["losses"] = [{"type": "livestock", "animal": "cow", "count": "two"}]
    ai["claim"]["unexpected"] = "ignored"
    services.m1.respond(json=ai)
    cid, h = new_claim(client)
    r = client.post(f"/claims/{cid}/audio", headers=h, files={"audio": ("a.webm", WEBM, "audio/webm")})
    assert r.status_code == 200
    assert "losses" not in r.json()["fields"] and "unexpected" not in r.json()["fields"]
    assert r.json()["fields"]["name"] == "Rina Das"


@pytest.mark.parametrize("broken, message", [
    ({"categories": {}}, "version"),
    ({"version": "x", "categories": {}}, "non-empty"),
    ({"version": "x", "categories": {"house": {"items": {"a": 1}}}}, "unit"),
    ({"version": "x", "categories": {"house": {"unit": "u", "items": {"a": "1000"}}}}, "number"),
    ({"version": "x", "categories": {"c": {"unit": "u", "items": {"a": 1},
                                           "max_amount": {"b": 5}}}}, "unknown item"),
])
def test_rules_structure_is_validated(broken, message):
    with pytest.raises(ValueError, match=message):
        relief.validate_rules(broken)


def test_health_warns_about_sample_rules(client):
    body = client.get("/health").json()
    assert body["rules_version"].startswith("sample")
    assert any("SAMPLE" in w for w in body["warnings"])
    assert client.post("/claims", json={}).status_code == 422   # sanity: app still strict


def test_timestamps_are_utc_with_z(client):
    cid, h = new_claim(client)
    client.post(f"/claims/{cid}/photos", headers=h, files={"photo": ("p.jpg", JPEG + b"tz", "image/jpeg")},
                data={"taken_at": "2026-11-20T10:00:00+05:30"})
    claim = client.get(f"/claims/{cid}", headers=h).json()
    for value in [claim["created_at"], claim["updated_at"], claim["consent_given_at"],
                  claim["history"][0]["at"], claim["photos"][0]["taken_at"]]:
        assert UTC_Z.fullmatch(value), value
    assert claim["photos"][0]["taken_at"] == "2026-11-20T04:30:00.000Z"   # IST -> UTC
    status = client.get(f"/status/{cid}", headers=h).json()
    assert UTC_Z.fullmatch(status["updated_at"]) and UTC_Z.fullmatch(status["timeline"][0]["at"])


def test_bad_taken_at_is_rejected(client):
    cid, h = new_claim(client)
    r = client.post(f"/claims/{cid}/photos", headers=h,
                    files={"photo": ("p.jpg", JPEG, "image/jpeg")}, data={"taken_at": "noon"})
    assert r.status_code == 422
