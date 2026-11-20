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
