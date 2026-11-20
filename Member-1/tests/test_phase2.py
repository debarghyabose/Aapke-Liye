import base64
import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)

CLAIM = {
    "session_id": "CLM-0042",
    "language": "hi",
    "claimant": {"name": "Sunita Devi", "phone": "9876543210"},
    "location": {"village": "Bahadurpur", "district": "Darbhanga", "state": "Bihar", "pincode": None},
    "disaster_type": "flood",
    "incident_date": "2026-09-02",
    "losses": [{"type": "crop", "crop_name": "paddy", "area_acres": 3, "amount_inr": 50000}],
    "documents_lost": ["ration_card", "aadhaar"],
}


def _img(color) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def test_doc_types_listed():
    types = {t["doc_type"] for t in client.get("/v1/documents/types").json()}
    assert len(types) == 9 and "rti_application" in types


def test_crop_insurance_draft_fills_and_flags():
    r = client.post("/v1/documents/draft", json={"doc_type": "insurance_crop", "claim": CLAIM,
                                                 "extra": {"insurer_name": "AIC of India"}}).json()
    assert "Sunita Devi" in r["text"]
    assert "Darbhanga" in r["text"]
    assert "Rs. 50,000" in r["text"]
    assert "paddy, 3 acres" in r["text"]
    assert "AIC of India" in r["text"]
    assert "policy_no" in r["missing_fields"]
    assert "[TO FILL: policy_no]" in r["text"]
    assert "{{" not in r["text"]


def test_every_template_renders():
    for t in client.get("/v1/documents/types").json():
        r = client.post("/v1/documents/draft", json={"doc_type": t["doc_type"], "claim": CLAIM})
        assert r.status_code == 200, t
        assert "{{" not in r.json()["text"]


def test_escalation_ladder():
    def nxt(days, done):
        return client.post("/v1/escalation/next", json={"days_pending": days, "steps_done": done}).json()

    assert nxt(10, [])["next_step"] is None
    assert nxt(31, [])["next_step"] == "followup_letter"
    assert nxt(50, ["followup_letter"])["next_step"] == "grievance"
    assert nxt(50, ["followup_letter", "grievance"])["next_step"] is None
    assert nxt(70, ["followup_letter", "grievance"])["next_step"] == "rti_application"


def test_damage_compare_mock():
    same = client.post("/v1/damage/compare", json={
        "baseline_image_base64": _img((120, 120, 120)), "damage_image_base64": _img((120, 120, 120)),
        "baseline_media_type": "image/png", "damage_media_type": "image/png"}).json()
    assert same["damage_score"] == 0 and same["level"] == "none"

    diff = client.post("/v1/damage/compare", json={
        "baseline_image_base64": _img((255, 255, 255)), "damage_image_base64": _img((0, 0, 0)),
        "baseline_media_type": "image/png", "damage_media_type": "image/png"}).json()
    assert diff["level"] == "destroyed"
    assert diff["needs_human_review"] is True  # mock confidence is low


def test_damage_rejects_bad_media_type():
    r = client.post("/v1/damage/compare", json={"baseline_image_base64": "x", "damage_image_base64": "x",
                                                "baseline_media_type": "application/pdf"})
    assert r.status_code == 400
