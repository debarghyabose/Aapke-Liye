"""Speech to text with Whisper, running locally (no account or API key).

Uses faster-whisper (CTranslate2). The model downloads once on first use:
  large-v3  ~3 GB  best for Hindi/Bengali/Marathi/Telugu/Tamil (GPU recommended)
  medium    ~1.5 GB  good middle ground on a laptop
  small     ~500 MB  fast on CPU, weaker on Indian languages
Set WHISPER_MODEL in .env.
"""
from __future__ import annotations

import logging
import os
import tempfile
import threading
from dataclasses import dataclass

from .audio import Audio
from .config import Settings
from .languages import normalize_lang

log = logging.getLogger("aapke_liye.asr")

# A short prompt in the target language nudges Whisper to write the right
# script and vocabulary (rupees, lakh, district names).
PROMPTS = {
    "en": "Disaster relief claim. My name is Ramesh Kumar, Puri district, Odisha. Loss of 2 lakh rupees.",
    "hi": "आपदा राहत दावा। मेरा नाम रमेश कुमार है, पुरी जिला, ओडिशा। दो लाख रुपये का नुकसान।",
    "bn": "দুর্যোগ ত্রাণের দাবি। আমার নাম সুমিত্রা দাস, মুর্শিদাবাদ জেলা। এক লাখ টাকার ক্ষতি।",
    "mr": "आपत्ती मदत दावा. माझे नाव सुरेश पाटील आहे, सोलापूर जिल्हा. एक लाख रुपयांचे नुकसान.",
    "te": "విపత్తు సహాయ దరఖాస్తు. నా పేరు వెంకట రావు, కృష్ణా జిల్లా. రెండు లక్షల రూపాయల నష్టం.",
    "ta": "பேரிடர் நிவாரண கோரிக்கை. என் பெயர் முருகன், நாகப்பட்டினம் மாவட்டம். ஒரு லட்சம் ரூபாய் இழப்பு.",
}


@dataclass
class ASRResult:
    text: str
    language: str
    confidence: float
    provider: str


class ASRError(RuntimeError):
    pass


_model = None
_device: str | None = None
_force_cpu = False
_lock = threading.Lock()


def _load(settings: Settings):
    global _model, _device
    with _lock:
        if _model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise ASRError("faster-whisper is not installed: pip install faster-whisper") from exc
            device = "cpu" if _force_cpu else settings.whisper_device
            if device == "auto":
                try:
                    import ctranslate2

                    device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
                except Exception:  # noqa: BLE001
                    device = "cpu"
            compute = "float16" if device == "cuda" else "int8"
            log.info("loading Whisper %s on %s (%s)", settings.whisper_model, device, compute)
            _model = WhisperModel(settings.whisper_model, device=device, compute_type=compute)
            _device = device
        return _model


def _is_cuda_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("cublas", "cudnn", "cuda", "cudart"))


def _fall_back_to_cpu() -> None:
    """GPU found but CUDA libraries missing: reload the model on CPU."""
    global _model, _force_cpu
    log.warning("CUDA libraries not available; switching Whisper to CPU")
    with _lock:
        _model = None
        _force_cpu = True


def warm_up(settings: Settings) -> None:
    """Load the model at startup so the first request isn't slow."""
    _load(settings)


def _run(settings: Settings, path: str, language: str | None):
    model = _load(settings)
    segments, info = model.transcribe(
        path,
        language=language,  # None = auto-detect
        initial_prompt=PROMPTS.get(language or "", None),
        beam_size=5,
        vad_filter=True,
        without_timestamps=True,
    )
    return list(segments), info


def transcribe(audio: Audio, language: str | None, settings: Settings) -> ASRResult:
    language = normalize_lang(language)

    f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    try:
        f.write(audio.wav_bytes)
        f.close()
        try:
            segments, info = _run(settings, f.name, language)
        except Exception as exc:  # noqa: BLE001
            if _device == "cuda" and _is_cuda_error(exc):
                _fall_back_to_cpu()
                segments, info = _run(settings, f.name, language)
            else:
                raise
    except ASRError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ASRError(f"Whisper failed: {exc}") from exc
    finally:
        try:
            os.unlink(f.name)
        except OSError:
            pass

    text = " ".join(s.text.strip() for s in segments).strip()
    if not text:
        raise ASRError("no speech found in the audio")

    detected = normalize_lang(info.language)
    if language is None and detected is None:
        raise ASRError(f"detected language '{info.language}' is not supported")

    # avg_logprob is roughly -0.2 (clear) to -1.5 (unclear); map to 0..1.
    avg = sum(s.avg_logprob for s in segments) / len(segments)
    conf = max(0.0, min(1.0, 1.0 + avg / 1.5))
    return ASRResult(text=text, language=language or detected, confidence=round(conf, 3), provider="whisper")
