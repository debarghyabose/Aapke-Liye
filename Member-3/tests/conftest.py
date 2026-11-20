import io
import sys
from datetime import datetime
from pathlib import Path

import piexif
import pytest
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _deg(value: float):
    value = abs(value)
    d = int(value)
    m = int((value - d) * 60)
    s = round(((value - d) * 60 - m) * 60 * 100)
    return ((d, 1), (m, 1), (s, 100))


def make_photo(seed: int = 0, lat=None, lon=None, taken_at: datetime | None = None) -> bytes:
    """Generate a synthetic JPEG (no real victim photos in tests), optionally with EXIF."""
    img = Image.new("RGB", (256, 256), (200, 200, 200))
    draw = ImageDraw.Draw(img)
    for i in range(8):
        x = (seed * 37 + i * 53) % 220
        y = (seed * 91 + i * 29) % 220
        draw.rectangle([x, y, x + 30, y + 30], fill=((seed * 50 + i * 30) % 255, 40, 120))
    exif = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
    if lat is not None:
        exif["GPS"] = {
            piexif.GPSIFD.GPSLatitudeRef: b"N" if lat >= 0 else b"S",
            piexif.GPSIFD.GPSLatitude: _deg(lat),
            piexif.GPSIFD.GPSLongitudeRef: b"E" if lon >= 0 else b"W",
            piexif.GPSIFD.GPSLongitude: _deg(lon),
        }
    if taken_at is not None:
        exif["Exif"][piexif.ExifIFD.DateTimeOriginal] = taken_at.strftime("%Y:%m:%d %H:%M:%S").encode()
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=piexif.dump(exif))
    return buf.getvalue()


@pytest.fixture
def photo_factory():
    return make_photo


@pytest.fixture(autouse=True)
def no_real_api_calls(monkeypatch):
    """Tests never call the paid vision API, even when .env has a real key."""
    from app import config

    monkeypatch.setattr(config, "VISION_API_KEY", "")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "DASHBOARD_API_KEY", "")
    monkeypatch.setattr(config, "NDVI_ENABLED", False)   # no satellite image requests in tests
    for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM", "PUBLIC_BASE_URL"):
        monkeypatch.setattr(config, k, "")                # no real WhatsApp messages in tests
    # Fixed disaster area and date: tests must not depend on whatever is in someone's .env
    # (for example the Puri demo settings).
    monkeypatch.setattr(config, "ZONE_LAT", 22.5726)
    monkeypatch.setattr(config, "ZONE_LON", 88.3639)
    monkeypatch.setattr(config, "ZONE_RADIUS_KM", 50.0)
    monkeypatch.setattr(config, "DISASTER_START", datetime(2026, 11, 1))


@pytest.fixture(autouse=True)
def no_map_files(monkeypatch):
    """Tests start with no flood or building maps unless they load their own."""
    from app import config, geodata

    monkeypatch.setattr(config, "FLOOD_MAP_FILES", [])
    monkeypatch.setattr(config, "BUILDING_FILES", [])
    geodata.reload_geo()
    yield
    geodata._geo = None


@pytest.fixture(autouse=True)
def temp_store(tmp_path):
    """Each test gets an empty database, never the real member3.db."""
    from app import store

    s = store.Store(str(tmp_path / "test.db"))
    store.set_store(s)
    yield s
    store.set_store(None)
