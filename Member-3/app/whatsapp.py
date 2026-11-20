"""WhatsApp bot: file a relief claim from WhatsApp (voice note + photos + location).

Twilio calls POST /whatsapp/webhook for every message. The bot files the claim through
Member 2's API exactly like the app (create -> voice note -> photos -> submit), so Member 1's
speech AI and Member 3's photo checks run as usual. It replies through Twilio's API, and
messages people when an official changes their claim's status.

Setup: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM and PUBLIC_BASE_URL in
.env (see README "WhatsApp bot"). Without them the webhook answers 404.
"""
import asyncio
import base64
import hashlib
import hmac
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import Response

from app import config
from app.store import Store, get_store

log = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

MAX_MEDIA_BYTES = 15 * 1024 * 1024
FINAL_STATUSES = {"Paid", "Rejected"}

# ------------------------------------------------------------------ texts

WELCOME = ("🙏 *Aapke Liye* — disaster relief claims\n\n"
           "Reply with a number / नंबर भेजें / নম্বর পাঠান:\n"
           "*1* English\n*2* हिन्दी\n*3* বাংলা")
LANG_CHOICES = {"1": "en", "2": "hi", "3": "bn"}

T = {
    "en": {
        "consent": "Aapke Liye helps you claim disaster relief.\n\nWe use your voice notes, photos, "
                   "location and this phone number only to prepare your relief claim and send it to "
                   "government officials.\n\nReply *YES* to agree.",
        "need_yes": "Please reply *YES* to agree, or *NEW* to choose another language.",
        "started": "✅ Your claim number is *{claim_id}*.\n\n🎤 Send a *voice note*: your name, village, "
                   "district, state, the date it happened and what you lost.\n📍 Then *share your "
                   "location* (📎 → Location) and send *photos* of the damage.",
        "listening": "🎧 Voice note received, listening…",
        "ai_down": "We could not process your voice note right now. It is saved: send *RETRY* in a few minutes.",
        "understood": "Here is what we understood:\n{summary}",
        "questions": "Please answer in another voice note:\n{questions}",
        "missing": "Still needed: {fields}. Please send another voice note with these.",
        "ready": "All details are there 👍 Send *SUBMIT* to send your claim, or a voice note to correct something.",
        "location_saved": "📍 Location saved. Now send photos of the damage.",
        "no_location": "Tip: share your location (📎 → Location) before sending photos, so officials can check them.",
        "photo_saved": "📷 Photo {n} saved.",
        "photo_failed": "Could not save this photo: {why}",
        "send_voice": "Please answer with a *voice note* 🎤.\nCommands: *SUBMIT*, *STATUS*, *NEW*, *HELP*.",
        "help": "🎤 Voice note: tell us what happened\n📍 Location, then 📷 photos of the damage\n"
                "*SUBMIT* send the claim · *STATUS* check it · *NEW* start again",
        "submitted": "✅ Claim *{claim_id}* submitted. Estimated relief: ₹{total}.\n"
                     "We will message you here when its status changes. Send *STATUS* any time.",
        "cannot_submit": "Some details are missing or need correcting: {fields}.\n"
                         "Send a voice note with them, then *SUBMIT* again.",
        "status": "Claim *{claim_id}*: *{status}*{note}",
        "status_changed": "🔔 Update on claim *{claim_id}*: it is now *{status}*.{note}",
        "locked": "Claim *{claim_id}* is already submitted. Send *STATUS* to check it, or *NEW* for a new claim.",
        "unsupported": "Please send a voice note, a photo, your location or a command (*HELP*).",
        "nothing_to_retry": "There is no voice note waiting.",
        "error": "Sorry, something went wrong on our side. Please try again in a few minutes.",
        "fields": {"name": "name", "phone": "phone number", "village": "village", "district": "district",
                   "state": "state", "date_of_incident": "date it happened", "losses": "what you lost"},
        "statuses": {"Draft": "not submitted yet", "Submitted": "Submitted", "Verified": "Verified",
                     "Approved": "Approved", "Paid": "Paid", "Rejected": "Rejected"},
        "losses": "{n} loss(es)", "relief": "Estimated relief ₹{total}",
    },
    "hi": {
        "consent": "आपके लिए आपको आपदा राहत का दावा करने में मदद करता है।\n\nआपके वॉइस नोट, फ़ोटो, लोकेशन "
                   "और यह फ़ोन नंबर केवल आपका राहत दावा तैयार करने और सरकारी अधिकारियों को भेजने के लिए "
                   "इस्तेमाल होंगे।\n\nसहमत हैं तो *हाँ* (या YES) लिखें।",
        "need_yes": "सहमति के लिए *हाँ* लिखें, या भाषा बदलने के लिए *NEW* लिखें।",
        "started": "✅ आपका दावा नंबर *{claim_id}* है।\n\n🎤 एक *वॉइस नोट* भेजें: आपका नाम, गाँव, ज़िला, "
                   "राज्य, घटना की तारीख और क्या नुकसान हुआ।\n📍 फिर अपनी *लोकेशन भेजें* (📎 → Location) "
                   "और नुकसान की *फ़ोटो* भेजें।",
        "listening": "🎧 वॉइस नोट मिल गया, सुन रहे हैं…",
        "ai_down": "अभी आपका वॉइस नोट समझ नहीं पाए। यह सुरक्षित है: कुछ मिनट बाद *RETRY* लिखें।",
        "understood": "हमने यह समझा:\n{summary}",
        "questions": "कृपया एक और वॉइस नोट में बताएं:\n{questions}",
        "missing": "अभी चाहिए: {fields}। कृपया इनके साथ एक और वॉइस नोट भेजें।",
        "ready": "सारी जानकारी मिल गई 👍 दावा भेजने के लिए *SUBMIT* (या जमा) लिखें, या सुधार के लिए वॉइस नोट भेजें।",
        "location_saved": "📍 लोकेशन सेव हो गई। अब नुकसान की फ़ोटो भेजें।",
        "no_location": "सुझाव: फ़ोटो से पहले अपनी लोकेशन भेजें (📎 → Location), ताकि अधिकारी उनकी जाँच कर सकें।",
        "photo_saved": "📷 फ़ोटो {n} सेव हो गई।",
        "photo_failed": "यह फ़ोटो सेव नहीं हो पाई: {why}",
        "send_voice": "कृपया *वॉइस नोट* 🎤 में जवाब दें।\nकमांड: *SUBMIT*, *STATUS*, *NEW*, *HELP*",
        "help": "🎤 वॉइस नोट: क्या हुआ बताएं\n📍 लोकेशन, फिर 📷 नुकसान की फ़ोटो\n"
                "*SUBMIT* दावा भेजें · *STATUS* स्थिति देखें · *NEW* फिर से शुरू करें",
        "submitted": "✅ दावा *{claim_id}* भेज दिया गया। अनुमानित राहत: ₹{total}।\n"
                     "स्थिति बदलने पर हम यहीं संदेश भेजेंगे। कभी भी *STATUS* लिखें।",
        "cannot_submit": "कुछ जानकारी नहीं है या सुधारनी है: {fields}।\nइनके साथ वॉइस नोट भेजें, फिर *SUBMIT* लिखें।",
        "status": "दावा *{claim_id}*: *{status}*{note}",
        "status_changed": "🔔 दावा *{claim_id}* की नई स्थिति: *{status}*।{note}",
        "locked": "दावा *{claim_id}* पहले ही भेजा जा चुका है। *STATUS* से जाँचें, या नए दावे के लिए *NEW* लिखें।",
        "unsupported": "कृपया वॉइस नोट, फ़ोटो, लोकेशन या कमांड (*HELP*) भेजें।",
        "nothing_to_retry": "कोई वॉइस नोट बाकी नहीं है।",
        "error": "माफ़ कीजिए, हमारी तरफ़ से गड़बड़ हुई। कुछ मिनट बाद फिर कोशिश करें।",
        "fields": {"name": "नाम", "phone": "फ़ोन नंबर", "village": "गाँव", "district": "ज़िला",
                   "state": "राज्य", "date_of_incident": "घटना की तारीख", "losses": "क्या नुकसान हुआ"},
        "statuses": {"Draft": "अभी भेजा नहीं गया", "Submitted": "भेजा गया", "Verified": "जाँच हो गई",
                     "Approved": "मंज़ूर", "Paid": "भुगतान हो गया", "Rejected": "अस्वीकार"},
        "losses": "{n} नुकसान", "relief": "अनुमानित राहत ₹{total}",
    },
    "bn": {
        "consent": "আপকে লিয়ে আপনাকে দুর্যোগ ত্রাণের দাবি করতে সাহায্য করে।\n\nআপনার ভয়েস নোট, ছবি, লোকেশন "
                   "আর এই ফোন নম্বর শুধু আপনার ত্রাণ দাবি তৈরি করে সরকারি আধিকারিকদের পাঠাতে ব্যবহার হবে।\n\n"
                   "রাজি থাকলে *হ্যাঁ* (বা YES) লিখুন।",
        "need_yes": "রাজি থাকলে *হ্যাঁ* লিখুন, অথবা ভাষা বদলাতে *NEW* লিখুন।",
        "started": "✅ আপনার দাবি নম্বর *{claim_id}*।\n\n🎤 একটি *ভয়েস নোট* পাঠান: আপনার নাম, গ্রাম, জেলা, "
                   "রাজ্য, ঘটনার তারিখ আর কী ক্ষতি হয়েছে।\n📍 তারপর আপনার *লোকেশন পাঠান* (📎 → Location) "
                   "আর ক্ষতির *ছবি* পাঠান।",
        "listening": "🎧 ভয়েস নোট পেয়েছি, শুনছি…",
        "ai_down": "এখন আপনার ভয়েস নোট বোঝা যায়নি। এটি রাখা আছে: কয়েক মিনিট পরে *RETRY* লিখুন।",
        "understood": "আমরা যা বুঝেছি:\n{summary}",
        "questions": "আর একটি ভয়েস নোটে জানান:\n{questions}",
        "missing": "এখনও দরকার: {fields}। এগুলো নিয়ে আর একটি ভয়েস নোট পাঠান।",
        "ready": "সব তথ্য পাওয়া গেছে 👍 দাবি পাঠাতে *SUBMIT* (বা জমা) লিখুন, বা কিছু ঠিক করতে ভয়েস নোট পাঠান।",
        "location_saved": "📍 লোকেশন রাখা হয়েছে। এবার ক্ষতির ছবি পাঠান।",
        "no_location": "পরামর্শ: ছবির আগে লোকেশন পাঠান (📎 → Location), যাতে আধিকারিকরা যাচাই করতে পারেন।",
        "photo_saved": "📷 ছবি {n} রাখা হয়েছে।",
        "photo_failed": "এই ছবিটি রাখা যায়নি: {why}",
        "send_voice": "দয়া করে *ভয়েস নোটে* 🎤 উত্তর দিন।\nকমান্ড: *SUBMIT*, *STATUS*, *NEW*, *HELP*",
        "help": "🎤 ভয়েস নোট: কী হয়েছে বলুন\n📍 লোকেশন, তারপর 📷 ক্ষতির ছবি\n"
                "*SUBMIT* দাবি পাঠান · *STATUS* অবস্থা দেখুন · *NEW* আবার শুরু",
        "submitted": "✅ দাবি *{claim_id}* পাঠানো হয়েছে। আনুমানিক ত্রাণ: ₹{total}।\n"
                     "অবস্থা বদলালে এখানেই জানাব। যেকোনো সময় *STATUS* লিখুন।",
        "cannot_submit": "কিছু তথ্য নেই বা ঠিক করতে হবে: {fields}।\nএগুলো নিয়ে ভয়েস নোট পাঠান, তারপর আবার *SUBMIT* লিখুন।",
        "status": "দাবি *{claim_id}*: *{status}*{note}",
        "status_changed": "🔔 দাবি *{claim_id}*-এর নতুন অবস্থা: *{status}*।{note}",
        "locked": "দাবি *{claim_id}* আগেই পাঠানো হয়েছে। *STATUS* দিয়ে দেখুন, বা নতুন দাবির জন্য *NEW* লিখুন।",
        "unsupported": "দয়া করে ভয়েস নোট, ছবি, লোকেশন বা কমান্ড (*HELP*) পাঠান।",
        "nothing_to_retry": "কোনো ভয়েস নোট বাকি নেই।",
        "error": "দুঃখিত, আমাদের দিকে সমস্যা হয়েছে। কয়েক মিনিট পরে আবার চেষ্টা করুন।",
        "fields": {"name": "নাম", "phone": "ফোন নম্বর", "village": "গ্রাম", "district": "জেলা",
                   "state": "রাজ্য", "date_of_incident": "ঘটনার তারিখ", "losses": "কী ক্ষতি হয়েছে"},
        "statuses": {"Draft": "এখনও পাঠানো হয়নি", "Submitted": "পাঠানো হয়েছে", "Verified": "যাচাই হয়েছে",
                     "Approved": "অনুমোদিত", "Paid": "টাকা দেওয়া হয়েছে", "Rejected": "বাতিল"},
        "losses": "{n}টি ক্ষতি", "relief": "আনুমানিক ত্রাণ ₹{total}",
    },
}

