"""Data for the government dashboard that Member 5 designs.

Spec: Member-5/docs/government_dashboard_spec.md. Member 3 supplies the damage scores,
photo locations, duplicate photos and location problems. Names, villages, rupee amounts
and claim status come from Member 2: join on `claim_id`.

  GET /dashboard/summary          totals for the KPI bar
  GET /dashboard/claims.geojson   one map point per claim (map pins, priority list)
  GET /dashboard/heatmap.geojson  claims grouped into grid cells (heatmap layer)
  GET /dashboard/fraud-flags      review queue: duplicates, GPS mismatches, fake photos

These show exact victim locations, so set DASHBOARD_API_KEY and send it as the
X-Dashboard-Key header. Without the key set (own computer only), they are open.
"""
import hmac
import math
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app import config
from app.geodata import get_geo
from app.store import get_store
from app.verify import GPS_MISMATCH_KM

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def require_key(x_dashboard_key: Optional[str] = Header(None)) -> None:
    if not config.DASHBOARD_API_KEY:
        return
    if not x_dashboard_key or not hmac.compare_digest(x_dashboard_key, config.DASHBOARD_API_KEY):
        raise HTTPException(401, "Missing or wrong X-Dashboard-Key")


def severity_band(score_100: int) -> str:
    """Per-claim band, matching the spec's colours (red / orange / yellow)."""
    if score_100 >= 70:
        return "severe"
    if score_100 >= 40:
        return "moderate"
    if score_100 > 0:
        return "minor"
    return "none"


def flags_for(check: dict) -> list[str]:
    flags = []
    if check["duplicate_of"]:
        flags.append("duplicate_photo")
    if check["gps_mismatch_km"] is not None and check["gps_mismatch_km"] > GPS_MISMATCH_KM:
        flags.append("gps_mismatch")
    if check["real_photo"] is False:
        flags.append("not_genuine_photo")
    if check.get("nearby_claims"):
        flags.append("possible_same_house")
    if (check.get("phone_other_claims") or 0) > config.PHONE_MAX_OTHER_CLAIMS_24H:
        flags.append("phone_many_claims")
    # Outside the flood map is not suspicious when satellite grading shows the building damaged
    # (cyclone wind damage, for example).
    if check.get("in_flood") is False and not check.get("satellite_damage_grade"):
        flags.append("outside_flood_extent")
    if check.get("building_found") is False:
        flags.append("no_building_at_location")
    if check.get("ndvi_status") == "little_vegetation_before":
        flags.append("crop_no_vegetation_before")
    elif check.get("ndvi_status") == "no_change":
        flags.append("crop_unchanged_after")
    if check["lat"] is None:
        flags.append("no_location")
    elif not check["gps_ok"]:
        flags.append("outside_disaster_area")
    if not check["timestamp_ok"]:
        missing = "No capture time available" in check["notes"]
        flags.append("no_capture_time" if missing else "time_invalid")
    if check["damage_type"] == "unknown":
        flags.append("damage_not_assessed")
    return flags


