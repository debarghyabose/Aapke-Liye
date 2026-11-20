"""Fill the dashboard with demo claims that show every Member 3 feature (Cyclone Fani, Puri).

Uses the real photos in data/demo/photos (see ATTRIBUTION.md) and adds demo GPS/time in memory,
then sends them through the running service's /verify exactly like Member 2 does. The damage AI
(Gemini), the Copernicus maps and the Sentinel-2 crop check all run for real.

Before running:
  1. .env has the Puri demo settings (see data/copernicus/README.md) and GEMINI_API_KEY.
  2. The service is running:  uvicorn app.main:app --port 8002
Then, from Member-3/:
    python scripts/seed_demo.py

Every claim ID starts with "DEMO-". Uses 7 Gemini calls (free tier): run it early on demo day.
To start over: stop the service, delete member3.db, start the service, run this again.
"""
import argparse
import io
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx2 as httpx
import piexif
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import config  # noqa: E402  (reads .env: the dashboard key is used, never printed)

PHOTOS = ROOT / "data" / "demo" / "photos"
BUILDINGS = ROOT / "data" / "copernicus" / "EMSR357_puri_building_damage_2019.geojson"
DEMO_PHONE = "+91 90000 12345"          # not a real person's number


def _deg(v: float):
    v = abs(v); d = int(v); m = int((v - d) * 60); s = round(((v - d) * 60 - m) * 60 * 100)
    return ((d, 1), (m, 1), (s, 100))


def with_exif(img: Image.Image, lat: float, lon: float, when: datetime, quality: int = 90) -> bytes:
    """JPEG with demo GPS + capture time in its EXIF (the photo files on disk are not changed)."""
    exif = {"0th": {}, "1st": {},
            "Exif": {piexif.ExifIFD.DateTimeOriginal: when.strftime("%Y:%m:%d %H:%M:%S").encode()},
            "GPS": {piexif.GPSIFD.GPSLatitudeRef: b"N", piexif.GPSIFD.GPSLatitude: _deg(lat),
                    piexif.GPSIFD.GPSLongitudeRef: b"E", piexif.GPSIFD.GPSLongitude: _deg(lon)}}
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=quality, exif=piexif.dump(exif))
    return buf.getvalue()


def chat_screenshot(photo: Image.Image) -> Image.Image:
    """A fake 'forwarded in a chat app' screenshot of a damage photo (for the fake-photo check)."""
    shot = Image.new("RGB", (720, 1280), (236, 229, 221))
    d = ImageDraw.Draw(shot)
    d.rectangle([0, 0, 720, 150], fill=(7, 94, 84))
    d.text((20, 15), "10:42   4G  87%", fill="white")
    d.text((90, 85), "Village Relief Group  (Forwarded many times)", fill="white")
    d.rounded_rectangle([30, 220, 690, 800], 18, fill="white")
    shot.paste(photo.convert("RGB").resize((640, 480)), (40, 240))
    d.text((50, 735), "Forwarded - house collapsed, please share", fill=(60, 60, 60))
    return shot


