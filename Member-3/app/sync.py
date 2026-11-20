"""POST /sync: receives claims from the offline queue.

Idempotent on client_uuid: if the phone retries the same upload, the first result is
returned again and no second claim is created.
"""
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from app.duplicates import DuplicateIndex
from app.exif_check import gps_in_zone, read_exif, timestamp_valid
from app.schemas import Checks, VerificationResult
from app.scoring import score
from app.vision import assess_damage

router = APIRouter()

# Demo storage. Member 2's database replaces these.
results: dict[str, VerificationResult] = {}
dup_index = DuplicateIndex()


@router.post("/sync", response_model=VerificationResult)
async def sync_claim(
    client_uuid: str = Form(...),
    phone: str = Form(...),
    device_lat: Optional[float] = Form(None),
    device_lon: Optional[float] = Form(None),
    photos: list[UploadFile] = File(...),
) -> VerificationResult:
    if client_uuid in results:
        return results[client_uuid]

    data = [await p.read() for p in photos]
    first = read_exif(data[0])
    # Fall back to the phone's GPS when the photo has no EXIF location.
    lat = first["lat"] if first["lat"] is not None else device_lat
    lon = first["lon"] if first["lon"] is not None else device_lon

    duplicate_of = None
    for photo in data:
        duplicate_of = dup_index.find_photo(photo)
        if duplicate_of:
            break
    duplicate_of = duplicate_of or dup_index.find_claim(phone, lat, lon)

    checks = Checks(
        gps_in_zone=gps_in_zone(lat, lon),
        timestamp_valid=timestamp_valid(first["taken_at"]),
        damage=assess_damage(data[0]),
        duplicate_of=duplicate_of,
    )
    result = score(client_uuid, checks)
    if first["lat"] is None:
        result.flags.append("exif_gps_missing")

    results[client_uuid] = result
    dup_index.add(client_uuid, phone, lat, lon, data)
    return result


@router.get("/claims/{claim_id}/verification", response_model=VerificationResult)
def get_verification(claim_id: str) -> VerificationResult:
    from fastapi import HTTPException

    if claim_id not in results:
        raise HTTPException(404, "claim not found")
    return results[claim_id]
