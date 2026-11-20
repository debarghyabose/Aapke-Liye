"""Make demo photos that pass the location and time checks on stage.

    Member-3\\.venv\\Scripts\\python Member-3\\scripts\\make_stage_photos.py

Run it on the morning of the demo: it stamps each photo's EXIF with
- GPS of a building that Copernicus EMS graded "Destroyed" inside the Cyclone Fani flood map
  (Puri, data/copernicus/EMSR357_*), so "inside the disaster area" and the satellite check pass;
- the current time, so the capture time is after DISASTER_START and within a day of the upload.

Output: data/demo/stage/*.jpg. Upload them on the app's photo step. The pictures are the
Wikimedia Commons photos in data/demo/photos (credits and licenses: data/demo/photos/ATTRIBUTION.md);
their real locations are not Puri, only the EXIF is changed, for demonstration.
"""
from __future__ import annotations

from datetime import datetime
from fractions import Fraction
from pathlib import Path

import piexif

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "demo" / "photos"
OUT = ROOT / "data" / "demo" / "stage"

# A "Destroyed" residential building inside the EMSR357 flood extent (Puri, Odisha).
PURI_LAT, PURI_LON = 19.829505, 85.853938

PHOTOS = {
    "collapsed_houses_nepal_2015.jpg": "puri_house_destroyed.jpg",
    "flood_home_tipomia_assam.jpg": "puri_flooded_home.jpg",
    "flooded_paddy_humbarli.jpg": "puri_flooded_paddy.jpg",
}


def _dms(value: float) -> tuple:
    value = abs(value)
    d = int(value)
    m = int((value - d) * 60)
    s = Fraction((value - d - m / 60) * 3600).limit_denominator(1000)
    return ((d, 1), (m, 1), (s.numerator, s.denominator))


def stamp(src: Path, dst: Path, lat: float, lon: float, when: datetime) -> None:
    stamp_text = when.strftime("%Y:%m:%d %H:%M:%S").encode()
    exif = {
        "0th": {piexif.ImageIFD.DateTime: stamp_text},
        "Exif": {piexif.ExifIFD.DateTimeOriginal: stamp_text,
                 piexif.ExifIFD.DateTimeDigitized: stamp_text},
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: b"N" if lat >= 0 else b"S",
            piexif.GPSIFD.GPSLatitude: _dms(lat),
            piexif.GPSIFD.GPSLongitudeRef: b"E" if lon >= 0 else b"W",
            piexif.GPSIFD.GPSLongitude: _dms(lon),
        },
    }
    piexif.insert(piexif.dump(exif), str(src), str(dst))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    for i, (src, dst) in enumerate(PHOTOS.items()):
        # spread the photos a few metres apart so they don't look like one shot
        stamp(SRC / src, OUT / dst, PURI_LAT + i * 0.00005, PURI_LON + i * 0.00005, now)
        print(f"  {OUT / dst}")
    print(f"Stamped {len(PHOTOS)} photos with Puri GPS and time {now:%d-%m-%Y %H:%M}.")


if __name__ == "__main__":
    main()
