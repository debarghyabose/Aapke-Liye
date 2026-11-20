"""IVR line: file a relief claim by phone call, from any phone (feature phones too).

Call flow (Twilio Voice calls POST /ivr/voice when the number rings):
  new caller:       language (1/2/3) -> consent (press 1) -> claim number read out
                    -> record the claim after the beep -> hang up
  returning caller: hears the claim's status; if details are missing, hears which and can
                    press 1 to record another message; 9 starts a new claim

The recording goes to Member 2's /claims/{id}/audio (Member 1's speech AI), like the app.
If nothing is missing afterwards the claim is submitted automatically. The recording is
then deleted from Twilio. Status is told on the next call (no SMS: Indian SMS needs DLT).

Setup: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and PUBLIC_BASE_URL in .env, and a Twilio
phone number whose "A call comes in" webhook is <PUBLIC_BASE_URL>/ivr/voice (POST).
"""
import asyncio
import base64
import hmac
import logging
from typing import Awaitable, Callable, Optional
from xml.sax.saxutils import escape, quoteattr

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import Response

from app import config
from app.store import Store, get_store
from app.whatsapp import T as WA_TEXTS
from app.whatsapp import Member2, Member2Error, indian_mobile, twilio_signature

log = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/ivr", tags=["ivr"])

# Text-to-speech voice per language (Twilio <Say>). Bengali needs a Google voice.
VOICES = {"en": ("Polly.Aditi", "en-IN"), "hi": ("Polly.Aditi", "hi-IN"),
          "bn": ("Google.bn-IN-Standard-A", "bn-IN")}
LANG_DIGITS = {"1": "en", "2": "hi", "3": "bn"}
MAX_RECORDING_SECONDS = 180

