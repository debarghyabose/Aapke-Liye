"""Wiring between members: Member 1's claim AI (via member1_adapter), Member 5's household
caps in the relief rules, the typed-answer endpoint and the officials' claim list."""
import copy
import json

from app.services.member1_adapter import map_loss, map_missing, to_member2_answer
from app.services.relief import calculate_relief
from tests.conftest import AI_RESPONSE, AI_TOTAL, STAFF, WEBM, new_claim, submitted_claim


# ---------- Member 1 -> Member 2 translation ----------

def test_house_crop_livestock_mapping():
    assert map_loss({"type": "house", "house_kind": "pucca", "damage_level": "partial"}) == [
        {"category": "house", "item": "partially_damaged_pucca", "quantity": 1}]
    assert map_loss({"type": "house", "damage_level": "destroyed"})[0]["item"] == "fully_damaged_plain"
    crop = map_loss({"type": "crop", "crop_name": "banana", "area_acres": 2.47})[0]
    assert crop["item"] == "perennial" and crop["quantity"] == 1.0
    assert crop["damage_percent"] is None          # unknown -> official must assess
    assert map_loss({"type": "livestock", "animal": "goats", "count": 4}) == [
        {"category": "livestock", "item": "milch_small", "quantity": 4}]
    assert map_loss({"type": "death", "count": 2}) == [
        {"category": "ex_gratia", "item": "death", "quantity": 2}]


def test_unpriceable_losses_are_kept_not_dropped():
    line = map_loss({"type": "vehicle", "description": "motorbike"})[0]
    assert line["category"] == "vehicle"
    assert calculate_relief([line])["unmatched"][0]["reason"] == "Unknown category 'vehicle'"


def test_missing_paths_become_member2_names():
    assert map_missing(["claimant.name", "losses[0].area_acres", "losses[1].count",
                        "location.state", "incident_date"]) == [
        "name", "losses", "state", "date_of_incident"]


def test_follow_up_question_and_state():
    out = to_member2_answer(AI_RESPONSE)
    assert out["follow_up_questions"] == ["On which date did the flood reach your house?"]
    assert out["ai_state"]["claimant"]["name"] == "Rina Das"
    confirm = {**AI_RESPONSE, "next_question": {"field": "confirm", "text": "Is this right?"}}
    assert to_member2_answer(confirm)["follow_up_questions"] == []


def test_ai_state_is_sent_back_on_the_next_turn(client, services):
    cid, h = new_claim(client)
    client.post(f"/claims/{cid}/audio", headers=h, files={"audio": ("a.webm", WEBM, "audio/webm")})
    first = json.loads(services.m1.calls[0].request.content)
    assert first["session_id"] == cid and first["claim"] is None and first["audio_base64"]

    r = client.post(f"/claims/{cid}/text", headers=h, json={"text": "15 November, 9800000000"})
    assert r.status_code == 200
    second = json.loads(services.m1.calls[1].request.content)
    assert second["text"] == "15 November, 9800000000"
    assert second["claim"]["claimant"]["name"] == "Rina Das"   # Member 1 remembers turn 1


def test_text_endpoint_returns_503_when_member1_down(client, services):
    from tests.conftest import DOWN
    cid, h = new_claim(client)
    services.m1.side_effect = DOWN
    r = client.post(f"/claims/{cid}/text", headers=h, json={"text": "hello"})
    assert r.status_code == 503
    assert client.post(f"/claims/{cid}/text", headers=h, json={"text": ""}).status_code == 422


def test_full_total_through_member1(client, services):
    cid, h = new_claim(client)
    r = client.post(f"/claims/{cid}/audio", headers=h, files={"audio": ("a.webm", WEBM, "audio/webm")})
    assert r.json()["relief"]["total"] == AI_TOTAL
    assert r.json()["missing_fields"] == ["date_of_incident", "phone"]
    assert r.json()["relief"]["may_also_qualify"][0]["scheme_code"] == "PMAY_G_DISASTER"
    assert "ai_state" not in r.json()


