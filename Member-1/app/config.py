"""Service settings, read once from environment variables (and .env if present)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

try:  # optional: load .env during local development
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def _bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # "live" uses Whisper (local) + Gemini. "mock" uses offline rule-based
    # stand-ins so the team can integrate and tests can run without keys.
    mode: str = field(default_factory=lambda: os.getenv("CLAIM_AI_MODE", "live").lower())

    # Speech to text. "gemini" (default) sends the voice note to Gemini, which hears all six
    # languages directly. "whisper" runs Whisper on this computer (no key). With
    # ASR_FALLBACK=whisper, a Gemini failure falls back to Whisper; "none" turns that off.
    asr_provider: str = field(default_factory=lambda: os.getenv("ASR_PROVIDER", "gemini").strip().lower())
    asr_fallback: str = field(default_factory=lambda: os.getenv("ASR_FALLBACK", "whisper").strip().lower())
    # Whisper settings (used when ASR_PROVIDER=whisper or as the fallback). large-v3-turbo is a good
    # speed/accuracy balance; large-v3 is most accurate; small is fastest.
    asr_min_confidence: float = field(default_factory=lambda: float(os.getenv("ASR_MIN_CONFIDENCE", "0.45")))
    whisper_model: str = field(default_factory=lambda: os.getenv("WHISPER_MODEL", "large-v3-turbo"))
    whisper_device: str = field(default_factory=lambda: os.getenv("WHISPER_DEVICE", "auto"))

    # Gemini (key in GEMINI_API_KEY)
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gemini-3.5-flash"))
    # used automatically when the main model is overloaded (503) or rate-limited
    llm_fallback_model: str = field(default_factory=lambda: os.getenv("LLM_FALLBACK_MODEL", "gemini-3.5-flash-lite,gemini-3.1-flash-lite").strip())
    # low | medium | high, or empty to not send it (for models without thinking levels)
    llm_thinking_level: str = field(default_factory=lambda: os.getenv("LLM_THINKING_LEVEL", "low").strip())

    # "llm" = Gemini phrases follow-up questions; "template" = fixed, reviewed
    # sentences per language (fast, no API call).
    question_mode: str = field(default_factory=lambda: os.getenv("QUESTION_MODE", "llm").lower())
    # Speak questions aloud with gTTS (free, needs internet)
    tts_enabled: bool = field(default_factory=lambda: _bool("TTS_ENABLED", False))

    max_audio_seconds: int = field(default_factory=lambda: int(os.getenv("MAX_AUDIO_SECONDS", "90")))

    @property
    def is_mock(self) -> bool:
        return self.mode == "mock"


def get_settings() -> Settings:
    # Re-read each call so tests can flip env vars; construction is cheap.
    return Settings()
