"""Phase 4: the relief form PDF renders Indic text and is readable by officials."""
import copy
import io
import re

import pytest
from pypdf import PdfReader

from app.services.pdf_builder import checks, script_font
from app.services.relief import inr
from conftest import AI_RESPONSE, AI_TOTAL, COMPLETE_FIELDS, DOWN, JPEG, WEBM, new_claim


def pdf_text(pdf: bytes) -> str:
    text = "".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)
    # fpdf2 maps a shaped cluster such as "রি" to its first glyph and leaves the other
    # glyph unmapped; pypdf then emits its raw code (e.g. "\x02"). Drop those codes.
    return re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)


def test_indic_pdf(client, services):
    ai = copy.deepcopy(AI_RESPONSE)
    ai["fields"].update({"name": "রিনা দাস", "village": "गोसाबा"})
    services.m1.respond(json=ai)
    services.m3.side_effect = DOWN                      # photo stays "pending"

    cid, h = new_claim(client)
    client.post(f"/claims/{cid}/audio", headers=h, files={"audio": ("a.webm", WEBM, "audio/webm")})
    client.post(f"/claims/{cid}/photos", headers=h, files={"photo": ("p.jpg", JPEG, "image/jpeg")})
    client.patch(f"/claims/{cid}", headers=h, json={"fields": COMPLETE_FIELDS})
    assert client.post(f"/claims/{cid}/submit", headers=h).status_code == 200

    r = client.get(f"/claims/{cid}/pdf", headers=h)
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    text = pdf_text(r.content)

    for expected in [
        "রিনা দাস", "गोसाबा",                                  # Indic strings survive
        cid, "IST",
        "House – fully damaged (plains)", "Milch animal (cow/buffalo)", "Crop – rainfed",
        "Clothing (per family)", "Household Items",            # labels, Title Case
        "1,98,605", "1,20,000",                                # Indian grouping
        "Aadhaar card", "Attestation by the Gram Panchayat",   # documents + substitutes
        "Verification pending",
        "consent text version v1",
        "Estimated amount — subject to official verification",  # rules are a sample
        "Signature / Thumb impression of applicant",
    ]:
        assert expected in text, expected
    assert inr(AI_TOTAL) == "1,98,605"


@pytest.mark.parametrize("n, out", [(0, "0"), (999, "999"), (1000, "1,000"),
                                    (198605, "1,98,605"), (12000000, "1,20,00,000"),
                                    (-4500, "-4,500")])
def test_indian_number_format(n, out):
    assert inr(n) == out


def test_checks_text():
    assert checks({"status": "pending"}) == "Verification pending"
    assert checks({"status": "complete", "gps_ok": True, "timestamp_ok": True,
                   "damage_score": 0.8}) == "GPS ✓ · Time ✓ · Damage 80%"
    assert checks({"status": "complete", "gps_ok": False}) == "GPS ✗"


@pytest.mark.parametrize("text, font", [("Rina Das", "latin"), ("রিনা দাস (Rina)", "bengali"),
                                        ("गोसाबा", "devanagari"), ("சென்னை", "tamil"),
                                        ("తెలుగు", "telugu"), ("", "latin")])
def test_font_is_picked_by_script(text, font):
    assert script_font(text) == font
