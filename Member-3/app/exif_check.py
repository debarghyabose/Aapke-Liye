"""Read GPS + capture time from photo EXIF, and check them against the disaster zone."""
import io
import math
from datetime import datetime
from typing import Optional

import piexif
from PIL import Image

from app import config


def _to_degrees(value, ref: str) -> float:
    d, m, s = (n / den for n, den in value)
    deg = d + m / 60 + s / 3600
    return -deg if ref in ("S", "W") else deg


def read_exif(photo: bytes) -> dict:
    """Return {"lat", "lon", "taken_at"}; any of them may be None if the phone stripped EXIF."""
    out = {"lat": None, "lon": None, "taken_at": None}
    try:
        raw = Image.open(io.BytesIO(photo)).info.get("exif")
        if not raw:
            return out
        exif = piexif.load(raw)
    except Exception:
        return out

    gps = exif.get("GPS", {})
    if piexif.GPSIFD.GPSLatitude in gps and piexif.GPSIFD.GPSLongitude in gps:
        out["lat"] = _to_degrees(gps[piexif.GPSIFD.GPSLatitude], gps.get(piexif.GPSIFD.GPSLatitudeRef, b"N").decode())
        out["lon"] = _to_degrees(gps[piexif.GPSIFD.GPSLongitude], gps.get(piexif.GPSIFD.GPSLongitudeRef, b"E").decode())

    taken = exif.get("Exif", {}).get(piexif.ExifIFD.DateTimeOriginal)
    if taken:
        try:
            out["taken_at"] = datetime.strptime(taken.decode(), "%Y:%m:%d %H:%M:%S")
        except ValueError:
            pass
    return out


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in km."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def gps_in_zone(lat: Optional[float], lon: Optional[float]) -> Optional[bool]:
    """Demo zone is a circle from .env. Phase 2 replaces this with PostGIS ST_Contains."""
    if lat is None or lon is None:
        return None
    return distance_km(lat, lon, config.ZONE_LAT, config.ZONE_LON) <= config.ZONE_RADIUS_KM


def timestamp_valid(taken_at: Optional[datetime], now: Optional[datetime] = None) -> Optional[bool]:
    """Photo must be taken after the disaster started and not in the future."""
    if taken_at is None:
        return None
    now = now or datetime.now()
    return config.DISASTER_START <= taken_at <= now
