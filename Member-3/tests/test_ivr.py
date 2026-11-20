"""IVR line: call flow with a fake Member 2 (no network, no Twilio)."""
import asyncio
import re
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from app import config, ivr
from app.ivr import Ivr, spell
from app.whatsapp import Member2Error, twilio_signature

CALLER = "+919812345678"


class FakeMember2:
    def __init__(self):
        self.calls = []
        self.state = "Draft"
        self.missing = ["district", "date_of_incident"]
        self.n = 0

    async def create_claim(self, language):
        self.n += 1
        self.calls.append(("create", language))
        return {"id": f"AL-XY{self.n}", "claim_token": "tok", "status": "Draft"}

    async def set_phone(self, claim_id, token, phone):
        self.calls.append(("phone", phone))

    async def upload_audio(self, claim_id, token, data, ctype):
        self.calls.append(("audio", claim_id, ctype, data))
        return {"missing_fields": self.missing}

    async def submit(self, claim_id, token):
        self.calls.append(("submit", claim_id))
        self.state = "Submitted"
        return {"status": "Submitted"}

    async def status(self, claim_id, token):
        return {"status": self.state, "timeline": []}

    async def get_claim(self, claim_id, token):
        return {"missing_fields": self.missing if self.state == "Draft" else []}


@pytest.fixture
def line(temp_store):
    deleted = []

    async def download(url):
        assert url.endswith(".wav")
        return b"RIFF-voice"

    async def delete(sid):
        deleted.append(sid)

    i = Ivr(temp_store, FakeMember2(), download, delete)
    i.deleted = deleted
    return i


def spoken(xml: str) -> str:
    return " ".join(e.text or "" for e in ET.fromstring(xml).iter("Say"))


def run(coro):
    return asyncio.run(coro)


def new_call(line, sid="CA1", lang_digit="1"):
    run(line.incoming(sid, CALLER))
    line.language(sid, CALLER, lang_digit)
    return run(line.consent(sid, CALLER, {"1": "en", "2": "hi", "3": "bn"}[lang_digit], "1"))


def test_spell_reads_claim_id_character_by_character():
    assert spell("AL-PZ5") == "A, L, P, Z, 5"


def test_new_caller_hears_language_menu(line):
    xml = run(line.incoming("CA1", CALLER))
    assert "press 1" in spoken(xml) and "2 दबाएं" in spoken(xml) and "3 টিপুন" in spoken(xml)
    assert ET.fromstring(xml).find("Gather").get("action") == "/ivr/language"


def test_language_then_consent_creates_claim_and_records(line):
    xml = line.language("CA1", CALLER, "2")
    assert "1 दबाएं" in spoken(xml)
    assert ET.fromstring(xml).find("Gather").get("action") == "/ivr/consent?lang=hi"
    assert line.m2.calls == []                     # nothing filed before consent
    xml = run(line.consent("CA1", CALLER, "hi", "1"))
    assert "A, L, X, Y, 1" in spoken(xml)
    rec = ET.fromstring(xml).find("Record")
    assert rec.get("action") == "/ivr/recorded?lang=hi" and rec.get("finishOnKey") == "#"
    assert ("create", "hi") in line.m2.calls and ("phone", "+919812345678") in line.m2.calls
    assert ET.fromstring(xml).find("Say").get("language") == "hi-IN"


def test_no_consent_files_nothing(line):
    line.language("CA1", CALLER, "1")
    assert "cannot file a claim" in spoken(run(line.consent("CA1", CALLER, "en", "2")))
    assert line.m2.calls == []


def test_recording_is_processed_then_deleted(line, temp_store):
    new_call(line)
    xml, process = line.recorded("CA1", "en", "https://api.twilio.com/rec/RE1", 30)
    assert process and "Thank you" in spoken(xml)
    assert temp_store.ivr_get("CA1")["processing"] == 1
    run(line.process_recording("CA1", "https://api.twilio.com/rec/RE1", "RE1"))
    assert ("audio", "AL-XY1", "audio/wav", b"RIFF-voice") in line.m2.calls
    assert not any(c[0] == "submit" for c in line.m2.calls)   # details still missing
    assert line.deleted == ["RE1"] and temp_store.ivr_get("CA1")["processing"] == 0