V = {
    "en": {
        "choose": "For English, press 1.",
        "consent": "Aapke Liye helps you claim disaster relief. Your voice recording and phone number are used "
                   "only to prepare your relief claim and send it to government officials. To agree, press 1.",
        "no_consent": "Without your agreement we cannot file a claim. Goodbye.",
        "claim_number": "Your claim number is: {spelled}. Again: {spelled}.",
        "record": "After the beep, tell us your name, your village, district and state, the date of the "
                  "disaster, and everything you lost. When you finish, press the hash key.",
        "record_more": "After the beep, tell us the missing details. When you finish, press the hash key.",
        "thanks": "Thank you, we have your message. Call this number again any time to hear your claim status. Goodbye.",
        "no_recording": "Sorry, we did not hear anything. Please call again. Goodbye.",
        "status": "Your claim {spelled} is: {status}.",
        "processing": "We are still listening to your last message. Please call again in a few minutes.",
        "still_needed": "We still need: {fields}.",
        "menu_draft": "To record another message for this claim, press 1. To start a new claim, press 9.",
        "menu_done": "To start a new claim, press 9. Otherwise you can hang up.",
        "goodbye": "Goodbye.",
        "error": "Sorry, our system is not available right now. Please call again later. Goodbye.",
    },
    "hi": {
        "choose": "हिंदी के लिए 2 दबाएं।",
        "consent": "आपके लिए आपको आपदा राहत का दावा करने में मदद करता है। आपकी आवाज़ की रिकॉर्डिंग और फ़ोन नंबर केवल "
                   "आपका राहत दावा तैयार करने और सरकारी अधिकारियों को भेजने के लिए इस्तेमाल होंगे। सहमत हैं तो 1 दबाएं।",
        "no_consent": "आपकी सहमति के बिना हम दावा नहीं कर सकते। धन्यवाद।",
        "claim_number": "आपका दावा नंबर है: {spelled}। फिर से: {spelled}।",
        "record": "बीप के बाद अपना नाम, गाँव, ज़िला और राज्य, आपदा की तारीख, और आपका क्या-क्या नुकसान हुआ, बताएं। "
                  "बोलने के बाद हैश बटन दबाएं।",
        "record_more": "बीप के बाद जो जानकारी बाकी है वह बताएं। बोलने के बाद हैश बटन दबाएं।",
        "thanks": "धन्यवाद, आपका संदेश मिल गया। अपने दावे की स्थिति सुनने के लिए कभी भी इसी नंबर पर फिर कॉल करें। नमस्ते।",
        "no_recording": "माफ़ कीजिए, हमें कुछ सुनाई नहीं दिया। कृपया फिर कॉल करें।",
        "status": "आपका दावा {spelled}: {status}।",
        "processing": "हम अभी आपका पिछला संदेश सुन रहे हैं। कृपया कुछ मिनट बाद फिर कॉल करें।",
        "still_needed": "अभी यह जानकारी चाहिए: {fields}।",
        "menu_draft": "इस दावे के लिए एक और संदेश रिकॉर्ड करने के लिए 1 दबाएं। नए दावे के लिए 9 दबाएं।",
        "menu_done": "नए दावे के लिए 9 दबाएं। नहीं तो आप फ़ोन रख सकते हैं।",
        "goodbye": "नमस्ते।",
        "error": "माफ़ कीजिए, अभी हमारा सिस्टम उपलब्ध नहीं है। कृपया बाद में कॉल करें।",
    },
    "bn": {
        "choose": "বাংলার জন্য 3 টিপুন।",
        "consent": "আপকে লিয়ে আপনাকে দুর্যোগ ত্রাণের দাবি করতে সাহায্য করে। আপনার কণ্ঠের রেকর্ডিং আর ফোন নম্বর শুধু "
                   "আপনার ত্রাণ দাবি তৈরি করে সরকারি আধিকারিকদের পাঠাতে ব্যবহার হবে। রাজি থাকলে 1 টিপুন।",
        "no_consent": "আপনার সম্মতি ছাড়া আমরা দাবি করতে পারি না। ধন্যবাদ।",
        "claim_number": "আপনার দাবি নম্বর: {spelled}। আবার বলছি: {spelled}।",
        "record": "বিপের পরে আপনার নাম, গ্রাম, জেলা আর রাজ্য, দুর্যোগের তারিখ, আর কী কী ক্ষতি হয়েছে বলুন। "
                  "বলা শেষ হলে হ্যাশ বোতাম টিপুন।",
        "record_more": "বিপের পরে যে তথ্য বাকি আছে তা বলুন। বলা শেষ হলে হ্যাশ বোতাম টিপুন।",
        "thanks": "ধন্যবাদ, আপনার বার্তা পেয়েছি। দাবির অবস্থা জানতে যেকোনো সময় এই নম্বরে আবার ফোন করুন। নমস্কার।",
        "no_recording": "দুঃখিত, আমরা কিছু শুনতে পাইনি। দয়া করে আবার ফোন করুন।",
        "status": "আপনার দাবি {spelled}: {status}।",
        "processing": "আমরা এখনও আপনার আগের বার্তা শুনছি। কয়েক মিনিট পরে আবার ফোন করুন।",
        "still_needed": "এখনও দরকার: {fields}।",
        "menu_draft": "এই দাবির জন্য আর একটি বার্তা রেকর্ড করতে 1 টিপুন। নতুন দাবির জন্য 9 টিপুন।",
        "menu_done": "নতুন দাবির জন্য 9 টিপুন। নইলে ফোন রেখে দিতে পারেন।",
        "goodbye": "নমস্কার।",
        "error": "দুঃখিত, এখন আমাদের সিস্টেম কাজ করছে না। পরে আবার ফোন করুন।",
    },
}


def spell(claim_id: str) -> str:
    """'AL-PZ5' -> 'A, L, P, Z, 5' so text-to-speech reads it one character at a time."""
    return ", ".join(c for c in claim_id if c.isalnum())


# ------------------------------------------------------------------ TwiML

def say(lang: str, text: str) -> str:
    voice, code = VOICES.get(lang, VOICES["en"])
    return f"<Say voice={quoteattr(voice)} language={quoteattr(code)}>{escape(text)}</Say>"


def gather(action: str, inner: str, timeout: int = 8) -> str:
    return (f'<Gather input="dtmf" numDigits="1" timeout="{timeout}" action={quoteattr(action)} method="POST">'
            f"{inner}</Gather>")


def record(action: str) -> str:
    return (f'<Record action={quoteattr(action)} method="POST" maxLength="{MAX_RECORDING_SECONDS}" '
            'finishOnKey="#" playBeep="true" timeout="6"/>')


def twiml(*parts: str) -> str:
    return '<?xml version="1.0" encoding="UTF-8"?><Response>' + "".join(parts) + "</Response>"


# ------------------------------------------------------------------ call logic

Downloader = Callable[[str], Awaitable[bytes]]