def _claims() -> dict[str, dict]:
    """Group photo checks by claim."""
    claims: dict[str, dict] = {}
    for c in get_store().all_checks():
        cid = c["claim_id"] or f"no-claim-{c['id']}"
        cl = claims.setdefault(cid, {
            "claim_id": cid, "lat": None, "lon": None, "gps_source": None, "photos": 0,
            "damage_score": 0, "damage_types": [], "sdrf_categories": [], "flags": [],
            "duplicate_of": [], "first_checked_at": c["checked_at"], "last_checked_at": c["checked_at"],
            "in_flood": None, "building_found": None, "satellite_damage_grade": None,
        })
        if c.get("satellite_damage_grade"):
            cl["satellite_damage_grade"] = c["satellite_damage_grade"]
        if c.get("ndvi_status"):   # Sentinel-2 crop before/after (latest crop photo wins)
            cl["crop_satellite"] = {k: c.get(f"ndvi_{k}") for k in
                                    ("status", "before", "after", "date_before", "date_after", "note")}
        # Satellite / map results: any photo confirming it is enough.
        for k in ("in_flood", "building_found"):
            if c.get(k) is True or (c.get(k) is False and cl[k] is None):
                cl[k] = c[k]
        cl["photos"] += 1
        cl["last_checked_at"] = c["checked_at"]
        if cl["lat"] is None and c["lat"] is not None:
            cl["lat"], cl["lon"], cl["gps_source"] = c["lat"], c["lon"], c["gps_source"]
        cl["damage_score"] = max(cl["damage_score"], round(c["severity"] * 100))
        if c["damage_type"] not in ("none", "unknown") and c["damage_type"] not in cl["damage_types"]:
            cl["damage_types"].append(c["damage_type"])
        if c["sdrf_category"] and c["sdrf_category"] != "not applicable" \
                and c["sdrf_category"] not in cl["sdrf_categories"]:
            cl["sdrf_categories"].append(c["sdrf_category"])
        for f in flags_for(c):
            if f not in cl["flags"]:
                cl["flags"].append(f)
        if c["duplicate_of"] and c["duplicate_of"] not in cl["duplicate_of"]:
            cl["duplicate_of"].append(c["duplicate_of"])
    for cl in claims.values():
        cl["severity_band"] = severity_band(cl["damage_score"])
        # A claim missing a location on one photo but located by another is fine.
        if cl["lat"] is not None and "no_location" in cl["flags"]:
            cl["flags"].remove("no_location")
        # One photo inside the flood (or at a building) clears the claim-level flag.
        for k, flag in (("in_flood", "outside_flood_extent"), ("building_found", "no_building_at_location")):
            if cl[k] is True and flag in cl["flags"]:
                cl["flags"].remove(flag)
    return claims


def _point(lon: float, lat: float, props: dict) -> dict:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": props}


@router.get("/summary", dependencies=[Depends(require_key)])
def summary() -> dict:
    claims = _claims()
    checks = get_store().all_checks()
    bands = defaultdict(int)
    types = defaultdict(int)
    flags = defaultdict(int)
    for cl in claims.values():
        bands[cl["severity_band"]] += 1
        for t in cl["damage_types"]:
            types[t] += 1
        for f in cl["flags"]:
            flags[f] += 1
    return {
        "claims": len(claims),
        "photos": len(checks),
        "claims_without_location": sum(1 for c in claims.values() if c["lat"] is None),
        "claims_flagged": sum(1 for c in claims.values() if c["flags"]),
        "by_severity": {b: bands.get(b, 0) for b in ("severe", "moderate", "minor", "none")},
        "by_damage_type": dict(types),
        "flags": dict(flags),
        "satellite": {
            "flood_maps_loaded": [n for n, _ in get_geo().floods.coverage],
            "claims_inside_flood": sum(1 for c in claims.values() if c["in_flood"] is True),
            "claims_outside_flood": sum(1 for c in claims.values() if c["in_flood"] is False),
            "claims_without_map": sum(1 for c in claims.values() if c["in_flood"] is None),
        },
        "last_checked_at": checks[-1]["checked_at"] if checks else None,
    }


@router.get("/claims.geojson", dependencies=[Depends(require_key)])
def claims_geojson(
    min_score: int = Query(0, ge=0, le=100, description="Only claims with damage_score >= this"),
    flagged_only: bool = Query(False, description="Only claims with at least one flag"),
) -> dict:
    features = []
    for cl in _claims().values():
        if cl["lat"] is None or cl["damage_score"] < min_score or (flagged_only and not cl["flags"]):
            continue
        props = {k: v for k, v in cl.items() if k not in ("lat", "lon")}
        features.append(_point(cl["lon"], cl["lat"], props))
    features.sort(key=lambda f: -f["properties"]["damage_score"])
    return {"type": "FeatureCollection", "features": features}


@router.get("/heatmap.geojson", dependencies=[Depends(require_key)])
def heatmap(cell_km: float = Query(1.0, gt=0.1, le=50, description="Grid cell size in km")) -> dict:
    """Claims grouped into square cells. `weight` (sum of damage scores / 100) suits a
    Leaflet/MapLibre heatmap layer. Cells hide exact household locations."""
    lat_step = cell_km / 111.0
    cells: dict[tuple[int, int], dict] = {}
    for cl in _claims().values():
        if cl["lat"] is None:
            continue
        lon_step = cell_km / (111.0 * max(0.1, math.cos(math.radians(cl["lat"]))))
        key = (math.floor(cl["lat"] / lat_step), math.floor(cl["lon"] / lon_step))
        cell = cells.setdefault(key, {"lat_step": lat_step, "lon_step": lon_step, "scores": [], "severe": 0})
        cell["scores"].append(cl["damage_score"])
        cell["severe"] += cl["severity_band"] == "severe"
    features = []
    for (i, j), cell in cells.items():
        lat = (i + 0.5) * cell["lat_step"]
        lon = (j + 0.5) * cell["lon_step"]
        s = cell["scores"]
        features.append(_point(round(lon, 5), round(lat, 5), {
            "claims": len(s), "severe_claims": cell["severe"],
            "max_damage_score": max(s), "avg_damage_score": round(sum(s) / len(s)),
            "weight": round(sum(s) / 100, 2),
        }))
    return {"type": "FeatureCollection", "cell_km": cell_km, "features": features}


