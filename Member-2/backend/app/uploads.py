"""Upload checks: allow-listed content types, magic bytes and size limits."""
from dataclasses import dataclass

from fastapi import HTTPException, UploadFile

MB = 1024 * 1024
MAX_REQUEST_BYTES = 16 * MB   # checked from Content-Length before the body is read (main.py)
MAX_PHOTOS_PER_CLAIM = 10


@dataclass(frozen=True)
class Kind:
    name: str
    max_bytes: int
    declared: frozenset[str]          # content types the client may send
    formats: dict[str, str]           # detected format -> content type we store


AUDIO = Kind("audio", 15 * MB,
             frozenset({"audio/webm", "audio/ogg", "audio/opus", "audio/mpeg", "audio/mp3",
                        "audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave",
                        "audio/mp4", "audio/m4a", "audio/x-m4a"}),
             {"webm": "audio/webm", "ogg": "audio/ogg", "mp3": "audio/mpeg",
              "wav": "audio/wav", "m4a": "audio/mp4"})

PHOTO = Kind("photo", 10 * MB,
             frozenset({"image/jpeg", "image/jpg", "image/png", "image/webp"}),
             {"jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"})


def sniff(data: bytes) -> str | None:
    """Detect the real file format from its first bytes."""
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "wav"
    if data[:4] == b"\x1a\x45\xdf\xa3":           # EBML header (WebM/Matroska)
        return "webm"
    if data[:4] == b"OggS":
        return "ogg"
    if data[4:8] == b"ftyp":                       # MP4 container (m4a, Safari recordings)
        return "m4a"
    if data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0):
        return "mp3"
    return None


async def read_upload(file: UploadFile, kind: Kind) -> tuple[bytes, str, str]:
    """Return (bytes, content type, format) or raise 413 / 415."""
    declared = (file.content_type or "").split(";")[0].strip().lower()
    if declared not in kind.declared:
        raise HTTPException(415, f"Unsupported {kind.name} type. Allowed: "
                                 + ", ".join(sorted(kind.formats)))
    data = await file.read(kind.max_bytes + 1)
    if len(data) > kind.max_bytes:
        raise HTTPException(413, f"{kind.name.title()} is too large "
                                 f"(max {kind.max_bytes // MB} MB)")
    fmt = sniff(data)
    if fmt not in kind.formats:
        raise HTTPException(415, f"The file is not a valid {kind.name}")
    return data, kind.formats[fmt], fmt