class Ivr:
    def __init__(self, store: Store, member2: Member2, download: Downloader,
                 delete_recording: Optional[Callable[[str], Awaitable[None]]] = None):
        self.store, self.m2, self.download = store, member2, download
        self.delete_recording = delete_recording
        # Same key as the WhatsApp bot: both keep Member 2 claim tokens.
        self._fernet = Fernet(base64.urlsafe_b64encode(store.secret_for("whatsapp-claim-token")))

    def _token(self, row: dict) -> str:
        try:
            return self._fernet.decrypt(row["token_enc"].encode()).decode()
        except (InvalidToken, AttributeError):
            raise Member2Error(404, "claim token lost") from None

    def language_menu(self) -> str:
        menu = "".join(say(lang, V[lang]["choose"]) for lang in ("en", "hi", "bn"))
        return twiml(gather("/ivr/language", say("en", "Aapke Liye. Namaste.") + menu),
                     '<Redirect method="POST">/ivr/voice</Redirect>')

    async def incoming(self, call_sid: str, phone: str) -> str:
        """A call starts: returning callers hear their claim, new callers choose a language."""
        prev = self.store.ivr_latest_claim(phone) if phone else None
        if not prev:
            return self.language_menu()
        lang = prev["language"] or "en"
        t = V[lang]
        if prev["processing"]:
            return twiml(say(lang, t["processing"]), gather("/ivr/menu", say(lang, t["menu_done"])),
                         say(lang, t["goodbye"]))
        try:
            token = self._token(prev)
            st = await self.m2.status(prev["claim_id"], token)
            claim = await self.m2.get_claim(prev["claim_id"], token)
        except Member2Error as e:
            if e.status == 404:                       # claim gone: start fresh
                return self.language_menu()
            return twiml(say(lang, t["error"]))
        status_word = WA_TEXTS[lang]["statuses"].get(st["status"], st["status"])
        parts = [say(lang, t["status"].format(spelled=spell(prev["claim_id"]), status=status_word))]
        if st["status"] == "Draft":
            missing = claim.get("missing_fields") or []
            if missing:
                names = WA_TEXTS[lang]["fields"]
                parts.append(say(lang, t["still_needed"].format(fields=", ".join(names.get(m, m) for m in missing))))
            parts.append(gather("/ivr/menu", say(lang, t["menu_draft"])))
        else:
            parts.append(gather("/ivr/menu", say(lang, t["menu_done"])))
        return twiml(*parts, say(lang, t["goodbye"]))

    def language(self, call_sid: str, phone: str, digit: str) -> str:
        lang = LANG_DIGITS.get(digit)
        if not lang:
            return self.language_menu()
        self.store.ivr_save(call_sid, phone=phone, language=lang)
        return twiml(gather(f"/ivr/consent?lang={lang}", say(lang, V[lang]["consent"]), timeout=10),
                     say(lang, V[lang]["no_consent"]))

    async def consent(self, call_sid: str, phone: str, lang: str, digit: str) -> str:
        lang = lang if lang in V else "en"
        t = V[lang]
        if digit != "1":
            return twiml(say(lang, t["no_consent"]))
        try:
            c = await self.m2.create_claim(lang)
        except Member2Error:
            log.exception("IVR: could not create a claim")
            return twiml(say(lang, t["error"]))
        self.store.ivr_save(call_sid, phone=phone, language=lang, claim_id=c["id"],
                            token_enc=self._fernet.encrypt(c["claim_token"].encode()).decode())
        if mobile := indian_mobile(phone):
            try:
                await self.m2.set_phone(c["id"], c["claim_token"], mobile)
            except Member2Error as e:
                log.info("IVR: could not add the caller's number to the claim: %s", e)
        return twiml(say(lang, t["claim_number"].format(spelled=spell(c["id"]))), say(lang, t["record"]),
                     record(f"/ivr/recorded?lang={lang}"), say(lang, t["no_recording"]))

    def menu(self, call_sid: str, phone: str, digit: str) -> str:
        prev = self.store.ivr_latest_claim(phone)
        if digit == "9" or not prev:
            return self.language_menu()
        lang = prev["language"] or "en"
        if digit == "1":
            self.store.ivr_save(call_sid, phone=phone, language=lang, claim_id=prev["claim_id"],
                                token_enc=prev["token_enc"])
            return twiml(say(lang, V[lang]["record_more"]), record(f"/ivr/recorded?lang={lang}"),
                         say(lang, V[lang]["no_recording"]))
        return twiml(say(lang, V[lang]["goodbye"]))

    def recorded(self, call_sid: str, lang: str, recording_url: str, duration: int) -> tuple[str, bool]:
        """The caller finished recording. Returns (TwiML, whether to process the recording)."""
        lang = lang if lang in V else "en"
        row = self.store.ivr_get(call_sid)
        if not recording_url or duration < 2 or not row or not row["claim_id"]:
            return twiml(say(lang, V[lang]["no_recording"])), False
        self.store.ivr_save(call_sid, processing=1)
        return twiml(say(lang, V[lang]["thanks"])), True

    async def process_recording(self, call_sid: str, recording_url: str, recording_sid: str = "") -> None:
        """After the call: send the recording to Member 2, submit the claim if complete."""
        row = self.store.ivr_get(call_sid)
        try:
            data = b""
            for attempt in range(4):              # the file can take a moment to be ready
                try:
                    data = await self.download(recording_url + ".wav")
                    break
                except Exception:
                    if attempt == 3:
                        raise
                    await asyncio.sleep(2)
            token = self._token(row)
            claim = await self.m2.upload_audio(row["claim_id"], token, data, "audio/wav")
            if not claim.get("missing_fields"):
                try:
                    await self.m2.submit(row["claim_id"], token)
                except Member2Error as e:          # a volunteer or the next call completes it
                    log.info("IVR: claim %s not submitted yet: %s", row["claim_id"], e)
            if recording_sid and self.delete_recording:
                await self.delete_recording(recording_sid)    # Member 2 keeps its own copy
        except Exception:
            log.exception("IVR: could not process the recording for claim %s", row and row["claim_id"])
        finally:
            self.store.ivr_save(call_sid, processing=0)


