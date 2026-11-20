"""WhatsApp bot: conversation flow with a fake Member 2 and a fake Twilio (no network)."""
import asyncio

import pytest
from fastapi.testclient import TestClient

from app import config, whatsapp
from app.whatsapp import Bot, Incoming, Member2Error, twilio_signature

PHONE = "whatsapp:+919812345678"


class FakeTwilio:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []
        self.media: dict[str, bytes] = {}

    async def send(self, to, body):
        self.sent.append((to, body))

    async def download(self, url):
        return self.media[url]

    def last(self) -> str:
        return self.sent[-1][1]


class FakeMember2:
    def __init__(self):
        self.calls = []
        self.claim = {"id": "C-1", "claim_token": "secret-token", "status": "Draft", "fields": {},
                      "missing_fields": [], "follow_up_questions": [], "relief": None, "photos": []}
        self.audio_down = False
        self.submit_error = None
        self.state = "Draft"
        self.timeline = [{"status": "Draft", "note": None}]

    async def create_claim(self, language):
        self.calls.append(("create", language))
        return dict(self.claim)

    async def set_phone(self, claim_id, token, phone):
        self.calls.append(("phone", phone))
        assert token == "secret-token"

    async def upload_audio(self, claim_id, token, data, ctype):
        self.calls.append(("audio", ctype, data))
        if self.audio_down:
            raise Member2Error(503, "AI down")
        return {**self.claim, "fields": {"name": "Rina Das", "village": "Satbhaya", "losses": [{"item": "house"}]},
                "missing_fields": ["district"], "relief": {"total": 120000}}

    async def retry_audio(self, claim_id, token):
        raise Member2Error(409, "No recording is waiting to be processed")

    async def upload_photo(self, claim_id, token, data, ctype, lat, lon):
        self.calls.append(("photo", lat, lon))
        self.claim["photos"].append({})
        return self.claim

    async def submit(self, claim_id, token):
        if self.submit_error:
            raise self.submit_error
        self.state = "Submitted"
        return {**self.claim, "status": "Submitted", "relief": {"total": 120000}}

    async def status(self, claim_id, token):
        return {"claim_id": claim_id, "status": self.state, "timeline": self.timeline}


@pytest.fixture
def bot(temp_store):
    return Bot(temp_store, FakeMember2(), FakeTwilio())


def say(bot, text="", **kw):
    asyncio.run(bot.handle(Incoming(phone=PHONE, text=text, **kw)))
    return bot.twilio.last()


def start(bot, lang="1"):
    say(bot, "hi")
    say(bot, lang)
    return say(bot, "YES")


def test_first_message_asks_language_then_consent(bot):
    assert "English" in say(bot, "hello")
    assert "Reply *YES*" in say(bot, "1")
    assert bot.m2.calls == []                  # nothing filed before consent
    assert "Please reply *YES*" in say(bot, "maybe")


def test_consent_creates_claim_and_adds_whatsapp_number(bot, temp_store):
    reply = start(bot)
    assert "*C-1*" in reply
    assert ("create", "en") in bot.m2.calls and ("phone", "+919812345678") in bot.m2.calls
    s = temp_store.wa_get(PHONE)
    assert s["step"] == "claim" and s["claim_id"] == "C-1"
    assert "secret-token" not in s["token_enc"]     # claim token stored encrypted


def test_hindi_flow(bot):
    assert "हिन्दी" in say(bot, "hi")
    assert "हाँ" in say(bot, "2")
    assert "दावा नंबर" in say(bot, "हाँ")
    assert bot.m2.calls[0] == ("create", "hi")


def test_voice_note_is_sent_to_member2_and_summarised(bot):
    start(bot)
    bot.twilio.media["https://m/1"] = b"OggS..."
    say(bot, media=[("https://m/1", "audio/ogg")])
    texts = [b for _, b in bot.twilio.sent[-3:]]
    assert texts[0].startswith("🎧")
    assert "Rina Das" in texts[1] and "₹120000" in texts[1]
    assert "district" in texts[2]
    assert ("audio", "audio/ogg", b"OggS...") in bot.m2.calls


def test_voice_note_when_ai_is_down(bot):
    start(bot)
    bot.m2.audio_down = True
    bot.twilio.media["u"] = b"x"
    assert "RETRY" in say(bot, media=[("u", "audio/ogg")])
    assert "no voice note waiting" in say(bot, "retry")


def test_location_then_photo_carries_location(bot):
    start(bot)
    assert "Location saved" in say(bot, lat=19.81, lon=85.83)
    bot.twilio.media["p"] = b"jpeg"
    assert "Photo 1 saved" in say(bot, media=[("p", "image/jpeg")])
    assert ("photo", 19.81, 85.83) in bot.m2.calls


