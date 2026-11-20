"""One conversation turn: audio/text in -> updated claim + next question out.

Stateless: Member 2 sends the current claim with every turn and stores what
we return, so this service can scale and restart freely.
"""
from __future__ import annotations

import logging
import time

from . import questions
from .asr import ASRError, transcribe
from .audio import AudioError, load_audio
from .config import Settings
from .tts import TTSError, speak
from .extract import apply_update, extract
from .gaps import missing_fields
from .languages import normalize_lang
from .llm import LLMError
from .normalize import normalize_text
from .schemas import Claim, NextQuestion, Transcript, TurnRequest, TurnResponse

log = logging.getLogger("aapke_liye.pipeline")


class _Timer:
    def __init__(self):
        self.t: dict[str, int] = {}
        self._start = time.perf_counter()

    def mark(self, name: str):
        now = time.perf_counter()
        self.t[name] = int((now - self._start) * 1000)
        self._start = now


def _comparable(c: Claim) -> dict:
    return c.model_dump(exclude={"field_confidence", "transcripts", "status"})


def _with_tts(q: NextQuestion | None, lang: str, settings: Settings) -> NextQuestion | None:
    if q is None or not settings.tts_enabled or settings.is_mock:
        return q
    try:
        q.audio_base64 = speak(q.text, lang)
    except TTSError as exc:
        log.warning("TTS failed: %s", exc)
    return q


def _repeat(claim: Claim, message: str, timer: _Timer, settings: Settings) -> TurnResponse:
    q = NextQuestion(field="repeat", text=questions.template("repeat", claim.language),
                     text_en=questions.template("repeat", "en"))
    return TurnResponse(claim=claim, transcript=None, missing_fields=missing_fields(claim),
                        next_question=_with_tts(q, claim.language, settings), status=claim.status,
                        message=message, timings_ms=timer.t)


def _finish(claim: Claim, transcript: str | None, timer: _Timer, settings: Settings) -> TurnResponse:
    """Work out status and the next question from the claim as it now stands."""
    missing = missing_fields(claim)
    if missing:
        claim.status = "incomplete"
        q = questions.next_question(missing[0], claim, settings)
    else:
        claim.status = "needs_confirmation"
        q = questions.confirm_question(claim)
    timer.mark("question")
    q = _with_tts(q, claim.language, settings)
    timer.mark("tts")
    return TurnResponse(claim=claim, transcript=transcript, missing_fields=missing, next_question=q,
                        status=claim.status, timings_ms=timer.t)


def _complete(claim: Claim, transcript: str | None, timer: _Timer) -> TurnResponse:
    claim.status = "complete"
    return TurnResponse(claim=claim, transcript=transcript, missing_fields=[], next_question=None,
                        status="complete", message=questions.template("done", claim.language),
                        timings_ms=timer.t)


def run_turn(req: TurnRequest, settings: Settings) -> TurnResponse:
    timer = _Timer()
    claim = req.claim.model_copy(deep=True) if req.claim else Claim(session_id=req.session_id)
    claim.session_id = req.session_id
    lang = normalize_lang(req.language) or (claim.language if req.claim else None)
    if lang:
        claim.language = lang

    has_input = bool((req.text and req.text.strip()) or req.audio_base64 or req.audio_url)

    # Buttons from Member 4's read-back screen
    if req.confirmed is True and claim.status == "needs_confirmation" and not missing_fields(claim):
        return _complete(claim, None, timer)
    if req.confirmed is False and not has_input:
        claim.status = "incomplete"
        q = NextQuestion(field="correction", text=questions.template("correct_what", claim.language),
                         text_en=questions.template("correct_what", "en"))
        return TurnResponse(claim=claim, missing_fields=missing_fields(claim),
                            next_question=_with_tts(q, claim.language, settings),
                            status="incomplete", timings_ms=timer.t)

    # ---- 1. get text
    asr_provider, asr_conf = "text", 1.0
    if req.text and req.text.strip():
        text = req.text.strip()
    elif req.audio_base64 or req.audio_url:
        if settings.is_mock:
            return _repeat(claim, "mock mode cannot transcribe audio; send `text` instead", timer, settings)
        try:
            audio = load_audio(req.audio_base64, req.audio_url, settings.max_audio_seconds)
            timer.mark("audio")
            res = transcribe(audio, lang, settings)
            timer.mark("asr")
        except AudioError as exc:
            return _repeat(claim, f"audio problem: {exc}", timer, settings)
        except ASRError as exc:
            log.error("ASR failed: %s", exc)
            return _repeat(claim, "speech recognition failed", timer, settings)
        text, asr_provider, asr_conf = res.text, res.provider, res.confidence
        if not req.claim and not lang:
            claim.language = normalize_lang(res.language) or "en"
        if asr_conf < settings.asr_min_confidence:
            return _repeat(claim, f"low ASR confidence ({asr_conf:.2f})", timer, settings)
    else:
        # Nothing said yet: ask the first question
        return _finish(claim, None, timer, settings)

    # ---- 2. normalize spoken amounts (Gemini reads all 6 languages directly)
    norm = normalize_text(text)
    english = None
    timer.mark("normalize")

    claim.transcripts.append(Transcript(original=text, english=english, normalized=norm.text,
                                        language=claim.language, asr_provider=asr_provider,
                                        confidence=round(asr_conf, 3)))

    # ---- 3. extract + merge
    was_confirming = claim.status == "needs_confirmation"
    try:
        upd = extract(claim, text, norm.text, norm.amounts, english, settings)
    except LLMError as exc:
        log.error("extraction failed: %s", exc)
        resp = _finish(claim, text, timer, settings)
        resp.message = "claim extraction is temporarily unavailable; the transcript was saved"
        return resp
    timer.mark("extract")

    before = _comparable(claim)
    claim = apply_update(claim, upd, force=was_confirming)
    changed = _comparable(claim) != before

    if was_confirming and not changed:
        if upd.get("confirmation") == "yes" or req.confirmed is True:
            return _complete(claim, text, timer)
        if upd.get("confirmation") == "no":
            claim.status = "incomplete"
            q = NextQuestion(field="correction", text=questions.template("correct_what", claim.language),
                             text_en=questions.template("correct_what", "en"))
            return TurnResponse(claim=claim, transcript=text, missing_fields=missing_fields(claim),
                                next_question=_with_tts(q, claim.language, settings),
                                status="incomplete", timings_ms=timer.t)

    return _finish(claim, text, timer, settings)
