"""Aapke Liye - Member 1 Speech + Claim AI API (FastAPI). Run: uvicorn app.main:app --reload --port 8001"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import damage, documents
from .asr import ASRError, transcribe
from .audio import AudioError, load_audio
from .config import get_settings
from .languages import LANGUAGES
from .llm import LLMError
from .pipeline import run_turn
from .tts import TTSError, speak
from .schemas import (
    SCHEMA_VERSION, Claim, LanguageCode, DamageCompareRequest, DamageCompareResponse, DraftRequest, DraftResponse,
    EscalationRequest, EscalationResponse, TranscribeRequest, TranscribeResponse, TurnRequest, TurnResponse,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Aapke Liye - Speech + Claim AI", version=SCHEMA_VERSION,
              description="Speech + Claim AI: voice notes in 6 languages -> structured relief claims.")

_DEMO = Path(__file__).parent / "static" / "demo.html"


@app.get("/", include_in_schema=False)
def demo_page():
    """Browser demo: chat on the left, live claim on the right."""
    return FileResponse(_DEMO, media_type="text/html")


@app.get("/health")
def health():
    s = get_settings()
    return {"ok": True, "mode": s.mode, "schema_version": SCHEMA_VERSION, "languages": LANGUAGES,
            "asr": f"whisper:{s.whisper_model}", "llm_model": s.llm_model}


@app.on_event("startup")
def _warm_whisper():
    """Load Whisper in the background so the first voice note isn't slow."""
    s = get_settings()
    if s.is_mock:
        return
    import threading

    from .asr import warm_up

    def run():
        try:
            warm_up(s)
        except Exception as exc:  # noqa: BLE001 - never crash startup over the speech model
            logging.getLogger("aapke_liye").warning("Whisper not ready: %s", exc)

    threading.Thread(target=run, daemon=True).start()


@app.get("/v1/schema/claim")
def claim_schema():
    """JSON schema of the claim object, for Member 2 and Member 4."""
    return Claim.model_json_schema()


@app.post("/v1/transcribe", response_model=TranscribeResponse)
def transcribe_route(req: TranscribeRequest):
    s = get_settings()
    if s.is_mock:
        raise HTTPException(503, "mock mode has no speech recognition; set CLAIM_AI_MODE=live")
    try:
        audio = load_audio(req.audio_base64, req.audio_url, s.max_audio_seconds)
        r = transcribe(audio, req.language, s)
    except AudioError as exc:
        raise HTTPException(400, str(exc)) from exc
    except ASRError as exc:
        raise HTTPException(502, f"speech recognition failed: {exc}") from exc
    return TranscribeResponse(text=r.text, language=r.language, confidence=r.confidence,
                              provider=r.provider, duration_s=round(audio.duration_s, 2))


@app.post("/v1/claim/turn", response_model=TurnResponse)
def claim_turn(req: TurnRequest):
    return run_turn(req, get_settings())


@app.post("/v1/damage/compare", response_model=DamageCompareResponse)
def damage_compare(req: DamageCompareRequest):
    try:
        return damage.compare(req, get_settings())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(502, str(exc)) from exc


@app.get("/v1/documents/types")
def document_types():
    return documents.list_doc_types()


@app.post("/v1/documents/draft", response_model=DraftResponse)
def documents_draft(req: DraftRequest):
    return documents.draft(req, get_settings())


@app.post("/v1/escalation/next", response_model=EscalationResponse)
def escalation_next(req: EscalationRequest):
    return documents.next_escalation(req)


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=600)
    language: LanguageCode = "en"


@app.post("/v1/tts")
def tts_route(req: TTSRequest):
    """Speak a question or status aloud (gTTS, needs internet). Returns base64 MP3."""
    try:
        return {"audio_base64": speak(req.text, req.language), "format": "mp3"}
    except TTSError as exc:
        raise HTTPException(502, str(exc)) from exc