# ---------- Member 5's caps (ported into relief.py) ----------

def test_livestock_caps_per_household():
    r = calculate_relief([{"category": "livestock", "item": "milch_large", "quantity": 10}])
    assert r["total"] == 3 * 37500
    r = calculate_relief([{"category": "livestock", "item": "milch_large", "quantity": 2},
                          {"category": "livestock", "item": "milch_large", "quantity": 2}])
    assert r["total"] == 3 * 37500                 # cap holds across lines


def test_one_clothing_grant_per_family():
    assert calculate_relief([{"category": "household", "item": "clothing", "quantity": 5}])["total"] == 2500


def test_zero_quantity_pays_nothing():
    r = calculate_relief([{"category": "house", "item": "fully_damaged_plain", "quantity": 0}])
    assert r["total"] == 0


def test_crop_needs_damage_percent_and_shares_2ha_cap():
    r = calculate_relief([{"category": "crop", "item": "rainfed", "quantity": 1}])
    assert r["total"] == 0 and "Damage percent needed" in r["unmatched"][0]["reason"]
    r = calculate_relief([{"category": "crop", "item": "rainfed", "quantity": 1.5, "damage_percent": 50},
                          {"category": "crop", "item": "irrigated", "quantity": 1.5, "damage_percent": 50}])
    assert r["total"] == round(1.5 * 8500) + round(0.5 * 17000)


# ---------- officials' queue ----------

def test_staff_list_shows_submitted_claims_only(client):
    draft_id, _ = new_claim(client)
    sub_id, _ = submitted_claim(client)
    assert client.get("/staff/claims").status_code == 401
    ids = [c["id"] for c in client.get("/staff/claims", headers=STAFF).json()]
    assert sub_id in ids and draft_id not in ids
    only = client.get("/staff/claims?status=Paid", headers=STAFF).json()
    assert all(c["status"] == "Paid" for c in only)


# ---------- ready-to-sign letters (Member 1 drafting) ----------

def test_member1_claim_uses_latest_review_edits():
    from app.services.member1_adapter import to_member1_claim
    c = to_member1_claim("AL-X", "bn", {"name": "Rina D.", "date_of_incident": "2026-11-15"},
                         AI_RESPONSE["claim"])
    assert c["session_id"] == "AL-X" and c["claimant"]["name"] == "Rina D."
    assert c["incident_date"] == "2026-11-15" and c["losses"] == AI_RESPONSE["claim"]["losses"]
    typed = to_member1_claim("AL-Y", "en", {"losses": [
        {"category": "livestock", "item": "milch_large", "quantity": 2}]}, None)
    assert typed["losses"] == [{"type": "livestock", "description": "milch large", "count": 2}]


def test_draft_document(client, services):
    services.m1_draft = services.post("http://member1.test/v1/documents/draft").respond(json={
        "doc_type": "rti_application", "title": "RTI", "text": "To, the PIO ... Rina Das",
        "missing_fields": ["office_name"], "template_source": "x"})
    cid, h = submitted_claim(client)
    r = client.post(f"/claims/{cid}/documents/rti_application", headers=h)
    assert r.status_code == 200 and "Rina Das" in r.json()["text"]
    sent = json.loads(services.m1_draft.calls[0].request.content)
    assert sent["doc_type"] == "rti_application" and sent["claim"]["session_id"] == cid
    assert sent["extra"]["claim_id"] == cid and "application_date" in sent["extra"]
    assert client.post(f"/claims/{cid}/documents/bogus", headers=h).status_code == 404
    assert client.post(f"/claims/{cid}/documents/grievance").status_code == 404   # no token
    services.m1_draft.side_effect = __import__("tests.conftest", fromlist=["DOWN"]).DOWN
    assert client.post(f"/claims/{cid}/documents/grievance", headers=h).status_code == 503