COMMANDS = {
    "new": {"new", "start", "restart", "नया", "नई", "নতুন"},
    "status": {"status", "स्थिति", "স্থিতি", "অবস্থা"},
    "submit": {"submit", "जमा", "জমা"},
    "help": {"help", "menu", "मदद", "সাহায্য"},
    "retry": {"retry", "फिर", "আবার"},
}
YES = {"yes", "y", "ok", "okay", "haan", "han", "ha", "haa", "हाँ", "हां", "हा", "হ্যাঁ", "হ্যা", "হাঁ"}


def command(text: str) -> Optional[str]:
    word = re.sub(r"[^\wऀ-৿]+", " ", text.lower()).strip()
    return next((c for c, words in COMMANDS.items() if word in words), None)


def is_yes(text: str) -> bool:
    return re.sub(r"[^\wऀ-৿]+", "", text.lower()) in YES


def indian_mobile(whatsapp_from: str) -> Optional[str]:
    """'whatsapp:+919812345678' -> '+919812345678' (Member 2 only accepts Indian mobiles)."""
    digits = re.sub(r"\D", "", whatsapp_from)
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return f"+91{digits}" if re.fullmatch(r"[6-9]\d{9}", digits) else None


# ------------------------------------------------------------------ Twilio

def twilio_signature(url: str, params: dict, auth_token: str) -> str:
    """Twilio's X-Twilio-Signature: HMAC-SHA1 of the URL plus every POST field, sorted."""
    data = url + "".join(k + params[k] for k in sorted(params))
    return base64.b64encode(hmac.new(auth_token.encode(), data.encode(), hashlib.sha1).digest()).decode()