def test_complete_recording_submits_claim(line):
    new_call(line)
    line.m2.missing = []
    line.recorded("CA1", "en", "https://x/rec", 30)
    run(line.process_recording("CA1", "https://x/rec", "RE1"))
    assert ("submit", "AL-XY1") in line.m2.calls


def test_silence_is_not_processed(line):
    new_call(line)
    xml, process = line.recorded("CA1", "en", "https://x/rec", 1)
    assert not process and "did not hear" in spoken(xml)


def test_returning_caller_hears_missing_details_and_can_record_more(line):
    new_call(line)
    line.recorded("CA1", "en", "https://x/rec", 30)
    run(line.process_recording("CA1", "https://x/rec"))
    said = spoken(run(line.incoming("CA2", CALLER)))
    assert "A, L, X, Y, 1 is: not submitted yet" in said
    assert "district, date it happened" in said and "press 1" in said
    xml = line.menu("CA2", CALLER, "1")
    assert ET.fromstring(xml).find("Record") is not None
    line.recorded("CA2", "en", "https://x/rec2", 20)
    run(line.process_recording("CA2", "https://x/rec2"))
    assert [c[1] for c in line.m2.calls if c[0] == "audio"] == ["AL-XY1", "AL-XY1"]   # same claim


def test_returning_caller_hears_status_after_submission(line):
    new_call(line)
    line.m2.state = "Approved"
    said = spoken(run(line.incoming("CA2", CALLER)))
    assert "is: Approved" in said and "new claim, press 9" in said


def test_returning_caller_while_processing(line, temp_store):
    new_call(line)
    line.recorded("CA1", "en", "https://x/rec", 30)
    assert "still listening" in spoken(run(line.incoming("CA2", CALLER)))


def test_nine_starts_new_claim(line):
    new_call(line)
    assert ET.fromstring(line.menu("CA2", CALLER, "9")).find("Gather").get("action") == "/ivr/language"


def test_member2_down_gives_spoken_error(line):
    async def broken(language):
        raise Member2Error(503, "down")
    line.m2.create_claim = broken
    line.language("CA1", CALLER, "1")
    assert "not available" in spoken(run(line.consent("CA1", CALLER, "en", "1")))


# ---------------------------------------------------------------- HTTP

@pytest.fixture
def twilio_on(monkeypatch, line):
    monkeypatch.setattr(config, "TWILIO_ACCOUNT_SID", "AC" + "0" * 32)
    monkeypatch.setattr(config, "TWILIO_AUTH_TOKEN", "test-auth-token")
    monkeypatch.setattr(config, "PUBLIC_BASE_URL", "https://line.example.test")
    ivr.set_ivr(line)
    yield line
    ivr.set_ivr(None)


def _post(path, form):
    from app.main import app
    sig = twilio_signature("https://line.example.test" + path, form, "test-auth-token")
    return TestClient(app).post(path, data=form, headers={"X-Twilio-Signature": sig})


def test_ivr_off_without_twilio():
    from app.main import app
    assert TestClient(app).post("/ivr/voice", data={"From": CALLER}).status_code == 404


def test_unsigned_call_rejected(twilio_on):
    from app.main import app
    r = TestClient(app).post("/ivr/voice", data={"From": CALLER}, headers={"X-Twilio-Signature": "x"})
    assert r.status_code == 403


def test_full_call_over_http(twilio_on):
    base = {"CallSid": "CA9", "From": CALLER}
    assert "<Gather" in _post("/ivr/voice", base).text
    assert "consent?lang=bn" in _post("/ivr/language", {**base, "Digits": "3"}).text
    r = _post("/ivr/consent?lang=bn", {**base, "Digits": "1"})
    assert "<Record" in r.text and r.headers["content-type"].startswith("application/xml")
    r = _post("/ivr/recorded?lang=bn", {**base, "RecordingUrl": "https://x/rec", "RecordingSid": "RE9",
                                         "RecordingDuration": "25"})
    assert "ধন্যবাদ" in r.text
    assert any(c[0] == "audio" for c in twilio_on.m2.calls) and twilio_on.deleted == ["RE9"]


def test_say_text_is_xml_escaped():
    assert "&lt;b&gt;" in ivr.say("en", "<b>")
    assert re.search(r'voice="Google\.bn-IN', ivr.say("bn", "x"))
