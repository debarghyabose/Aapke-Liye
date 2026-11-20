"""Satellite flood map and building map checks (local files, synthetic test shapes)."""
import json
from datetime import datetime

import pytest
import shapefile  # pyshp
from fastapi.testclient import TestClient

from app import config, geodata, sync, verify
from app.duplicates import DuplicateIndex
from app.main import app
from app.schemas import DamageResult

client = TestClient(app)
T = datetime(2026, 11, 5, 10, 0)
# Flooded square: 22.56..22.58 N, 88.35..88.37 E (about 2 x 2 km)
FLOOD = [[88.35, 22.56], [88.37, 22.56], [88.37, 22.58], [88.35, 22.58], [88.35, 22.56]]


def square(lon, lat, half=0.00005):  # ~10 m building
    return [[lon - half, lat - half], [lon + half, lat - half], [lon + half, lat + half],
            [lon - half, lat + half], [lon - half, lat - half]]


def geojson(path, rings):
    path.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [r]}} for r in rings]}))
    return str(path)


@pytest.fixture
def maps(tmp_path, monkeypatch):
    """A flood map, plus buildings mapped over the area 22.55..22.60 N, 88.34..88.40 E."""
    flood = geojson(tmp_path / "ems_flood_demo.geojson", [FLOOD])
    buildings = geojson(tmp_path / "buildings_demo.geojson", [
        square(88.360, 22.570), square(88.395, 22.598),      # far corner sets the covered area
        square(88.341, 22.551)])
    monkeypatch.setattr(config, "FLOOD_MAP_FILES", [flood])
    monkeypatch.setattr(config, "BUILDING_FILES", [buildings])
    return geodata.reload_geo()


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    sync.dup_index = DuplicateIndex()
    monkeypatch.setattr(verify, "assess_damage", lambda p: DamageResult(
        type="house", severity=0.8, description="Roof collapsed.", real_photo=True))


def send(photo, claim_id="AL-1", **data):
    data = {k: str(v) for k, v in {"claim_id": claim_id, **data}.items() if v is not None}
    r = client.post("/verify", files={"photo": ("p.jpg", photo, "image/jpeg")}, data=data)
    assert r.status_code == 200, r.text
    return r.json()


def has(notes, text):
    return any(text in n for n in notes)


# ---------------------------------------------------------------- flood map

def test_inside_flood_map(maps, photo_factory):
    body = send(photo_factory(seed=1, lat=22.570, lon=88.360, taken_at=T))
    assert has(body["notes"], "Satellite flood map (ems_flood_demo): photo location is inside the flooded area")


def test_just_outside_is_within_tolerance(maps, photo_factory):
    # ~110 m north of the flood edge: GPS error / water receded since the satellite passed
    assert has(send(photo_factory(seed=2, lat=22.581, lon=88.36, taken_at=T))["notes"], "inside the flooded area")


def test_outside_flood_map_gives_distance(maps, photo_factory):
    body = send(photo_factory(seed=3, lat=22.598, lon=88.395, taken_at=T))  # ~3 km away, still covered
    note = next(n for n in body["notes"] if "Satellite flood map" in n)
    assert "km from the mapped flooding" in note
    item = next(i for i in client.get("/dashboard/fraud-flags").json()["items"] if i["type"] == "outside_flood_extent")
    assert 2 < item["distance_km"] < 4 and item["flood_map"] == "ems_flood_demo"


def test_far_from_any_map_says_no_coverage(maps, photo_factory):
    body = send(photo_factory(seed=4, lat=28.61, lon=77.20, taken_at=T))  # Delhi
    assert has(body["notes"], "No satellite flood map covers this location yet")
    flags = client.get("/dashboard/claims.geojson").json()["features"][0]["properties"]["flags"]
    assert "outside_flood_extent" not in flags


