"""
Regional Languages Text-to-Speech Service
Uses gTTS to generate natural MP3 speech in 6 Indian languages.
"""
import io
import logging
from gtts import gTTS

log = logging.getLogger(__name__)

# Map app language codes to gTTS language codes
LANG_MAP = {
    "en": "en",
    "hi": "hi",
    "bn": "bn",
    "ta": "ta",
    "te": "te",
    "mr": "mr",
}

async def generate_speech(text: str, language: str = "en") -> bytes:
    """Generates MP3 audio bytes for the given text."""
    lang = LANG_MAP.get(language, "en")
    buf = io.BytesIO()
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        log.error("TTS generation failed for lang %s: %s", lang, e)
        # Fallback to English TTS if regional fails
        buf = io.BytesIO()
        tts = gTTS(text=text, lang="en", slow=False)
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.getvalue()
