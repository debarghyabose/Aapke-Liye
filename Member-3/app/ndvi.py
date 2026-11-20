"""Crop before/after check from Sentinel-2 satellite images (NDVI).

NDVI = (NIR - Red) / (NIR + Red) measures how green the vegetation is: about 0.6-0.9 for a
healthy crop, 0.2-0.3 for bare soil, below 0 for water. For a crop-damage claim we compare
the field:
  before: the clearest image 45-120 days before the photo (2-4 months, the user's idea)
  after:  the clearest image from 10 days before to 7 days after the photo
A big drop, or the field under water afterwards, is consistent with crop damage. Little
vegetation before, or a healthy field after, is a note for the official to check.

Images: Sentinel-2 Level-2A (10 m pixels) from Earth Search (AWS open data, no account).
Privacy: the image search uses a coarse box (about 25 km), never the exact field, and no
claim ID, name or phone is sent. Only small windows of public images are read.
Sentinel-2 started in mid-2015 and monsoon images are often cloudy: then the result is
"no clear image", never a guess.
"""
import logging
import math
from datetime import datetime, timedelta
from typing import Optional

from app import config

log = logging.getLogger(__name__)

STAC_URL = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"
# Sentinel-2 scene classification (SCL): pixels usable for NDVI.
CLEAR = {4, 5, 6, 7}     # vegetation, bare soil, water, unclassified
WATER = 6
MIN_CLEAR_FRACTION = 0.6

# Thresholds (NDVI units)
DROP = 0.15              # before - after at least this = vegetation loss
LOW_BEFORE = 0.30        # below this before = little or no crop growing


class Sentinel2:
    """Reads small NDVI windows around a point from public Sentinel-2 COGs."""

    def __init__(self, url: str = STAC_URL):
        self.url = url

    @staticmethod
    def coarse_box(lat: float, lon: float, cell: float = 0.25) -> list[float]:
        """The 0.25-degree (~25 km) cell containing the point: sent instead of the field."""
        x0, y0 = math.floor(lon / cell) * cell, math.floor(lat / cell) * cell
        return [x0, y0, x0 + cell, y0 + cell]

    def _search(self, lat: float, lon: float, start: datetime, end: datetime) -> list:
        from pystac_client import Client

        items = Client.open(self.url).search(
            collections=[COLLECTION], bbox=self.coarse_box(lat, lon),
            datetime=f"{start:%Y-%m-%d}/{end:%Y-%m-%d}",
            query={"eo:cloud_cover": {"lt": 70}}, max_items=50).items()
        # The coarse box also returns neighbouring tiles that don't cover this field: keep only
        # scenes whose footprint contains the point (checked here, so the field stays private).
        from shapely.geometry import Point, shape

        pt = Point(lon, lat)
        items = [i for i in items if i.geometry and shape(i.geometry).contains(pt)]
        return sorted(items, key=lambda i: i.properties.get("eo:cloud_cover", 100))

    @staticmethod
    def _window(item, lat: float, lon: float, radius_m: float):
        """NDVI median, clear fraction and water fraction in a square around the point."""
        import numpy as np
        import rasterio
        from pyproj import Transformer
        from rasterio.windows import from_bounds

        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", AWS_NO_SIGN_REQUEST="YES"):
            with rasterio.open(item.assets["red"].href) as red_ds:
                x, y = Transformer.from_crs(4326, red_ds.crs, always_xy=True).transform(lon, lat)
                b = (x - radius_m, y - radius_m, x + radius_m, y + radius_m)
                win = from_bounds(*b, transform=red_ds.transform)
                red = red_ds.read(1, window=win, boundless=True, fill_value=0).astype("float32")
            with rasterio.open(item.assets["nir"].href) as nir_ds:
                nir = nir_ds.read(1, window=from_bounds(*b, transform=nir_ds.transform),
                                  boundless=True, fill_value=0, out_shape=red.shape).astype("float32")
            with rasterio.open(item.assets["scl"].href) as scl_ds:   # 20 m: resampled to the 10 m grid
                scl = scl_ds.read(1, window=from_bounds(*b, transform=scl_ds.transform),
                                  boundless=True, fill_value=0, out_shape=red.shape)
        clear = np.isin(scl, list(CLEAR)) & ((red + nir) > 0)
        if clear.sum() == 0:
            return None, 0.0, 0.0
        ndvi = (nir - red) / np.maximum(nir + red, 1)
        return (float(np.median(ndvi[clear])), float(clear.mean()),
                float((scl[clear] == WATER).mean()))

    def best(self, lat: float, lon: float, start: datetime, end: datetime, radius_m: float,
             tries: int = 4) -> Optional[dict]:
        """Clearest usable image in the date range: {"date", "ndvi", "water"} or None."""
        for item in self._search(lat, lon, start, end)[:tries]:
            try:
                ndvi, clear, water = self._window(item, lat, lon, radius_m)
            except Exception as e:  # one unreadable scene: try the next
                log.warning("Sentinel-2 scene %s unreadable: %s", item.id, type(e).__name__)
                continue
            if ndvi is not None and clear >= MIN_CLEAR_FRACTION:
                return {"date": item.datetime.date().isoformat(), "ndvi": round(ndvi, 3),
                        "water": round(water, 2), "scene": item.id}
        return None


