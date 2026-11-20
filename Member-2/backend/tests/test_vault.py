"""Document vault, DigiLocker (mock), before/after photos and the hilly-area rate."""
import io
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from pypdf import PdfReader

from app.services.relief import calculate_relief
from conftest import COMPLETE_FIELDS, DOWN, JPEG, STORAGE, WEBM, new_claim

PDF_DOC = b"%PDF-1.4\nfake aadhaar scan bytes 1234-5678-9012"
COMPARE = {"same_property": True, "damage_score": 85, "level": "destroyed",
           "damaged_items": ["roof", "walls"], "reason": "roof gone", "confidence": 0.9,
           "needs_human_review": False}


def new_household(client) -> tuple[str, dict]:
    r = client.post("/households")
    assert r.status_code == 201, r.text
    return r.json()["household_id"], {"X-Household-Token": r.json()["household_token"]}


def add_doc(client, hid, hh, doc_type="aadhaar", data=PDF_DOC, ctype="application/pdf"):
    return client.post(f"/households/{hid}/documents", headers=hh, data={"doc_type": doc_type},
                       files={"file": ("my aadhaar.pdf", data, ctype)})


def pdf_text(client, cid, h) -> str:
    pdf = client.get(f"/claims/{cid}/pdf", headers=h).content
    return " ".join(" ".join(p.extract_text().split()) for p in PdfReader(io.BytesIO(pdf)).pages)


def test_household_token_required(client):
    hid, hh = new_household(client)
    other_id, other = new_household(client)
    assert add_doc(client, hid, hh).status_code == 201
    assert client.get(f"/households/{hid}/documents").status_code == 404
    assert client.get(f"/households/{hid}/documents",
                      headers={"X-Household-Token": "wrong"}).status_code == 404
    assert client.get(f"/households/{hid}/documents", headers=other).status_code == 404
    assert client.get("/households/HH-NOPE/documents", headers=hh).status_code == 404
    assert len(client.get(f"/households/{hid}/documents", headers=hh).json()) == 1


def test_upload_rules(client):
    hid, hh = new_household(client)
    assert add_doc(client, hid, hh, doc_type="passport_photo").status_code == 422
    assert add_doc(client, hid, hh, data=b"MZ\x90 not a document").status_code == 415
    # the baseline photo must be a photo, not a PDF
    assert add_doc(client, hid, hh, doc_type="baseline_photo").status_code == 415
    r = add_doc(client, hid, hh, doc_type="baseline_photo", data=JPEG, ctype="image/jpeg")
    assert r.status_code == 201 and r.json()["content_type"] == "image/jpeg"


def test_file_is_encrypted_and_downloadable(client):
    hid, hh = new_household(client)
    doc = add_doc(client, hid, hh).json()
    files = [p for p in Path(STORAGE, "vault").iterdir() if p.is_file()]
    stored = [p.read_bytes() for p in files]
    assert stored and all(b"1234-5678-9012" not in s and s != PDF_DOC for s in stored)
    assert not any("aadhaar" in p.name for p in files)   # never the client's filename
    r = client.get(doc["file_url"], headers=hh)
    assert r.status_code == 200 and r.content == PDF_DOC


def test_delete_really_deletes(client):
    hid, hh = new_household(client)
    doc = add_doc(client, hid, hh).json()
    before = {p.name for p in Path(STORAGE, "vault").iterdir()}
    assert client.delete(f"/households/{hid}/documents/{doc['id']}", headers=hh).status_code == 204
    after = {p.name for p in Path(STORAGE, "vault").iterdir()}
    assert len(before - after) == 1                       # the encrypted file is gone
    assert client.get(f"/households/{hid}/documents", headers=hh).json() == []
    assert client.get(doc["file_url"], headers=hh).status_code == 404
    assert client.delete(f"/households/{hid}/documents/{doc['id']}", headers=hh).status_code == 404


def test_vault_aadhaar_is_not_lost(client):
    """The sprint's 'done when': Aadhaar saved before the flood -> PDF says vault, not lost."""
    hid, hh = new_household(client)
    add_doc(client, hid, hh)
    cid, h = new_claim(client)
    client.post(f"/claims/{cid}/audio", headers=h, files={"audio": ("a.webm", WEBM, "audio/webm")})
    r = client.get(f"/claims/{cid}", headers=h).json()
    assert [p["document"] for p in r["proof_suggestions"]] == ["aadhaar"]   # lost, for now

    # both tokens are needed to link
    assert client.post(f"/claims/{cid}/household", headers=h,
                       json={"household_id": hid}).status_code == 404
    assert client.post(f"/claims/{cid}/household", headers={**h, "X-Household-Token": "x"},
                       json={"household_id": hid}).status_code == 404
    r = client.post(f"/claims/{cid}/household", headers={**h, **hh}, json={"household_id": hid})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["household_id"] == hid
    assert body["documents_in_vault"] == [{"document": "aadhaar", "source": "upload"}]
    assert body["proof_suggestions"] == []

    client.patch(f"/claims/{cid}", headers=h, json={"fields": COMPLETE_FIELDS})
    assert client.post(f"/claims/{cid}/submit", headers=h).json()["proof_suggestions"] == []
    text = pdf_text(client, cid, h)
    assert "Available in vault" in text and "Document lost" not in text


def test_hilly_rate():
    house = [{"category": "house", "item": "fully_damaged_plain", "quantity": 1}]
    assert calculate_relief(house)["total"] == 120000
    assert calculate_relief(house, is_hilly=False)["total"] == 120000
    hilly = calculate_relief(house, is_hilly=True)
    assert hilly["total"] == 130000 and hilly["lines"][0]["item"] == "fully_damaged_hilly"


