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
    """(geometry, properties) pairs from GeoJSON, shapefile or Open Buildings CSV, always in
    longitude/latitude. Shapefiles in metres (e.g. Copernicus EMS files in UTM) are converted
    using their .prj file."""
    suffix = path.suffix.lower()
    if suffix in (".geojson", ".json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        feats = data["features"] if data.get("type") == "FeatureCollection" else [data]
        out = [(shape(f["geometry"] if "geometry" in f else f), f.get("properties") or {})
               for f in feats if f.get("geometry", f)]
    elif suffix == ".shp":
        import shapefile  # pyshp

        with shapefile.Reader(str(path)) as r:
            names = [f[0] for f in r.fields[1:]]
            out = [(shape(sr.shape.__geo_interface__), dict(zip(names, sr.record)))
                   for sr in r.shapeRecords() if sr.shape.points]
        prj = path.with_suffix(".prj")
        if prj.exists() and "PROJCS" in prj.read_text(errors="ignore").upper():
            from pyproj import CRS, Transformer

            t = Transformer.from_crs(CRS.from_wkt(prj.read_text(errors="ignore")), 4326, always_xy=True)
            to_lonlat = lambda xy: __import__("numpy").column_stack(t.transform(xy[:, 0], xy[:, 1]))  # noqa: E731
            out = [(shapely.transform(g, to_lonlat), p) for g, p in out]
            log.info("Converted %s from %s to longitude/latitude", path.name, CRS.from_wkt(prj.read_text(errors="ignore")).name)
    elif suffix == ".csv":
        csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
        out = []
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("geometry"):
                    out.append((wkt.loads(row["geometry"]), {}))
                elif row.get("latitude") and row.get("longitude"):
                    out.append((Point(float(row["longitude"]), float(row["latitude"])), {}))
    else:
        raise ValueError(f"Unsupported map file type: {path.name} (use .geojson, .shp or .csv)")
    # A file still in metres would put every point in the wrong place: refuse it.
    for g, _ in out[:50]:
        minx, miny, maxx, maxy = g.bounds
        if not (-180 <= minx <= 180 and -180 <= maxx <= 180 and -90 <= miny <= 90 and -90 <= maxy <= 90):
            raise ValueError(f"{path.name} is not in longitude/latitude (add its .prj file, or convert to WGS84)")
    return out


class Layer:
    """Geometries from several files, with a spatial index and the area each file covers."""

    def __init__(self, files: list[str], kind: str):
        self.geoms: list = []
        self.props: list[dict] = []       # same order as geoms
        self.coverage: list[tuple] = []   # (name, bbox polygon)
        for f in files:
            p = Path(f)
            if not p.exists():
                log.warning("%s file not found: %s", kind, p)
                continue
            try:
                pairs = [(g, pr) for g, pr in _read_geometries(p) if not g.is_empty]
            except Exception as e:  # a broken file must not stop the service
                log.error("Could not read %s file %s: %s", kind, p, e)
                continue
            g = [x for x, _ in pairs]
            if g:
                self.geoms.extend(g)
                self.props.extend(pr for _, pr in pairs)
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
            if area.buffer(margin_deg).covers(pt):   # covers: points on the edge count too
                return name
        return None

    def near(self, lat: float, lon: float, radius_m: float) -> list:
        return [g for g, _ in self.near_with_props(lat, lon, radius_m)]

    def near_with_props(self, lat: float, lon: float, radius_m: float) -> list[tuple]:
        if self.tree is None:
            return []
        deg = radius_m / (M_PER_DEG_LAT * max(0.2, math.cos(math.radians(lat))))
        idx = self.tree.query(Point(lon, lat).buffer(deg))
        return [(self.geoms[i], self.props[i]) for i in idx]


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
        # Margin: a photo just outside the outermost mapped building is still in the mapped area.
        if self.buildings.covering(lat, lon, margin_m=config.BUILDING_SEARCH_M) is None:
            return out
        r = config.BUILDING_SEARCH_M
        near = self.buildings.near_with_props(lat, lon, r * 2)
        if not near:
            out["building_found"] = False
            return out
        d, props = min(((_distance_m(lat, lon, g), p) for g, p in near), key=lambda x: x[0])
        out.update(building_found=d <= r, distance_m=round(d, 1))
        # Copernicus EMS grading products rate each building from satellite images.
        grade = props.get("damage_gra") or props.get("damage_grade")
        if d <= r and grade and str(grade).lower() not in ("", "none", "unknown", "not applicable"):
            out["damage_grade"] = str(grade)
            out["grade_source"] = props.get("source") or "Copernicus EMS"
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
