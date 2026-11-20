"""Satellite and map checks for a claim photo's location.

1. Flood map: was this spot inside the flooded area mapped from satellite images?
   Files: Copernicus EMS rapid-mapping products, ISRO Bhuvan / NRSC inundation layers,
   or any flood-extent polygons, as GeoJSON or shapefile (.shp). Set FLOOD_MAP_FILES.
2. Building: is there a building at the coordinates of a "house destroyed" photo?
   Files: Google Open Buildings (CSV with WKT geometry) or OpenStreetMap buildings exported
   as GeoJSON, for the affected district. Set BUILDING_FILES.

Everything is read from local files, so no victim location is sent to any outside service.
Maps are snapshots: a flood map shows the water when the satellite passed, and building
maps of rural India are incomplete. Both results are notes for an official, never proof.
"""
import csv
import json
import logging
import math
import sys
from pathlib import Path
from typing import Optional

import shapely
from shapely import wkt
from shapely.geometry import Point, box, mapping, shape
from shapely.strtree import STRtree

from app import config

log = logging.getLogger(__name__)
M_PER_DEG_LAT = 110_574.0


def _distance_m(lat: float, lon: float, geom) -> float:
    """Distance in metres, using a flat projection around the point (good to a few metres
    over a few km, which is all these checks need)."""
    scale = (111_320.0 * math.cos(math.radians(lat)), M_PER_DEG_LAT)
    to_m = lambda coords: coords * scale  # noqa: E731  (N x 2 array of lon, lat)
    return shapely.transform(Point(lon, lat), to_m).distance(shapely.transform(geom, to_m))


def _read_geometries(path: Path) -> list:
    """Polygons/points from GeoJSON, shapefile or Open Buildings CSV (WKT `geometry` column)."""
    suffix = path.suffix.lower()
    if suffix in (".geojson", ".json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        feats = data["features"] if data.get("type") == "FeatureCollection" else [data]
        return [shape(f["geometry"] if "geometry" in f else f) for f in feats if f.get("geometry", f)]
    if suffix == ".shp":
        import shapefile  # pyshp

        with shapefile.Reader(str(path)) as r:
            return [shape(s.__geo_interface__) for s in r.shapes() if s.points]
    if suffix == ".csv":
        csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
        geoms = []
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("geometry"):
                    geoms.append(wkt.loads(row["geometry"]))
                elif row.get("latitude") and row.get("longitude"):
                    geoms.append(Point(float(row["longitude"]), float(row["latitude"])))
        return geoms
    raise ValueError(f"Unsupported map file type: {path.name} (use .geojson, .shp or .csv)")


class Layer:
    """Geometries from several files, with a spatial index and the area each file covers."""

    def __init__(self, files: list[str], kind: str):
        self.geoms: list = []
        self.coverage: list[tuple] = []   # (name, bbox polygon)
        for f in files:
            p = Path(f)
            if not p.exists():
                log.warning("%s file not found: %s", kind, p)
                continue
            try:
                g = [x for x in _read_geometries(p) if not x.is_empty]
            except Exception as e:  # a broken file must not stop the service
                log.error("Could not read %s file %s: %s", kind, p, e)
                continue
            if g:
                self.geoms.extend(g)
                minx = min(x.bounds[0] for x in g); miny = min(x.bounds[1] for x in g)
                maxx = max(x.bounds[2] for x in g); maxy = max(x.bounds[3] for x in g)
                self.coverage.append((p.stem, box(minx, miny, maxx, maxy)))
                log.info("Loaded %d %s shapes from %s", len(g), kind, p.name)
        self.tree = STRtree(self.geoms) if self.geoms else None

    def covering(self, lat: float, lon: float, margin_m: float = 0) -> Optional[str]:
        """Name of a file whose area contains the point (with a margin), else None."""
        pt = Point(lon, lat)
        margin_deg = margin_m / M_PER_DEG_LAT
        for name, area in self.coverage:
            if area.buffer(margin_deg).contains(pt):
                return name
        return None

    def near(self, lat: float, lon: float, radius_m: float) -> list:
        if self.tree is None:
            return []
        deg = radius_m / (M_PER_DEG_LAT * max(0.2, math.cos(math.radians(lat))))
        idx = self.tree.query(Point(lon, lat).buffer(deg))
        return [self.geoms[i] for i in idx]


class GeoData:
    def __init__(self):
        self.floods = Layer(config.FLOOD_MAP_FILES, "flood map")
        self.buildings = Layer(config.BUILDING_FILES, "building")

    def flood_check(self, lat: Optional[float], lon: Optional[float]) -> dict:
        """{"in_flood": True/False/None, "distance_km", "map"}. None = no map covers this spot."""
        out = {"in_flood": None, "distance_km": None, "map": None}
        if lat is None or lon is None or self.floods.tree is None:
            return out
        name = self.floods.covering(lat, lon, margin_m=config.FLOOD_COVERAGE_MARGIN_KM * 1000)
        if name is None:
            return out
        out["map"] = name
        search = config.FLOOD_COVERAGE_MARGIN_KM * 1000
        candidates = self.floods.near(lat, lon, search)
        if not candidates:
            out.update(in_flood=False, distance_km=None)
            return out
        d = min(_distance_m(lat, lon, g) for g in candidates)
        # Small tolerance: the map shows water when the satellite passed, plus GPS error.
        out.update(in_flood=d <= config.FLOOD_TOLERANCE_M, distance_km=round(d / 1000, 2))
        return out

    def building_check(self, lat: Optional[float], lon: Optional[float]) -> dict:
        """{"building_found": True/False/None, "distance_m"}. None = no building data here."""
        out = {"building_found": None, "distance_m": None}
        if lat is None or lon is None or self.buildings.tree is None:
            return out
        if self.buildings.covering(lat, lon) is None:
            return out
        r = config.BUILDING_SEARCH_M
        near = self.buildings.near(lat, lon, r * 2)
        if not near:
            out["building_found"] = False
            return out
        d = min(_distance_m(lat, lon, g) for g in near)
        out.update(building_found=d <= r, distance_m=round(d, 1))
        return out

    def flood_geojson(self, tolerance_deg: float = 0.0005, max_features: int = 5000) -> dict:
        """Loaded flood polygons, simplified, for drawing on the dashboard map."""
        feats = []
        for g in self.floods.geoms[:max_features]:
            s = g.simplify(tolerance_deg, preserve_topology=True)
            if not s.is_empty:
                feats.append({"type": "Feature", "geometry": mapping(s), "properties": {}})
        return {"type": "FeatureCollection", "maps": [n for n, _ in self.floods.coverage], "features": feats}


_geo: Optional[GeoData] = None


def get_geo() -> GeoData:
    global _geo
    if _geo is None:
        _geo = GeoData()
    return _geo


def reload_geo() -> GeoData:
    """Re-read the map files (after changing FLOOD_MAP_FILES / BUILDING_FILES, and in tests)."""
    global _geo
    _geo = GeoData()
    return _geo
