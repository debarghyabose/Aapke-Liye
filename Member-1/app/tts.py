"""Speak follow-up questions aloud with gTTS (Google Translate voices, no API key).

Returns base64 MP3. Needs internet. Supports en, hi, bn, mr, te, ta.
"""
from __future__ import annotations

import base64
import io
import logging

log = logging.getLogger("aapke_liye.tts")


class TTSError(RuntimeError):
    pass


def speak(text: str, lang: str) -> str:
    try:
        from gtts import gTTS
    except ImportError as exc:
        raise TTSError("gTTS is not installed: pip install gTTS") from exc
    buf = io.BytesIO()
    try:
        gTTS(text=text, lang=lang).write_to_fp(buf)
    except Exception as exc:  # noqa: BLE001
        raise TTSError(f"text-to-speech failed: {exc}") from exc
    return base64.b64encode(buf.getvalue()).decode("ascii")
