"""POST /verify: the endpoint Member 2's backend calls for each claim photo.

Contract (Member-2/backend/app/services/integrations.py):
  request  multipart: photo=<file>, lat, lon, taken_at (ISO 8601), claim_id  (all but photo optional)
  response {"damage_detected": bool, "damage_score": 0-1, "gps_ok": bool,
            "timestamp_ok": bool, "duplicate": bool, "notes": [str]}

If damage vision is only temporarily unavailable (daily limit, network), we answer 503.
Member 2 then stores the photo as "pending" and can call /verify again later
(POST /claims/{id}/photos/{photo_id}/reverify) instead of saving a wrong "no damage".
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app import config, sync
from app.exif_check import distance_km, gps_in_zone, read_exif, timestamp_valid
from app.geodata import get_geo
from app.ndvi import crop_check
from app.store import get_store
from app.vision import assess_damage

router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))
MAX_PHOTO_BYTES = 15 * 1024 * 1024
# Photo GPS vs phone GPS further apart than this is suspicious.
GPS_MISMATCH_KM = 2.0
# Photo capture time vs time reported by the phone, further apart than this is suspicious.
TIME_MISMATCH = timedelta(hours=24)
# Vision answers that mean "try again later", not "no damage".
RETRYABLE_VISION = {
    "vision daily limit reached, retry later",
    "vision rate limited, retry later",
    "vision service unreachable",
    "vision service error",
}


class VerifyResponse(BaseModel):
    damage_detected: bool
    damage_score: float
    gps_ok: bool
    timestamp_ok: bool
    duplicate: bool
    notes: list[str]


def _parse_float(value: Optional[str], name: str) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        raise HTTPException(422, f"{name} must be a number") from None


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    """ISO 8601 -> naive India time (EXIF times and DISASTER_START are local)."""
    if not value:
        return None
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(422, "taken_at must be an ISO 8601 timestamp") from None
    if t.tzinfo is not None:
        t = t.astimezone(IST).replace(tzinfo=None)
    return t


def run_crop_check(check_id: int, lat: float, lon: float, taken_at: datetime) -> None:
    """Background task: Sentinel-2 before/after check, saved to the store when done."""
    r = crop_check(lat, lon, taken_at)
    get_store().update(check_id, ndvi_status=r["status"], ndvi_before=r["ndvi_before"],
                       ndvi_after=r["ndvi_after"], ndvi_date_before=r["date_before"],
                       ndvi_date_after=r["date_after"], ndvi_note=r.get("note"))


@router.post("/verify", response_model=VerifyResponse)
async def verify(
    background: BackgroundTasks,
    photo: UploadFile = File(...),
    lat: Optional[str] = Form(None),
    lon: Optional[str] = Form(None),
    taken_at: Optional[str] = Form(None),
    claim_id: Optional[str] = Form(None),
    phone: Optional[str] = Form(None, max_length=20,
                                description="Optional. Only a keyed fingerprint is stored, never the number."),
) -> VerifyResponse:
    data = await photo.read()
    if not data:
        raise HTTPException(422, "photo is empty")
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(413, "photo is too large")

    device_lat, device_lon = _parse_float(lat, "lat"), _parse_float(lon, "lon")
    device_time = _parse_time(taken_at)
    exif = read_exif(data)
    notes: list[str] = []

    # --- GPS: trust the photo's own EXIF location first, then the phone's.
    gap: Optional[float] = None
    if exif["lat"] is not None:
        use_lat, use_lon, gps_source = exif["lat"], exif["lon"], "exif"
        if device_lat is not None and device_lon is not None:
            gap = distance_km(use_lat, use_lon, device_lat, device_lon)
            if gap > GPS_MISMATCH_KM:
                notes.append(f"Photo GPS is {gap:.0f} km from the phone's reported location")
    else:
        use_lat, use_lon = device_lat, device_lon
        gps_source = "phone" if device_lat is not None and device_lon is not None else "none"
        if gps_source == "phone":
            notes.append("Photo has no GPS data; used the phone's location")
    in_zone = gps_in_zone(use_lat, use_lon)
    if in_zone is None:
        notes.append("No location available")
    elif not in_zone:
        notes.append("Location is outside the disaster area")

    # --- Time: same order, EXIF first.
    if exif["taken_at"] is not None:
        use_time = exif["taken_at"]
        if device_time is not None and abs(use_time - device_time) > TIME_MISMATCH:
            notes.append("Photo capture time differs from the phone's reported time by over a day")
    else:
        use_time = device_time
        if device_time is not None:
            notes.append("Photo has no capture time; used the phone's time")
    time_ok = timestamp_valid(use_time)
    if time_ok is None:
        notes.append("No capture time available")
    elif not time_ok:
        notes.append("Photo was taken before the disaster or in the future")

    # --- Duplicate: same (or near-identical) photo already used by another claim.
    try:
        fingerprint = sync.dup_index.phash(data)
    except Exception:
        raise HTTPException(422, "photo is not a readable image") from None
    duplicate_of, hash_distance = sync.dup_index.closest_other_claim(fingerprint, claim_id)
    duplicate = duplicate_of is not None
    if duplicate:
        notes.append("Same photo was already submitted with another claim")

    store = get_store()
    # --- Same house: a different photo, but taken within a few metres of another claim's.
    # Only the photo's own GPS counts: the phone's location at upload time would flag every
    # family an NGO worker files for from the same relief camp.
    nearby = []
    if gps_source == "exif":
        nearby = [n for n in store.nearby_other_claims(use_lat, use_lon, claim_id, config.SAME_HOUSE_RADIUS_M)
                  if n["claim_id"] != duplicate_of]
        if nearby:
            n = nearby[0]
            more = f" (and {len(nearby) - 1} more)" if len(nearby) > 1 else ""
            notes.append(f"Photo taken {n['distance_m']:.0f} m from a photo in claim {n['claim_id']}{more}: "
                         "possibly the same house")

    # --- Same person: one phone number behind many claims in 24 hours.
    phone_fp = store.phone_fingerprint(phone)
    phone_others = store.other_claims_for_phone(phone_fp, claim_id)
    if len(phone_others) > config.PHONE_MAX_OTHER_CLAIMS_24H:
        notes.append(f"This phone number was used on {len(phone_others)} other claims in the last 24 hours "
                     "(NGO bulk filing, or possible fraud)")

    # --- Damage vision (slow network call: run off the event loop).
    damage = await run_in_threadpool(assess_damage, data)
    if damage.type == "unknown" and damage.description in RETRYABLE_VISION:
        raise HTTPException(503, f"Damage check temporarily unavailable: {damage.description}",
                            headers={"Retry-After": "60"})
    if damage.real_photo is False:
        notes.append("Image may not be a genuine photo (screenshot, stock, drawing or AI-generated)")
    if damage.type == "unknown":
        notes.append(f"Damage not assessed: {damage.description}")
    elif damage.description:
        notes.append(damage.description)
    if damage.sdrf_category and damage.sdrf_category != "not applicable":
        notes.append(f"Suggested SDRF category: {damage.sdrf_category}")

    # --- Satellite flood map and building map (local files, see app/geodata.py).
    # Only the photo's own GPS: relief camps on dry ground would look "outside the flood".
    geo = get_geo()
    flood = {"in_flood": None, "distance_km": None, "map": None}
    building = {"building_found": None, "distance_m": None}
    if gps_source == "exif":
        flood = geo.flood_check(use_lat, use_lon)
        # Also when the AI could not assess the photo: satellite grading still helps the official.
        if damage.type in ("house", "unknown"):
            building = geo.building_check(use_lat, use_lon)
    if flood["in_flood"] is True:
        notes.append(f"Satellite flood map ({flood['map']}): photo location is inside the flooded area")
    elif flood["in_flood"] is False:
        where = (f"{flood['distance_km']:.1f} km from" if flood["distance_km"] is not None
                 else f"more than {config.FLOOD_COVERAGE_MARGIN_KM:.0f} km from")
        notes.append(f"Satellite flood map ({flood['map']}): photo location is {where} the mapped flooding")
    elif geo.floods.tree is not None and gps_source == "exif":
        notes.append("No satellite flood map covers this location yet")
    if building["building_found"] is True and building.get("damage_grade"):
        notes.append(f"Satellite damage grading ({building['grade_source']}): the building "
                     f"{building['distance_m']:.0f} m from the photo is graded \"{building['damage_grade']}\"")
        if flood["in_flood"] is False:
            notes.append("Outside the flood map, but satellite grading shows building damage "
                         "(for example cyclone wind damage), so no flood flag")
    elif building["building_found"] is True:
        notes.append(f"Building map: a building is mapped {building['distance_m']:.0f} m from the photo location")
    elif building["building_found"] is False:
        notes.append(f"Building map: no building mapped within {config.BUILDING_SEARCH_M:.0f} m of the photo "
                     "location (maps of rural areas can be incomplete)")

    # --- Crop before/after from Sentinel-2 (slow: runs after we reply, result on the dashboard).
    crop_check_due = (config.NDVI_ENABLED and damage.type == "crop" and gps_source == "exif"
                      and use_time is not None)
    if crop_check_due:
        notes.append("Satellite crop check (Sentinel-2, field 2-4 months before vs now) started: "
                     "the result appears on the dashboard in about a minute")

    detected = damage.type not in ("none", "unknown") and damage.severity > 0
    score = round(damage.severity if detected else 0.0, 2)
    sync.dup_index.add_hash(fingerprint, claim_id)
    check_id = store.record(
        ndvi_status="pending" if crop_check_due else None,
        claim_id=claim_id, lat=use_lat, lon=use_lon, gps_source=gps_source,
        phone_hash=phone_fp, nearby_claims=nearby, phone_other_claims=len(phone_others) if phone_fp else None,
        in_flood=None if flood["in_flood"] is None else int(flood["in_flood"]),
        flood_distance_km=flood["distance_km"], flood_map=flood["map"],
        building_found=None if building["building_found"] is None else int(building["building_found"]),
        building_distance_m=building["distance_m"], satellite_damage_grade=building.get("damage_grade"),
        gps_mismatch_km=None if gap is None else round(gap, 2),
        gps_ok=bool(in_zone), timestamp_ok=bool(time_ok),
        damage_type=damage.type, severity=score, sdrf_category=damage.sdrf_category,
        real_photo=None if damage.real_photo is None else int(damage.real_photo),
        duplicate_of=duplicate_of, hash_distance=hash_distance,
        phash=str(fingerprint), notes=notes,
    )
    if crop_check_due:
        background.add_task(run_crop_check, check_id, use_lat, use_lon, use_time)

    return VerifyResponse(
        damage_detected=detected,
        damage_score=score,
        gps_ok=bool(in_zone),
        timestamp_ok=bool(time_ok),
        duplicate=duplicate,
        notes=notes,
    )
