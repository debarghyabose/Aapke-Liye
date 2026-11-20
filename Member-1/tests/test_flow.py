"""End-to-end conversation tests through the HTTP API, in mock mode."""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def turn(session, claim=None, **kw):
    body = {"session_id": session, **kw}
    if claim is not None:
        body["claim"] = claim
    r = client.post("/v1/claim/turn", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_health():
    r = client.get("/health").json()
    assert r["ok"] and r["mode"] == "mock" and len(r["languages"]) == 6


def test_first_turn_without_input_asks_name():
    r = turn("s0", language="ta")
    assert r["next_question"]["field"] == "claimant.name"
    assert r["next_question"]["text"] == "உங்கள் முழு பெயர் என்ன?"


def test_hindi_conversation_to_complete():
    r = turn("s1", language="hi", text="मेरा नाम रमेश कुमार है। पुरी जिला, ओडिशा। कल चक्रवात में मेरा "
                                        "कच्चा घर पूरी तरह टूट गया, दो लाख का नुकसान।")
    c = r["claim"]
    assert c["claimant"]["name"] == "रमेश कुमार"
    assert c["location"]["district"] == "पुरी"
    assert c["location"]["state"] == "Odisha"
    assert c["disaster_type"] == "cyclone"
    assert c["incident_date"] == (date.today() - timedelta(days=1)).isoformat()
    loss = c["losses"][0]
    assert (loss["type"], loss["house_kind"], loss["damage_level"], loss["amount_inr"]) == \
        ("house", "kutcha", "destroyed", 200000)
    assert r["status"] == "incomplete"
    assert r["next_question"]["field"] == "location.village"
    assert "गाँव" in r["next_question"]["text"]

    r = turn("s1", claim=r["claim"], text="सतपड़ा गाँव")
    assert r["claim"]["location"]["village"] == "सतपड़ा"
    assert r["next_question"]["field"] == "claimant.phone"

    r = turn("s1", claim=r["claim"], text="मेरा नंबर 9876543210 है")
    assert r["status"] == "needs_confirmation"
    assert r["next_question"]["field"] == "confirm"
    assert "₹2,00,000" in r["next_question"]["text"]

    r = turn("s1", claim=r["claim"], text="हाँ, सही है")
    assert r["status"] == "complete"
    assert r["next_question"] is None
    assert len(r["claim"]["transcripts"]) == 4


def test_english_with_button_confirm_and_correction():
    r = turn("s2", language="en", text="My name is Joseph Mathew from Kuttanad village, Alappuzha district, "
                                        "Kerala. The flood on 14/08/2026 damaged my pucca house badly. The loss "
                                        "is about 3 lakh rupees. I also lost my ration card.")
    c = r["claim"]
    assert c["claimant"]["name"] == "Joseph Mathew"
    assert c["location"] == {"village": "Kuttanad", "district": "Alappuzha", "state": "Kerala", "pincode": None}
    assert c["incident_date"] == "2026-08-14"
    assert c["losses"][0]["amount_inr"] == 300000
    assert c["losses"][0]["damage_level"] == "severe"
    assert c["documents_lost"] == ["ration_card"]
    assert [l["type"] for l in c["losses"]] == ["house"]  # "card" must not read as "car"
    assert r["missing_fields"] == ["claimant.phone"]

    r = turn("s2", claim=r["claim"], text="+91 98765 43210")
    assert r["status"] == "needs_confirmation"

    # correction during read-back overwrites the old value
    r = turn("s2", claim=r["claim"], text="No, my name is Joseph Mathews.")
    assert r["claim"]["claimant"]["name"] == "Joseph Mathews"
    assert r["status"] == "needs_confirmation"

    # "No" with nothing new -> ask what to correct
    r2 = turn("s2", claim=r["claim"], text="no")
    assert r2["next_question"]["field"] == "correction"

    # Member 4's Confirm button
    r = turn("s2", claim=r["claim"], confirmed=True)
    assert r["status"] == "complete"


def test_crop_follow_ups_in_marathi():
    r = turn("s3", language="mr", text="माझे नाव सुरेश पाटील आहे. दुष्काळामुळे माझे पीक गेले.")
    assert r["claim"]["disaster_type"] == "drought"
    assert r["next_question"]["field"] == "losses[0].crop_name"
    assert r["next_question"]["text"] == "कोणते पीक खराब झाले?"


def test_mock_mode_rejects_audio_politely():
    r = turn("s4", language="hi", audio_base64="UklGRg==")
    assert r["next_question"]["field"] == "repeat"
    assert "mock" in r["message"]