def test_phone_gps_only_is_not_checked(maps, photo_factory):
    """A claim filed from a relief camp: no photo GPS, so no satellite verdict."""
    body = send(photo_factory(seed=5), lat=22.598, lon=88.395)
    assert not has(body["notes"], "Satellite flood map") and not has(body["notes"], "Building map")


def test_no_maps_loaded_adds_no_notes(photo_factory):
    body = send(photo_factory(seed=6, lat=22.57, lon=88.36, taken_at=T))
    assert not has(body["notes"], "flood map") and not has(body["notes"], "Building map")


# ---------------------------------------------------------------- building map

def test_building_found_at_house_photo(maps, photo_factory):
    body = send(photo_factory(seed=7, lat=22.57005, lon=88.36005, taken_at=T))
    assert has(body["notes"], "Building map: a building is mapped")


def test_house_claim_with_no_building_is_flagged(maps, photo_factory):
    body = send(photo_factory(seed=8, lat=22.575, lon=88.365, taken_at=T))  # covered area, empty spot
    assert has(body["notes"], "no building mapped within 30 m")
    assert ("no_building_at_location", "AL-1") in [
        (i["type"], i["claim_id"]) for i in client.get("/dashboard/fraud-flags").json()["items"]]


def test_crop_photo_skips_building_check(maps, photo_factory, monkeypatch):
    monkeypatch.setattr(verify, "assess_damage", lambda p: DamageResult(type="crop", severity=0.6, real_photo=True))
    body = send(photo_factory(seed=9, lat=22.575, lon=88.365, taken_at=T))
    assert not has(body["notes"], "Building map")


def test_outside_building_coverage_is_unknown(maps, photo_factory):
    body = send(photo_factory(seed=10, lat=22.70, lon=88.50, taken_at=T))
    assert not has(body["notes"], "Building map")


def test_one_good_photo_clears_claim_flag(maps, photo_factory):
    send(photo_factory(seed=11, lat=22.575, lon=88.365, taken_at=T))          # no building
    send(photo_factory(seed=12, lat=22.57005, lon=88.36005, taken_at=T))      # building, same claim
    flags = client.get("/dashboard/claims.geojson").json()["features"][0]["properties"]
    assert flags["building_found"] is True and "no_building_at_location" not in flags["flags"]


# ---------------------------------------------------------------- file formats and dashboard

def test_shapefile_and_open_buildings_csv(tmp_path, monkeypatch):
    shp = tmp_path / "bhuvan_inundation"
    with shapefile.Writer(str(shp), shapeType=shapefile.POLYGON) as w:
        w.field("name", "C")
        w.poly([FLOOD])
        w.record("flood")
    csv_file = tmp_path / "open_buildings.csv"
    csv_file.write_text("latitude,longitude,area_in_meters,confidence,geometry,full_plus_code\n"
                        '22.57,88.36,95.2,0.81,"POLYGON ((88.35995 22.56995, 88.36005 22.56995, 88.36005 22.57005, '
                        '88.35995 22.57005, 88.35995 22.56995))",7MJCH8C6+2X\n'
                        "22.60,88.40,40.0,0.75,,7MJCJC22+22\n")
    monkeypatch.setattr(config, "FLOOD_MAP_FILES", [str(shp) + ".shp"])
    monkeypatch.setattr(config, "BUILDING_FILES", [str(csv_file)])
    g = geodata.reload_geo()
    assert g.flood_check(22.57, 88.36)["in_flood"] is True
    assert g.building_check(22.57, 88.36)["building_found"] is True
    assert g.building_check(22.585, 88.38)["building_found"] is False


def test_broken_or_missing_files_do_not_crash(tmp_path, monkeypatch):
    bad = tmp_path / "broken.geojson"
    bad.write_text("{not json")
    monkeypatch.setattr(config, "FLOOD_MAP_FILES", [str(bad), str(tmp_path / "missing.geojson")])
    g = geodata.reload_geo()
    assert g.flood_check(22.57, 88.36)["in_flood"] is None