def interpret(before: Optional[dict], after: Optional[dict]) -> dict:
    """Turn two NDVI readings into a status and a note for the official."""
    out = {"status": "no_clear_image", "ndvi_before": None, "ndvi_after": None,
           "date_before": None, "date_after": None}
    if before:
        out.update(ndvi_before=before["ndvi"], date_before=before["date"])
    if after:
        out.update(ndvi_after=after["ndvi"], date_after=after["date"])
    if not before or not after:
        missing = " and ".join(w for w, x in (("before", before), ("after", after)) if not x)
        out["note"] = f"Satellite crop check (Sentinel-2): no clear image {missing} the photo date (clouds?)"
        return out
    b, a = before["ndvi"], after["ndvi"]
    if after["water"] >= 0.5:
        out["status"] = "water_after"
        out["note"] = (f"Satellite crop check (Sentinel-2): field was green (NDVI {b:.2f}) on {before['date']} "
                       f"and under water on {after['date']}: consistent with flood damage")
    elif b < LOW_BEFORE:
        out["status"] = "little_vegetation_before"
        out["note"] = (f"Satellite crop check (Sentinel-2): little vegetation at this spot on {before['date']} "
                       f"(NDVI {b:.2f}): check that a crop was growing here (the field may have been "
                       "between crop seasons then)")
    elif b - a >= DROP:
        out["status"] = "vegetation_loss"
        out["note"] = (f"Satellite crop check (Sentinel-2): vegetation dropped from NDVI {b:.2f} ({before['date']}) "
                       f"to {a:.2f} ({after['date']}): consistent with crop damage")
    else:
        out["status"] = "no_change"
        out["note"] = (f"Satellite crop check (Sentinel-2): vegetation about the same before ({b:.2f}, "
                       f"{before['date']}) and after ({a:.2f}, {after['date']}): check the damage on site")
    return out


_source = None


def get_source():
    global _source
    if _source is None:
        _source = Sentinel2()
    return _source


def set_source(src) -> None:
    """For tests: a fake source with .best(lat, lon, start, end, radius_m)."""
    global _source
    _source = src


def crop_check(lat: float, lon: float, taken_at: datetime) -> dict:
    src = get_source()
    r = config.NDVI_RADIUS_M
    try:
        before = src.best(lat, lon, taken_at - timedelta(days=120), taken_at - timedelta(days=45), r)
        # "After" must not start before the disaster, or a pre-disaster image could be picked
        # for a photo taken a few days after it.
        after_start = max(taken_at - timedelta(days=10), config.DISASTER_START)
        after = src.best(lat, lon, after_start, taken_at + timedelta(days=7), r)
    except Exception as e:  # network down, service changed...
        log.warning("Sentinel-2 crop check failed: %s", type(e).__name__)
        return {"status": "error", "note": "Satellite crop check (Sentinel-2) could not reach the image service",
                "ndvi_before": None, "ndvi_after": None, "date_before": None, "date_after": None}
    return interpret(before, after)