@router.get("/flood-extent.geojson", dependencies=[Depends(require_key)])
def flood_extent() -> dict:
    """The loaded satellite flood polygons (simplified), for the dashboard's flood overlay."""
    return get_geo().flood_geojson()


@router.get("/fraud-flags", dependencies=[Depends(require_key)])
def fraud_flags() -> dict:
    """Review queue for officials. Every item needs a human decision; none is proof of fraud."""
    items = []
    for c in get_store().all_checks():
        base = {"claim_id": c["claim_id"], "photo_check_id": c["id"], "checked_at": c["checked_at"]}
        if c["duplicate_of"]:
            items.append({**base, "type": "duplicate_photo", "other_claim_id": c["duplicate_of"],
                          "hash_distance": c["hash_distance"],
                          "action": "Compare the two photos side by side, then confirm or dismiss"})
        if c["gps_mismatch_km"] is not None and c["gps_mismatch_km"] > GPS_MISMATCH_KM:
            items.append({**base, "type": "gps_mismatch", "distance_km": c["gps_mismatch_km"],
                          "action": "Photo was taken far from where the phone was: field visit before sanction"})
        for n in c.get("nearby_claims") or []:
            items.append({**base, "type": "possible_same_house", "other_claim_id": n["claim_id"],
                          "distance_m": n["distance_m"],
                          "action": "Photos from two claims were taken a few metres apart: check if it is the "
                                    "same house (neighbours and joint families are common)"})
        if (c.get("phone_other_claims") or 0) > config.PHONE_MAX_OTHER_CLAIMS_24H:
            items.append({**base, "type": "phone_many_claims", "other_claims": c["phone_other_claims"],
                          "action": "One phone number filed many claims in 24 h: confirm it is an NGO or "
                                    "volunteer filing for several families"})
        if c.get("in_flood") is False and not c.get("satellite_damage_grade"):
            items.append({**base, "type": "outside_flood_extent", "distance_km": c.get("flood_distance_km"),
                          "flood_map": c.get("flood_map"),
                          "action": "Satellite flood map shows no flooding here: check the damage cause "
                                    "(the map shows water only at the time the satellite passed)"})
        if c.get("ndvi_status") in ("little_vegetation_before", "no_change"):
            items.append({**base, "type": "crop_satellite_mismatch", "ndvi_status": c["ndvi_status"],
                          "ndvi_before": c.get("ndvi_before"), "ndvi_after": c.get("ndvi_after"),
                          "date_before": c.get("ndvi_date_before"), "date_after": c.get("ndvi_date_after"),
                          "action": c.get("ndvi_note") or "Satellite images don't show crop loss here: check on site"})
        if c.get("building_found") is False:
            items.append({**base, "type": "no_building_at_location",
                          "action": "House claim, but no building is mapped at the photo location: field "
                                    "visit (village building maps are often incomplete)"})
        if c["real_photo"] is False:
            items.append({**base, "type": "not_genuine_photo",
                          "action": "Image looks like a screenshot, stock, drawing or AI image: ask for a new photo"})
        if c["lat"] is not None and not c["gps_ok"]:
            items.append({**base, "type": "outside_disaster_area", "lat": c["lat"], "lon": c["lon"],
                          "action": "Location is outside the affected area: check before sanction"})
    order = {"duplicate_photo": 0, "possible_same_house": 1, "phone_many_claims": 2, "gps_mismatch": 3,
             "no_building_at_location": 4, "crop_satellite_mismatch": 5, "outside_flood_extent": 6,
             "not_genuine_photo": 7, "outside_disaster_area": 8}
    items.sort(key=lambda x: (order[x["type"]], x["checked_at"]))
    return {"count": len(items), "items": items}
