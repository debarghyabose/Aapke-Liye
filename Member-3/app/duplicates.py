"""Flag the same photo or the same claim sent twice.

The in-memory index is for the demo; Member 2 will back it with a photo_hashes table.
"""
import io
from typing import Optional

import imagehash
from PIL import Image

from app import config
from app.exif_check import distance_km


class DuplicateIndex:
    def __init__(self) -> None:
        self._hashes: list[tuple[imagehash.ImageHash, str]] = []  # (hash, claim_id)
        self._claims: list[tuple[str, float, float, str]] = []  # (phone, lat, lon, claim_id)

    @staticmethod
    def phash(photo: bytes) -> imagehash.ImageHash:
        return imagehash.phash(Image.open(io.BytesIO(photo)))

    def find_photo(self, photo: bytes) -> Optional[str]:
        h = self.phash(photo)
        for other, claim_id in self._hashes:
            if h - other <= config.PHASH_MAX_DISTANCE:
                return claim_id
        return None

    def find_claim(self, phone: str, lat: Optional[float], lon: Optional[float]) -> Optional[str]:
        if lat is None or lon is None:
            return None
        for p, la, lo, claim_id in self._claims:
            if p == phone and distance_km(lat, lon, la, lo) * 1000 <= config.SAME_CLAIM_RADIUS_M:
                return claim_id
        return None

    def add(self, claim_id: str, phone: str, lat: Optional[float], lon: Optional[float], photos: list[bytes]) -> None:
        for photo in photos:
            self._hashes.append((self.phash(photo), claim_id))
        if lat is not None and lon is not None:
            self._claims.append((phone, lat, lon, claim_id))