def demo_claims() -> list[tuple]:
    graded = json.loads(BUILDINGS.read_text(encoding="utf-8"))["features"]
    dlon, dlat = next(f for f in graded if f["properties"]["damage_gra"] == "Destroyed")["geometry"]["coordinates"]
    glon, glat = next(f for f in graded if f["properties"]["damage_gra"] == "Damaged")["geometry"]["coordinates"]
    open_ = lambda name: Image.open(PHOTOS / name)  # noqa: E731
    collapsed = open_("collapsed_houses_nepal_2015.jpg")
    t = datetime(2019, 5, 5, 10, 0)            # 2 days after Fani's landfall
    return [
        ("DEMO-PURI-001", "Collapsed house on a building Copernicus graded 'Destroyed', inside the flood map",
         with_exif(collapsed, dlat, dlon, t), {"phone": DEMO_PHONE}),
        ("DEMO-PURI-002", "Flooded house on a 'Damaged' building outside the flood map; phone 54 km away",
         with_exif(open_("flood_home_tipomia_assam.jpg"), glat, glon, t),
         {"phone": DEMO_PHONE, "lat": "20.2961", "lon": "85.8245"}),
        ("DEMO-PURI-003", "Re-saved copy of claim 001's photo (duplicate)",
         with_exif(collapsed, dlat, dlon, t, quality=70), {"phone": DEMO_PHONE}),
        ("DEMO-PURI-004", "Different photo taken 10 m from claim 001 (possibly the same house)",
         with_exif(open_("flooded_village_bihar_aerial.jpg"), dlat + 0.00009, dlon, t), {"phone": DEMO_PHONE}),
        ("DEMO-PURI-005", "Screenshot from a chat app; 5th claim from the same phone",
         with_exif(chat_screenshot(collapsed), dlat + 0.01, dlon - 0.01, t), {"phone": DEMO_PHONE}),
        ("DEMO-CROP-006", "Paddy field in villages west of Puri (Sentinel-2 before/after runs in the background)",
         with_exif(open_("flooded_paddy_humbarli.jpg"), 19.84, 85.70, datetime(2019, 5, 10, 9, 0)), {}),
        ("DEMO-HOUSE-007", "Intact house far outside the disaster area",
         with_exif(open_("village_house_india_2022.jpg"), 22.57, 88.36, t), {}),
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8002")
    ap.add_argument("--force", action="store_true", help="add the demo claims even if some already exist")
    args = ap.parse_args()
    base = args.url.rstrip("/")
    headers = {"X-Dashboard-Key": config.DASHBOARD_API_KEY} if config.DASHBOARD_API_KEY else {}

    try:
        httpx.get(f"{base}/health", timeout=5).raise_for_status()
    except Exception:
        sys.exit(f"Member 3's service is not running at {base}. Start it: uvicorn app.main:app --port 8002")
    r = httpx.get(f"{base}/dashboard/claims.geojson", headers=headers, timeout=10)
    if r.status_code == 401:
        sys.exit("The service refused the dashboard key: check DASHBOARD_API_KEY in .env")
    existing = [f["properties"]["claim_id"] for f in r.json()["features"] if f["properties"]["claim_id"].startswith("DEMO-")]
    if existing and not args.force:
        sys.exit(f"{len(existing)} demo claims already exist. Re-adding them would flag every photo as a duplicate.\n"
                 "To start over: stop the service, delete member3.db, start it again, then run this script.")
    if config.DISASTER_START.year != 2019 or abs(config.ZONE_LAT - 19.85) > 0.5:
        print("Note: .env is not set to the Cyclone Fani / Puri demo, so several checks will differ.\n")

    for cid, what, photo, extra in demo_claims():
        for attempt in range(5):
            r = httpx.post(f"{base}/verify", files={"photo": ("photo.jpg", photo, "image/jpeg")},
                           data={"claim_id": cid, **extra}, timeout=60)
            if r.status_code != 503:
                break
            print(f"  {cid}: damage AI busy (free tier), retrying in 20 s...")
            time.sleep(20)
        if r.status_code != 200:
            print(f"{cid}: FAILED (HTTP {r.status_code}) {r.text[:150]}")
            continue
        b = r.json()
        print(f"\n{cid}  {what}\n  damage {b['damage_score']} | duplicate {b['duplicate']}")
        for n in b["notes"]:
            print("   -", n)
        time.sleep(3)

    print("\nWaiting for the Sentinel-2 crop check (up to 2 minutes)...")
    for _ in range(24):
        feats = httpx.get(f"{base}/dashboard/claims.geojson", headers=headers, timeout=10).json()["features"]
        crop = next((f["properties"].get("crop_satellite") for f in feats
                     if f["properties"]["claim_id"] == "DEMO-CROP-006"), None)
        if crop and crop.get("status") != "pending":
            print("  DEMO-CROP-006:", crop.get("note"))
            break
        time.sleep(5)
    else:
        print("  Still running: it will appear on the dashboard when done.")
    s = httpx.get(f"{base}/dashboard/summary", headers=headers, timeout=10).json()
    print(f"\nDone: {s['claims']} claims, {s['claims_flagged']} flagged. Open Member 5's dashboard and press Connect live.")


if __name__ == "__main__":
    main()
