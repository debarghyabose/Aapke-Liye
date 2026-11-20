"""Speech to text: Gemini by default, Whisper as the fallback (Gemini and Whisper are faked)."""
import io
import wave

import pytest

from app import asr, llm
from app.audio import Audio
from app.config import Settings


def _audio(seconds: float = 1.0) -> Audio:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(16000 * seconds))
    return Audio(wav_bytes=buf.getvalue(), duration_s=seconds)


def _settings(monkeypatch, **env) -> Settings:
    for k, v in {"CLAIM_AI_MODE": "live", "ASR_PROVIDER": "gemini", "ASR_FALLBACK": "whisper", **env}.items():
        monkeypatch.setenv(k, v)
    return Settings()


@pytest.fixture
def whisper(monkeypatch):
    calls = []

    def fake(audio, language, settings):
        calls.append(language)
        return asr.ASRResult(text="whisper text", language=language or "hi", confidence=0.9, provider="whisper")

    monkeypatch.setattr(asr, "_whisper", fake)
    return calls


def test_gemini_is_the_default(monkeypatch, whisper):
    seen = {}

    def fake_structured(settings, *, system, content, schema, max_tokens=4000):
        seen["content"] = content
        return {"text": "मेरा घर बाढ़ में टूट गया", "language": "hi", "confidence": 0.93}

    monkeypatch.setattr(llm, "structured", fake_structured)
    r = asr.transcribe(_audio(), "hi", _settings(monkeypatch))
    assert (r.provider, r.language, r.text) == ("gemini", "hi", "मेरा घर बाढ़ में टूट गया")
    assert seen["content"][1]["type"] == "audio" and seen["content"][1]["source"]["media_type"] == "audio/wav"
    assert whisper == []                                   # Whisper never ran


def test_gemini_detects_language_when_not_given(monkeypatch, whisper):
    monkeypatch.setattr(llm, "structured", lambda *a, **k: {"text": "আমার বাড়ি", "language": "bn", "confidence": 0.8})
    assert asr.transcribe(_audio(), None, _settings(monkeypatch)).language == "bn"


def test_falls_back_to_whisper_when_gemini_fails(monkeypatch, whisper):
    def down(*a, **k):
        raise llm.LLMError("could not reach Gemini")

    monkeypatch.setattr(llm, "structured", down)
    r = asr.transcribe(_audio(), "ta", _settings(monkeypatch))
    assert r.provider == "whisper" and whisper == ["ta"]


def test_no_fallback_raises(monkeypatch, whisper):
    monkeypatch.setattr(llm, "structured", lambda *a, **k: (_ for _ in ()).throw(llm.LLMError("quota")))
    with pytest.raises(asr.ASRError, match="Gemini speech recognition failed"):
        asr.transcribe(_audio(), "en", _settings(monkeypatch, ASR_FALLBACK="none"))
    assert whisper == []


def test_silence_is_not_sent_to_whisper(monkeypatch, whisper):
    monkeypatch.setattr(llm, "structured", lambda *a, **k: {"text": "", "language": "en", "confidence": 0})
    with pytest.raises(asr.ASRError, match="no speech"):
        asr.transcribe(_audio(), "en", _settings(monkeypatch))
    assert whisper == []


def test_whisper_provider_skips_gemini(monkeypatch, whisper):
    monkeypatch.setattr(llm, "structured", lambda *a, **k: pytest.fail("Gemini must not be called"))
    assert asr.transcribe(_audio(), "mr", _settings(monkeypatch, ASR_PROVIDER="whisper")).provider == "whisper"


def test_turn_reports_the_provider(monkeypatch, whisper):
    from app import pipeline
    from app.schemas import TurnRequest

    s = _settings(monkeypatch)
    monkeypatch.setattr(pipeline, "transcribe", lambda audio, lang, settings: asr.ASRResult(
        text="My name is Rina", language="en", confidence=0.95, provider="gemini"))
    monkeypatch.setattr(pipeline, "load_audio", lambda *a, **k: _audio())
    monkeypatch.setattr(pipeline, "extract", lambda *a, **k: {"claimant": {"name": "Rina"}})
    import base64
    resp = pipeline.run_turn(TurnRequest(session_id="s1", language="en",
                                         audio_base64=base64.b64encode(b"x").decode()), s)
    assert resp.asr_provider == "gemini"
    text_turn = pipeline.run_turn(TurnRequest(session_id="s2", language="en", text="hello"), s)
    assert text_turn.asr_provider is None