def test_hilly_rate_from_review_screen(client):
    cid, h = new_claim(client)
    client.post(f"/claims/{cid}/audio", headers=h, files={"audio": ("a.webm", WEBM, "audio/webm")})
    plain = client.get(f"/claims/{cid}", headers=h).json()["relief"]["total"]
    hilly = client.patch(f"/claims/{cid}", headers=h, json={"fields": {"is_hilly": True}})
    assert hilly.json()["relief"]["total"] == plain + 10000


def test_before_after_photo(client, services):
    compare = services.post("http://member1.test/v1/damage/compare").respond(json=COMPARE)
    hid, hh = new_household(client)
    add_doc(client, hid, hh, doc_type="baseline_photo", data=JPEG, ctype="image/jpeg")
    cid, h = new_claim(client)
    client.post(f"/claims/{cid}/household", headers={**h, **hh}, json={"household_id": hid})
    r = client.post(f"/claims/{cid}/photos", headers=h,
                    files={"photo": ("p.jpg", JPEG + b"after", "image/jpeg")})
    ba = r.json()["photos"][0]["verification"]["before_after"]
    assert ba["status"] == "complete" and ba["damage_score"] == 85
    sent = json.loads(compare.calls.last.request.content)   # Member 1's request shape
    assert set(sent) >= {"baseline_image_base64", "damage_image_base64",
                         "baseline_media_type", "damage_media_type"}

    compare.side_effect = DOWN                               # Member 1 down: upload still works
    r = client.post(f"/claims/{cid}/photos", headers=h,
                    files={"photo": ("q.jpg", JPEG + b"second", "image/jpeg")})
    assert r.status_code == 200
    assert r.json()["photos"][1]["verification"]["before_after"] == {"status": "unavailable"}


def test_photos_uploaded_before_linking_are_compared(client, services):
    services.post("http://member1.test/v1/damage/compare").respond(json=COMPARE)
    cid, h = new_claim(client)
    client.post(f"/claims/{cid}/photos", headers=h, files={"photo": ("p.jpg", JPEG, "image/jpeg")})
    hid, hh = new_household(client)
    add_doc(client, hid, hh, doc_type="baseline_photo", data=JPEG + b"b", ctype="image/jpeg")
    r = client.post(f"/claims/{cid}/household", headers={**h, **hh}, json={"household_id": hid})
    assert r.json()["photos"][0]["verification"]["before_after"]["level"] == "destroyed"


def test_no_baseline_no_comparison(client, services):
    compare = services.post("http://member1.test/v1/damage/compare").respond(json=COMPARE)
    cid, h = new_claim(client)
    r = client.post(f"/claims/{cid}/photos", headers=h, files={"photo": ("p.jpg", JPEG, "image/jpeg")})
    assert "before_after" not in r.json()["photos"][0]["verification"]
    assert not compare.called


def _query(url: str) -> dict:
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


def test_digilocker_mock_flow(client):
    hid, hh = new_household(client)
    assert client.get(f"/households/{hid}/digilocker/start").status_code == 404   # token needed
    start = client.get(f"/households/{hid}/digilocker/start", headers=hh).json()
    assert start["demo"] is True and start["mode"] == "mock"

    page = client.get(start["consent_url"])
    assert page.status_code == 200 and "Demo: DigiLocker mock" in page.text

    state = _query(start["consent_url"])["state"]
    r = client.get("/digilocker/callback", params={"state": state, "code": "mock-code"})
    assert r.status_code == 200 and "Demo" in r.text
    docs = client.get(f"/households/{hid}/documents", headers=hh).json()
    assert sorted(d["doc_type"] for d in docs) == ["aadhaar", "ration_card"]
    assert {d["source"] for d in docs} == {"digilocker_mock"}
    sample = client.get(docs[0]["file_url"], headers=hh).content
    assert "DEMO" in PdfReader(io.BytesIO(sample)).pages[0].extract_text()

    # a state works once only
    again = client.get("/digilocker/callback", params={"state": state, "code": "mock-code"})
    assert "expired" in again.text
    assert len(client.get(f"/households/{hid}/documents", headers=hh).json()) == 2


def test_digilocker_pdf_says_demo(client):
    hid, hh = new_household(client)
    start = client.get(f"/households/{hid}/digilocker/start", headers=hh).json()
    client.get("/digilocker/callback", params={"state": _query(start["consent_url"])["state"],
                                               "code": "mock-code"})
    cid, h = new_claim(client)
    client.post(f"/claims/{cid}/audio", headers=h, files={"audio": ("a.webm", WEBM, "audio/webm")})
    client.post(f"/claims/{cid}/household", headers={**h, **hh}, json={"household_id": hid})
    client.patch(f"/claims/{cid}", headers=h, json={"fields": COMPLETE_FIELDS})
    client.post(f"/claims/{cid}/submit", headers=h)
    assert "DigiLocker (demo)" in pdf_text(client, cid, h)


def test_digilocker_return_to_only_own_app(client):
    hid, hh = new_household(client)
    for target, expect in [("http://localhost:5173/prepare", "http://localhost:5173/prepare?"),
                           ("https://evil.example/steal", None)]:
        start = client.get(f"/households/{hid}/digilocker/start", headers=hh,
                           params={"return_to": target}).json()
        r = client.get("/digilocker/callback", follow_redirects=False,
                       params={"state": _query(start["consent_url"])["state"],
                               "error": "access_denied"})
        if expect:
            assert r.status_code == 303 and r.headers["location"].startswith(expect)
            assert "digilocker=denied" in r.headers["location"]
        else:
            assert r.status_code == 200 and "Nothing was shared" in r.text
    assert client.get(f"/households/{hid}/documents", headers=hh).json() == []