def enabled() -> bool:
    return bool(config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN and config.TWILIO_WHATSAPP_FROM)


class Twilio:
    """Sends WhatsApp messages and downloads the media people send."""

    def __init__(self):
        self.auth = (config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        self.url = f"https://api.twilio.com/2010-04-01/Accounts/{config.TWILIO_ACCOUNT_SID}/Messages.json"

    async def send(self, to: str, body: str) -> None:
        async with httpx.AsyncClient(auth=self.auth, timeout=20) as c:
            for i in range(0, len(body), 1500):          # WhatsApp limit is 1600 characters
                r = await c.post(self.url, data={"From": config.TWILIO_WHATSAPP_FROM, "To": to,
                                                 "Body": body[i:i + 1500]})
                if r.status_code >= 400:
                    log.warning("Twilio refused a message: HTTP %s %s", r.status_code, r.text[:200])

    async def download(self, url: str) -> bytes:
        # Twilio media needs the account login; httpx drops it on the redirect to the file host.
        async with httpx.AsyncClient(auth=self.auth, timeout=60, follow_redirects=True) as c:
            r = await c.get(url)
            r.raise_for_status()
            if len(r.content) > MAX_MEDIA_BYTES:
                raise ValueError("file too large")
            return r.content


# ------------------------------------------------------------------ Member 2

class Member2Error(Exception):
    def __init__(self, status: int, detail):
        super().__init__(f"HTTP {status}: {detail}")
        self.status, self.detail = status, detail


class Member2:
    """The same calls the app makes (Member 2's /claims API)."""

    def __init__(self, base: str):
        self.base = base

    async def _call(self, method: str, path: str, token: Optional[str] = None, timeout=30, **kw) -> dict:
        headers = {"X-Claim-Token": token} if token else {}
        try:
            async with httpx.AsyncClient(timeout=timeout) as c:
                r = await c.request(method, self.base + path, headers=headers, **kw)
        except httpx.HTTPError as e:
            raise Member2Error(503, f"Member 2 unreachable: {e.__class__.__name__}") from None
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail")
            except ValueError:
                detail = r.text[:200]
            raise Member2Error(r.status_code, detail)
        return r.json()

    async def create_claim(self, language: str, consent_text_version: Optional[str] = None) -> dict:
        return await self._call("POST", "/claims", json={
            "language": language, "consent": True,
            "consent_text_version": consent_text_version or config.WHATSAPP_CONSENT_VERSION})

    async def update_fields(self, claim_id: str, token: str, fields: dict) -> dict:
        return await self._call("PATCH", f"/claims/{claim_id}", token, json={"fields": fields})

    async def set_phone(self, claim_id: str, token: str, phone: str) -> dict:
        return await self._call("PATCH", f"/claims/{claim_id}", token, json={"fields": {"phone": phone}})

    async def upload_audio(self, claim_id: str, token: str, data: bytes, content_type: str) -> dict:
        ext = {"audio/ogg": "ogg", "audio/mpeg": "mp3", "audio/mp4": "m4a", "audio/amr": "amr"}.get(content_type, "ogg")
        return await self._call("POST", f"/claims/{claim_id}/audio", token, timeout=120,
                                files={"audio": (f"voice.{ext}", data, content_type)})

    async def retry_audio(self, claim_id: str, token: str) -> dict:
        return await self._call("POST", f"/claims/{claim_id}/audio/retry", token, timeout=120)

    async def upload_photo(self, claim_id: str, token: str, data: bytes, content_type: str,
                           lat: Optional[float], lon: Optional[float], taken_at: Optional[str] = None) -> dict:
        form = {k: str(v) for k, v in (("lat", lat), ("lon", lon), ("taken_at", taken_at)) if v is not None}
        return await self._call("POST", f"/claims/{claim_id}/photos", token, timeout=60, data=form,
                                files={"photo": ("photo.jpg", data, content_type)})

    async def submit(self, claim_id: str, token: str) -> dict:
        return await self._call("POST", f"/claims/{claim_id}/submit", token, timeout=60)

    async def get_claim(self, claim_id: str, token: str) -> dict:
        return await self._call("GET", f"/claims/{claim_id}", token)

    async def status(self, claim_id: str, token: str) -> dict:
        return await self._call("GET", f"/status/{claim_id}", token)


# ------------------------------------------------------------------ the conversation

@dataclass
class Incoming:
    phone: str                                   # whatsapp:+91...
    text: str = ""
    media: list[tuple[str, str]] = field(default_factory=list)   # (url, content type)
    lat: Optional[float] = None
    lon: Optional[float] = None

    @classmethod
    def from_form(cls, f: dict) -> "Incoming":
        media = [(f[f"MediaUrl{i}"], f.get(f"MediaContentType{i}", "").split(";")[0].strip().lower())
                 for i in range(int(f.get("NumMedia") or 0)) if f.get(f"MediaUrl{i}")]
        lat = lon = None
        try:
            if f.get("Latitude") and f.get("Longitude"):
                lat, lon = float(f["Latitude"]), float(f["Longitude"])
        except ValueError:
            pass
        return cls(phone=f.get("From", ""), text=(f.get("Body") or "").strip(), media=media, lat=lat, lon=lon)


class Bot:
    def __init__(self, store: Store, member2: Member2, twilio):
        self.store, self.m2, self.twilio = store, member2, twilio
        self._fernet = Fernet(base64.urlsafe_b64encode(store.secret_for("whatsapp-claim-token")))
        self._locks: dict[str, asyncio.Lock] = {}

    # -- helpers
    def _enc(self, token: str) -> str:
        return self._fernet.encrypt(token.encode()).decode()

    def _token(self, s: dict) -> str:
        try:
            return self._fernet.decrypt(s["token_enc"].encode()).decode()
        except (InvalidToken, AttributeError):
            raise Member2Error(404, "claim token lost") from None

    async def _say(self, s: dict, key: str, **kw) -> None:
        t = T.get(s.get("language") or "en", T["en"])
        await self.twilio.send(s["phone"], t[key].format(**kw))

    def _names(self, s: dict, fields: list) -> str:
        names = T.get(s.get("language") or "en", T["en"])["fields"]
        return ", ".join(names.get(f, f) for f in fields)

    # -- entry point
    async def handle(self, msg: Incoming) -> None:
        if not msg.phone:
            return
        lock = self._locks.setdefault(msg.phone, asyncio.Lock())   # photos sent together arrive together
        async with lock:
            s = self.store.wa_get(msg.phone)
            try:
                await self._handle(msg, s)
            except Exception:
                log.exception("WhatsApp bot error")
                await self._say(s or {"phone": msg.phone}, "error")

    async def _handle(self, msg: Incoming, s: Optional[dict]) -> None:
        cmd = command(msg.text) if msg.text and not msg.media else None
        if s is None or s["step"] == "language" or cmd == "new":
            lang = LANG_CHOICES.get(msg.text.strip()) if s and s["step"] == "language" else None
            if lang:
                self.store.wa_save(msg.phone, step="consent", language=lang)
                return await self._say({"phone": msg.phone, "language": lang}, "consent")
            self.store.wa_save(msg.phone, step="language", claim_id=None, token_enc=None, last_status=None)
            return await self.twilio.send(msg.phone, WELCOME)

        if cmd == "help":
            return await self._say(s, "help")
        if s["step"] == "consent":
            if is_yes(msg.text):
                return await self._start_claim(s)
            return await self._say(s, "need_yes")

        # step == "claim"
        if msg.lat is not None:
            self.store.wa_save(msg.phone, lat=msg.lat, lon=msg.lon)
            return await self._say(s, "location_saved")
        if msg.media:
            for url, ctype in msg.media:
                if ctype.startswith("audio/"):
                    await self._voice(s, await self.twilio.download(url), ctype)
                elif ctype in ("image/jpeg", "image/png", "image/webp"):
                    await self._photo(s, await self.twilio.download(url), ctype)
                else:
                    await self._say(s, "unsupported")
            return
        if cmd == "status":
            return await self._status(s)
        if cmd == "submit":
            return await self._submit(s)
        if cmd == "retry":
            return await self._retry(s)
        await self._say(s, "send_voice")

    # -- steps
    async def _start_claim(self, s: dict) -> None:
        c = await self.m2.create_claim(s["language"])
        self.store.wa_save(s["phone"], step="claim", claim_id=c["id"], token_enc=self._enc(c["claim_token"]),
                           last_status=c.get("status", "Draft"), lat=None, lon=None)
        phone = indian_mobile(s["phone"])
        if phone:                       # so nobody has to say their number in the voice note
            try:
                await self.m2.set_phone(c["id"], c["claim_token"], phone)
            except Member2Error as e:
                log.info("Could not add the WhatsApp number to the claim: %s", e)
        await self._say(s, "started", claim_id=c["id"])

    def _locked(self, e: Member2Error) -> bool:
        return e.status == 409 and "submitted" in str(e.detail).lower()

    async def _voice(self, s: dict, data: bytes, ctype: str) -> None:
        await self._say(s, "listening")
        try:
            claim = await self.m2.upload_audio(s["claim_id"], self._token(s), data, ctype)
        except Member2Error as e:
            if e.status == 503:
                return await self._say(s, "ai_down")
            if self._locked(e):
                return await self._say(s, "locked", claim_id=s["claim_id"])
            raise
        await self._report(s, claim)

    async def _retry(self, s: dict) -> None:
        try:
            claim = await self.m2.retry_audio(s["claim_id"], self._token(s))
        except Member2Error as e:
            if e.status == 503:
                return await self._say(s, "ai_down")
            if e.status == 409:
                return await self._say(s, "locked" if self._locked(e) else "nothing_to_retry",
                                       claim_id=s["claim_id"])
            raise
        await self._report(s, claim)

    async def _report(self, s: dict, claim: dict) -> None:
        """Tell the person what Member 1 understood and what is still missing."""
        t = T.get(s["language"] or "en", T["en"])
        f = claim.get("fields") or {}
        lines = [f"• {t['fields'][k]}: {f[k]}" for k in ("name", "village", "district", "state", "date_of_incident")
                 if f.get(k)]
        if f.get("losses"):
            lines.append("• " + t["losses"].format(n=len(f["losses"])))
        total = (claim.get("relief") or {}).get("total")
        if total:
            lines.append("• " + t["relief"].format(total=total))
        if lines:
            await self._say(s, "understood", summary="\n".join(lines))
        missing = claim.get("missing_fields") or []
        questions = claim.get("follow_up_questions") or []
        if questions:
            await self._say(s, "questions", questions="\n".join(f"• {q}" for q in questions[:5]))
        elif missing:
            await self._say(s, "missing", fields=self._names(s, missing))
        else:
            await self._say(s, "ready")

    async def _photo(self, s: dict, data: bytes, ctype: str) -> None:
        if s.get("lat") is None:
            await self._say(s, "no_location")
        try:
            claim = await self.m2.upload_photo(s["claim_id"], self._token(s), data, ctype, s.get("lat"), s.get("lon"))
        except Member2Error as e:
            if self._locked(e):
                return await self._say(s, "locked", claim_id=s["claim_id"])
            if e.status in (409, 413, 415, 422):
                return await self._say(s, "photo_failed", why=e.detail)
            raise
        await self._say(s, "photo_saved", n=len(claim.get("photos") or []))

    async def _submit(self, s: dict) -> None:
        try:
            claim = await self.m2.submit(s["claim_id"], self._token(s))
        except Member2Error as e:
            if self._locked(e):
                return await self._say(s, "locked", claim_id=s["claim_id"])
            if e.status == 422 and isinstance(e.detail, dict):
                bad = list(e.detail.get("missing_fields", [])) + list(e.detail.get("invalid_fields", {}))
                return await self._say(s, "cannot_submit", fields=self._names(s, bad))
            raise
        self.store.wa_save(s["phone"], last_status=claim["status"])
        await self._say(s, "submitted", claim_id=s["claim_id"], total=(claim.get("relief") or {}).get("total", 0))

    async def _status(self, s: dict) -> None:
        st = await self.m2.status(s["claim_id"], self._token(s))
        await self._say(s, "status", claim_id=s["claim_id"], **self._status_words(s, st))

    def _status_words(self, s: dict, st: dict) -> dict:
        t = T.get(s["language"] or "en", T["en"])
        last = (st.get("timeline") or [{}])[-1]
        note = f"\n{last['note']}" if last.get("note") and last.get("status") == st["status"] else ""
        return {"status": t["statuses"].get(st["status"], st["status"]), "note": note}

    # -- status updates
    async def check_statuses(self) -> int:
        """Message everyone whose claim status changed since we last told them. Returns how many."""
        sent = 0
        for s in self.store.wa_with_claims():
            if s["last_status"] in FINAL_STATUSES or s["step"] != "claim":
                continue
            try:
                st = await self.m2.status(s["claim_id"], self._token(s))
            except Member2Error:
                continue
            if st["status"] != s["last_status"]:
                self.store.wa_save(s["phone"], last_status=st["status"])
                await self._say(s, "status_changed", claim_id=s["claim_id"], **self._status_words(s, st))
                sent += 1
        return sent


_bot: Optional[Bot] = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(get_store(), Member2(config.MEMBER2_API_URL), Twilio())
    return _bot


def set_bot(bot: Optional[Bot]) -> None:
    """For tests."""
    global _bot
    _bot = bot


async def status_loop() -> None:
    """Runs while the service is up (started in app/main.py)."""
    while True:
        await asyncio.sleep(config.WHATSAPP_STATUS_POLL_SECONDS)
        try:
            n = await get_bot().check_statuses()
            if n:
                log.info("WhatsApp: sent %d status update(s)", n)
        except Exception:
            log.exception("WhatsApp status check failed")


@router.post("/webhook")
async def webhook(request: Request, background: BackgroundTasks) -> Response:
    if not enabled():
        raise HTTPException(404, "WhatsApp bot is not configured")
    params = {k: v for k, v in (await request.form()).items() if isinstance(v, str)}
    url = (config.PUBLIC_BASE_URL + request.url.path) if config.PUBLIC_BASE_URL else str(request.url)
    if request.url.query and config.PUBLIC_BASE_URL:
        url += "?" + request.url.query
    expected = twilio_signature(url, params, config.TWILIO_AUTH_TOKEN)
    if not hmac.compare_digest(expected, request.headers.get("X-Twilio-Signature", "")):
        raise HTTPException(403, "Not signed by Twilio (check PUBLIC_BASE_URL matches the webhook URL)")
    # Answer Twilio at once (it gives up after 15 s); replies are sent through the API.
    background.add_task(get_bot().handle, Incoming.from_form(params))
    return Response('<?xml version="1.0" encoding="UTF-8"?><Response></Response>', media_type="application/xml")
