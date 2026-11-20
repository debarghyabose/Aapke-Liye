"""Audio intake: decode, download, and convert to 16 kHz mono 16-bit WAV."""
from __future__ import annotations

import base64
import io
import shutil
import subprocess
import wave
from dataclasses import dataclass

import httpx

TARGET_RATE = 16000


class AudioError(ValueError):
    """Raised for audio we cannot use; the message is safe to show Member 2."""


@dataclass
class Audio:
    wav_bytes: bytes  # 16 kHz, mono, 16-bit PCM WAV
    duration_s: float

    @property
    def base64(self) -> str:
        return base64.b64encode(self.wav_bytes).decode("ascii")


def load_audio(audio_base64: str | None, audio_url: str | None, max_seconds: int) -> Audio:
    if audio_base64:
        try:
            raw = base64.b64decode(audio_base64, validate=False)
        except Exception as exc:  # noqa: BLE001
            raise AudioError("audio_base64 is not valid base64") from exc
    elif audio_url:
        try:
            resp = httpx.get(audio_url, timeout=15, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise AudioError(f"could not download audio_url: {exc}") from exc
        raw = resp.content
    else:
        raise AudioError("send audio_base64, audio_url or text")

    if not raw:
        raise AudioError("audio is empty")

    wav = to_wav16k(raw)
    duration = _wav_duration(wav)
    if duration < 0.3:
        raise AudioError("audio is too short")
    if duration > max_seconds:
        raise AudioError(f"audio is longer than {max_seconds} s; ask the user to send shorter notes")
    return Audio(wav_bytes=wav, duration_s=duration)


def to_wav16k(raw: bytes) -> bytes:
    """Return 16 kHz mono 16-bit WAV. Uses ffmpeg if installed, else PyAV (bundled with faster-whisper)."""
    if _is_target_wav(raw):
        return raw
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return _pyav_to_wav16k(raw)
    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "error",
        "-i", "pipe:0",
        "-ac", "1", "-ar", str(TARGET_RATE), "-sample_fmt", "s16",
        # trim leading and trailing silence
        "-af", "silenceremove=start_periods=1:start_threshold=-45dB:"
               "stop_periods=-1:stop_threshold=-45dB:stop_duration=0.6",
        "-f", "wav", "pipe:1",
    ]
    proc = subprocess.run(cmd, input=raw, capture_output=True, timeout=30)
    if proc.returncode != 0 or not proc.stdout:
        raise AudioError(f"could not decode audio: {proc.stderr.decode(errors='ignore')[:200]}")
    return _fix_wav_sizes(proc.stdout)


def _fix_wav_sizes(wav: bytes) -> bytes:
    """ffmpeg writing WAV to a pipe cannot seek back to fill in the RIFF and data sizes, so
    they hold placeholder values (a 12 s note reads as ~37 hours). Rewrite them from the
    real byte count."""
    pos = 12
    while pos + 8 <= len(wav):
        chunk, size = wav[pos:pos + 4], int.from_bytes(wav[pos + 4:pos + 8], "little")
        if chunk == b"data":
            data_len = len(wav) - (pos + 8)
            out = bytearray(wav)
            out[4:8] = (len(wav) - 8).to_bytes(4, "little")
            out[pos + 4:pos + 8] = data_len.to_bytes(4, "little")
            return bytes(out)
        pos += 8 + size + (size & 1)
    return wav


def _pyav_to_wav16k(raw: bytes) -> bytes:
    """Decode any format (webm/ogg from browsers, mp3, m4a) with PyAV's built-in ffmpeg libraries."""
    try:
        import av
    except ImportError as exc:
        raise AudioError("cannot decode this audio: install ffmpeg or `pip install av`") from exc
    pcm = bytearray()
    try:
        with av.open(io.BytesIO(raw)) as container:
            resampler = av.AudioResampler(format="s16", layout="mono", rate=TARGET_RATE)
            for frame in container.decode(audio=0):
                for out in resampler.resample(frame):
                    pcm += out.to_ndarray().tobytes()
            for out in resampler.resample(None):  # flush
                pcm += out.to_ndarray().tobytes()
    except Exception as exc:  # noqa: BLE001
        raise AudioError(f"could not decode audio: {exc}") from exc
    if not pcm:
        raise AudioError("no audio found in the recording")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TARGET_RATE)
        w.writeframes(bytes(pcm))
    return buf.getvalue()


def _is_target_wav(raw: bytes) -> bool:
    if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        return False
    try:
        with wave.open(io.BytesIO(raw)) as w:
            return w.getframerate() == TARGET_RATE and w.getnchannels() == 1 and w.getsampwidth() == 2
    except wave.Error:
        return False


def _wav_duration(wav: bytes) -> float:
    try:
        with wave.open(io.BytesIO(wav)) as w:
            return w.getnframes() / float(w.getframerate())
    except wave.Error as exc:
        raise AudioError("converted audio is not a readable WAV") from exc
