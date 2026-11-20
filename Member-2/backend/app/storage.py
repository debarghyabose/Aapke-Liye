"""
Uploaded and generated files, encrypted at rest with Fernet (STORAGE_ENCRYPTION_KEY).
File names are random UUIDs, never the client's filename. Files are decrypted only
when they are read back (downloads, PDF thumbnails, retries to Member 1/3).
"""
import logging
import uuid
from functools import lru_cache

from cryptography.fernet import Fernet, MultiFernet
from starlette.concurrency import run_in_threadpool

from .config import settings

log = logging.getLogger(__name__)


@lru_cache
def _fernet() -> MultiFernet:
    keys = settings.storage_encryption_keys
    if not keys:  # development only; production refuses to start without a key
        key_file = settings.storage_dir / ".dev-encryption-key"
        if not key_file.exists():
            key_file.parent.mkdir(parents=True, exist_ok=True)
            key_file.write_bytes(Fernet.generate_key())
            log.warning("STORAGE_ENCRYPTION_KEY not set: created a development key in %s",
                        key_file)
        keys = [key_file.read_text().strip()]
    return MultiFernet([Fernet(k) for k in keys])  # first key encrypts; all keys decrypt


def _write(rel: str, data: bytes) -> None:
    path = settings.storage_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_fernet().encrypt(data))


def _read(rel: str) -> bytes:
    return _fernet().decrypt((settings.storage_dir / rel).read_bytes())


async def save(kind: str, data: bytes) -> str:
    """Encrypt and store bytes under <STORAGE_DIR>/<kind>/<uuid>. Returns the relative path."""
    rel = f"{kind}/{uuid.uuid4().hex}"
    await run_in_threadpool(_write, rel, data)
    return rel


async def read(rel: str) -> bytes:
    return await run_in_threadpool(_read, rel)
