"""
Image and Document Storage Service
Supports Cloudinary CDN with seamless fallback to secure local storage.
"""
import io
import logging
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple

from . import config

log = logging.getLogger(__name__)

# Initialize Cloudinary if credentials exist
CLOUDINARY_AVAILABLE = False
try:
    import cloudinary
    import cloudinary.uploader
    if config.CLOUDINARY_URL or (config.CLOUDINARY_CLOUD_NAME and config.CLOUDINARY_API_KEY):
        if config.CLOUDINARY_URL:
            cloudinary.config(cloudinary_url=config.CLOUDINARY_URL)
        else:
            cloudinary.config(
                cloud_name=config.CLOUDINARY_CLOUD_NAME,
                api_key=config.CLOUDINARY_API_KEY,
                api_secret=config.CLOUDINARY_API_SECRET,
                secure=True,
            )
        CLOUDINARY_AVAILABLE = True
        log.info("Cloudinary storage enabled.")
except Exception as e:
    log.warning("Cloudinary initialization skipped: %s", e)


class ImageStorage:
    def __init__(self, storage_dir: Path = config.STORAGE_DIR):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def save_image(self, data: bytes, filename: str, content_type: str = "image/jpeg", folder: str = "photos") -> Tuple[str, str]:
        """
        Saves image to Cloudinary if available, otherwise saves locally.
        Returns: (relative_or_remote_url, storage_path)
        """
        file_ext = Path(filename).suffix or ".jpg"
        unique_name = f"{uuid.uuid4().hex}{file_ext}"

        if CLOUDINARY_AVAILABLE:
            try:
                res = cloudinary.uploader.upload(
                    data,
                    folder=f"aapke-liye/{folder}",
                    public_id=Path(unique_name).stem,
                    resource_type="auto"
                )
                secure_url = res.get("secure_url")
                if secure_url:
                    log.info("Uploaded to Cloudinary: %s", secure_url)
                    # Also save a local backup
                    local_path = self.storage_dir / unique_name
                    local_path.write_bytes(data)
                    return secure_url, str(local_path)
            except Exception as e:
                log.error("Cloudinary upload failed: %s, falling back to local storage", e)

        # Local storage fallback
        local_path = self.storage_dir / unique_name
        local_path.write_bytes(data)
        url = f"/storage/{unique_name}"
        return url, str(local_path)

    async def read_file(self, path_or_name: str) -> bytes:
        p = Path(path_or_name)
        if not p.is_absolute():
            p = self.storage_dir / p.name
        if p.exists():
            return p.read_bytes()
        raise FileNotFoundError(f"File not found: {path_or_name}")

storage_service = ImageStorage()