# ------------------------------------------------------------------ HTTP

async def _twilio_download(url: str) -> bytes:
    async with httpx.AsyncClient(auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN),
                                 timeout=60, follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.content


async def _twilio_delete_recording(recording_sid: str) -> None:
    url = (f"https://api.twilio.com/2010-04-01/Accounts/{config.TWILIO_ACCOUNT_SID}"
           f"/Recordings/{recording_sid}.json")
    async with httpx.AsyncClient(auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN), timeout=20) as c:
        r = await c.delete(url)
        if r.status_code not in (204, 404):
            log.warning("IVR: Twilio did not delete recording: HTTP %s", r.status_code)


_ivr: Optional[Ivr] = None


def get_ivr() -> Ivr:
    global _ivr
    if _ivr is None:
        _ivr = Ivr(get_store(), Member2(config.MEMBER2_API_URL), _twilio_download, _twilio_delete_recording)
    return _ivr


def set_ivr(ivr: Optional[Ivr]) -> None:
    """For tests."""
    global _ivr
    _ivr = ivr


def enabled() -> bool:
    return bool(config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN)


async def _signed_form(request: Request) -> dict:
    if not enabled():
        raise HTTPException(404, "IVR line is not configured")
    params = {k: v for k, v in (await request.form()).items() if isinstance(v, str)}
    url = (config.PUBLIC_BASE_URL + request.url.path) if config.PUBLIC_BASE_URL else str(request.url).split("?")[0]
    if request.url.query:
        url += "?" + request.url.query
    expected = twilio_signature(url, params, config.TWILIO_AUTH_TOKEN)
    if not hmac.compare_digest(expected, request.headers.get("X-Twilio-Signature", "")):
        raise HTTPException(403, "Not signed by Twilio (check PUBLIC_BASE_URL matches the webhook URL)")
    return params


def _xml(body: str) -> Response:
    return Response(body, media_type="application/xml")


@router.post("/voice")
async def voice(request: Request) -> Response:
    f = await _signed_form(request)
    return _xml(await get_ivr().incoming(f.get("CallSid", ""), f.get("From", "")))


@router.post("/language")
async def language(request: Request) -> Response:
    f = await _signed_form(request)
    return _xml(get_ivr().language(f.get("CallSid", ""), f.get("From", ""), f.get("Digits", "")))


@router.post("/consent")
async def consent(request: Request, lang: str = "en") -> Response:
    f = await _signed_form(request)
    return _xml(await get_ivr().consent(f.get("CallSid", ""), f.get("From", ""), lang, f.get("Digits", "")))


@router.post("/menu")
async def menu(request: Request) -> Response:
    f = await _signed_form(request)
    return _xml(get_ivr().menu(f.get("CallSid", ""), f.get("From", ""), f.get("Digits", "")))


@router.post("/recorded")
async def recorded(request: Request, background: BackgroundTasks, lang: str = "en") -> Response:
    f = await _signed_form(request)
    ivr = get_ivr()
    try:
        duration = int(f.get("RecordingDuration") or 0)
    except ValueError:
        duration = 0
    body, process = ivr.recorded(f.get("CallSid", ""), lang, f.get("RecordingUrl", ""), duration)
    if process:
        background.add_task(ivr.process_recording, f["CallSid"], f["RecordingUrl"], f.get("RecordingSid", ""))
    return _xml(body)