def test_photo_without_location_gets_a_tip(bot):
    start(bot)
    bot.twilio.media["p"] = b"jpeg"
    say(bot, media=[("p", "image/jpeg")])
    assert "share your location" in bot.twilio.sent[-2][1]
    assert ("photo", None, None) in bot.m2.calls


def test_submit_missing_fields_then_ok(bot):
    start(bot)
    bot.m2.submit_error = Member2Error(422, {"missing_fields": ["district", "losses"], "invalid_fields": {}})
    assert "district, what you lost" in say(bot, "SUBMIT")
    bot.m2.submit_error = None
    assert "submitted" in say(bot, "submit") and "₹120000" in bot.twilio.last()


def test_status_updates_are_sent_once(bot, temp_store):
    start(bot)
    say(bot, "submit")
    assert asyncio.run(bot.check_statuses()) == 0          # we already told them "Submitted"
    bot.m2.state = "Verified"
    bot.m2.timeline = [{"status": "Verified", "note": "Field visit done"}]
    assert asyncio.run(bot.check_statuses()) == 1
    assert "now *Verified*" in bot.twilio.last() and "Field visit done" in bot.twilio.last()
    assert asyncio.run(bot.check_statuses()) == 0
    assert "*Verified*" in say(bot, "status")


def test_new_starts_over(bot, temp_store):
    start(bot)
    assert "English" in say(bot, "NEW")
    assert temp_store.wa_get(PHONE)["claim_id"] is None


def test_non_indian_number_not_added(bot):
    asyncio.run(bot.handle(Incoming(phone="whatsapp:+14155550100", text="hi")))
    asyncio.run(bot.handle(Incoming(phone="whatsapp:+14155550100", text="1")))
    asyncio.run(bot.handle(Incoming(phone="whatsapp:+14155550100", text="yes")))
    assert not any(c[0] == "phone" for c in bot.m2.calls)


def test_member2_failure_gives_friendly_error(bot):
    async def broken(language):
        raise Member2Error(503, "down")
    bot.m2.create_claim = broken
    say(bot, "hi"); say(bot, "1")
    assert "something went wrong" in say(bot, "yes")


# ---------------------------------------------------------------- webhook


@pytest.fixture
def twilio_on(monkeypatch, bot):
    monkeypatch.setattr(config, "TWILIO_ACCOUNT_SID", "AC" + "0" * 32)
    monkeypatch.setattr(config, "TWILIO_AUTH_TOKEN", "test-auth-token")
    monkeypatch.setattr(config, "TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    monkeypatch.setattr(config, "PUBLIC_BASE_URL", "https://bot.example.test")
    monkeypatch.setattr(config, "WHATSAPP_STATUS_POLL_SECONDS", 0)
    whatsapp.set_bot(bot)
    yield bot
    whatsapp.set_bot(None)


def _client():
    from app.main import app
    return TestClient(app)


def test_webhook_off_without_twilio_settings():
    assert _client().post("/whatsapp/webhook", data={"From": PHONE}).status_code == 404


def test_webhook_rejects_unsigned_requests(twilio_on):
    r = _client().post("/whatsapp/webhook", data={"From": PHONE, "Body": "hi"},
                       headers={"X-Twilio-Signature": "forged"})
    assert r.status_code == 403
    assert twilio_on.twilio.sent == []


def test_webhook_accepts_signed_request_and_replies(twilio_on):
    form = {"From": PHONE, "Body": "hi", "NumMedia": "0"}
    sig = twilio_signature("https://bot.example.test/whatsapp/webhook", form, "test-auth-token")
    r = _client().post("/whatsapp/webhook", data=form, headers={"X-Twilio-Signature": sig})
    assert r.status_code == 200 and "<Response>" in r.text
    assert "English" in twilio_on.twilio.last()


def test_signature_matches_twilio_documentation_example():
    # Twilio's docs example; expected value computed with the official twilio library's
    # RequestValidator.compute_signature (the library is not a dependency of this service).
    params = {"CallSid": "CA1234567890ABCDE", "Caller": "+12349013030", "Digits": "1234",
              "From": "+12349013030", "To": "+18005551212"}
    assert twilio_signature("https://mycompany.com/myapp.php?foo=1&bar=2", params,
                            "12345") == "0/KCTR6DLpKmkAf8muzZqo1nDgQ="


def test_incoming_from_form_parses_media_and_location():
    m = Incoming.from_form({"From": PHONE, "NumMedia": "2", "MediaUrl0": "a", "MediaContentType0": "audio/ogg; codecs=opus",
                            "MediaUrl1": "b", "MediaContentType1": "image/jpeg", "Latitude": "19.8", "Longitude": "85.8"})
    assert m.media == [("a", "audio/ogg"), ("b", "image/jpeg")] and (m.lat, m.lon) == (19.8, 85.8)