def test_flood_extent_endpoint_and_summary(maps, photo_factory):
    send(photo_factory(seed=13, lat=22.57, lon=88.36, taken_at=T), "AL-1")
    send(photo_factory(seed=14, lat=22.598, lon=88.395, taken_at=T), "AL-2")
    fx = client.get("/dashboard/flood-extent.geojson").json()
    assert fx["maps"] == ["ems_flood_demo"] and fx["features"][0]["geometry"]["type"] == "Polygon"
    sat = client.get("/dashboard/summary").json()["satellite"]
    assert sat == {"flood_maps_loaded": ["ems_flood_demo"], "claims_inside_flood": 1,
                   "claims_outside_flood": 1, "claims_without_map": 0}


# ---------------------------------------------------------------- real-data formats

def test_utm_shapefile_is_converted_to_lat_lon(tmp_path, monkeypatch):
    """Copernicus EMS files can be in metres (UTM 44N); the .prj tells us how to convert."""
    from pyproj import CRS, Transformer

    to_utm = Transformer.from_crs(4326, 32644, always_xy=True)
    ring = [list(to_utm.transform(x, y)) for x, y in [[83.20, 17.70], [83.24, 17.70], [83.24, 17.74], [83.20, 17.74], [83.20, 17.70]]]
    shp = tmp_path / "emsr_utm"
    with shapefile.Writer(str(shp), shapeType=shapefile.POLYGON) as w:
        w.field("interpret", "C")
        w.poly([ring])
        w.record("Flooded Area")
    (tmp_path / "emsr_utm.prj").write_text(CRS.from_epsg(32644).to_wkt("WKT1_ESRI"))
    monkeypatch.setattr(config, "FLOOD_MAP_FILES", [str(shp) + ".shp"])
    g = geodata.reload_geo()
    assert g.flood_check(17.72, 83.22)["in_flood"] is True
    assert g.flood_check(17.80, 83.22)["in_flood"] is False


def test_file_in_metres_without_prj_is_refused(tmp_path, monkeypatch):
    path = geojson(tmp_path / "metres.geojson", [[[721670, 1946404], [743752, 1946404], [743752, 1976525], [721670, 1946404]]])
    monkeypatch.setattr(config, "FLOOD_MAP_FILES", [path])
    assert geodata.reload_geo().floods.tree is None  # skipped with an error, not loaded wrongly


def test_satellite_damage_grade_is_reported_and_clears_flood_flag(tmp_path, monkeypatch, photo_factory):
    """Cyclone wind damage: outside the flood map, but Copernicus graded the building Damaged."""
    flood = geojson(tmp_path / "flood.geojson", [FLOOD])
    pts = tmp_path / "grading.geojson"
    pts.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"damage_gra": "Damaged", "source": "Copernicus EMS EMSR999"},
         "geometry": {"type": "Point", "coordinates": [88.395, 22.598]}},
        {"type": "Feature", "properties": {"damage_gra": "Destroyed", "source": "Copernicus EMS EMSR999"},
         "geometry": {"type": "Point", "coordinates": [88.34, 22.55]}}]}))
    monkeypatch.setattr(config, "FLOOD_MAP_FILES", [flood])
    monkeypatch.setattr(config, "BUILDING_FILES", [str(pts)])
    geodata.reload_geo()
    body = send(photo_factory(seed=20, lat=22.598, lon=88.395, taken_at=T), "AL-WIND")
    assert has(body["notes"], 'graded "Damaged"') and has(body["notes"], "so no flood flag")
    props = client.get("/dashboard/claims.geojson").json()["features"][0]["properties"]
    assert props["satellite_damage_grade"] == "Damaged" and "outside_flood_extent" not in props["flags"]
    assert all(i["type"] != "outside_flood_extent" for i in client.get("/dashboard/fraud-flags").json()["items"])
