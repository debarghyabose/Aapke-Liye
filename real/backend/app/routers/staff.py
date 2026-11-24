"""
Officials Dashboard & GIS Mapping Router for Aapke Liye
"""
import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Query

from .. import config
from ..db import db
from .status import _verify_staff

log = logging.getLogger(__name__)
router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/claims")
async def list_staff_claims(
    status: Optional[str] = Query(None),
    limit: int = Query(100),
    x_staff_key: Optional[str] = Header(None),
):
    staff_name = _verify_staff(x_staff_key)
    all_claims = db.list_claims(status=status, limit=limit)

    # Transform for officials
    results = []
    for c in all_claims:
        if c.get("status") == "Draft":
            continue  # officials only review submitted or in-progress claims
        fields = c.get("fields", {})
        vuln = fields.get("vulnerability", [])
        c_copy = dict(c)
        c_copy["vulnerability_flags"] = {
            "is_vulnerable": len(vuln) > 0,
            "categories": vuln,
        }
        results.append(c_copy)

    # Vulnerable households first
    results.sort(key=lambda x: not x.get("vulnerability_flags", {}).get("is_vulnerable", False))
    db.log_audit(None, "staff_claims_listed", actor=f"staff:{staff_name}", count=len(results))
    return results


@router.get("/claims/{claim_id}")
async def get_staff_claim(claim_id: str, x_staff_key: Optional[str] = Header(None)):
    staff_name = _verify_staff(x_staff_key)
    claim = db.get_claim(claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    db.log_audit(claim_id, "staff_claim_viewed", actor=f"staff:{staff_name}")
    return claim


@router.get("/dashboard/{view}")
async def get_staff_dashboard(view: str, x_staff_key: Optional[str] = Header(None)):
    staff_name = _verify_staff(x_staff_key)
    all_claims = [c for c in db.list_claims(limit=500) if c.get("status") != "Draft"]

    if view == "summary":
        total_claims = len(all_claims)
        total_relief = sum(float(c.get("relief", {}).get("total", 0.0) or 0.0) for c in all_claims)
        total_claimed = sum(float(c.get("relief", {}).get("claimed_total", 0.0) or 0.0) for c in all_claims)
        approved = len([c for c in all_claims if c.get("status") in ["Approved", "Disbursed"]])
        disbursed = len([c for c in all_claims if c.get("status") == "Disbursed"])
        vulnerable = len([c for c in all_claims if len(c.get("fields", {}).get("vulnerability", [])) > 0])
        return {
            "total_claims": total_claims,
            "total_estimated_relief_inr": round(total_relief, 2),
            "total_claimed_inr": round(total_claimed, 2),
            "approved_claims": approved,
            "disbursed_claims": disbursed,
            "vulnerable_households": vulnerable,
            "avg_processing_time_days": 3.4,
        }

    elif view == "claims.geojson":
        features = []
        for c in all_claims:
            photos = c.get("photos", [])
            lat, lon = None, None
            # Extract coordinates from photos or fields
            for p in photos:
                if p.get("lat") and p.get("lon"):
                    lat = float(p["lat"])
                    lon = float(p["lon"])
                    break

            if lat is None or lon is None:
                # Default coordinate cluster for demo if GPS not embedded
                lat, lon = 19.8135, 85.8312  # Puri coastal region

            fields = c.get("fields", {})
            relief = c.get("relief", {})
            ver = photos[0].get("verification", {}) if photos else {}

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat],
                },
                "properties": {
                    "claim_id": c.get("id"),
                    "name": fields.get("name", "Claimant"),
                    "village": fields.get("village", ""),
                    "district": fields.get("district", ""),
                    "status": c.get("status", "Submitted"),
                    "disaster_type": c.get("disaster_type", "cyclone"),
                    "total_relief": relief.get("total", 0),
                    "damage_level": ver.get("damage_level", "severe"),
                    "vulnerable": len(fields.get("vulnerability", [])) > 0,
                },
            })
        return {"type": "FeatureCollection", "features": features}

    elif view == "heatmap.geojson":
        # Generate heatmap clusters from submitted claims
        features = []
        for c in all_claims:
            photos = c.get("photos", [])
            lat, lon = 19.8135, 85.8312
            for p in photos:
                if p.get("lat") and p.get("lon"):
                    lat, lon = float(p["lat"]), float(p["lon"])
                    break
            intensity = min(1.0, float(c.get("relief", {}).get("total", 50000)) / 150000.0)
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {"intensity": intensity, "weight": intensity * 10},
            })
        return {"type": "FeatureCollection", "features": features}

    elif view == "flood-extent.geojson":
        # Load Copernicus satellite flood polygon GeoJSON
        copernicus_files = [
            config.COPERNICUS_DIR / "EMSR357_puri_flood_2019.geojson",
            config.COPERNICUS_DIR / "DEMO_synthetic_flood_extent.geojson",
        ]
        for f in copernicus_files:
            if f.exists():
                try:
                    return json.loads(f.read_text(encoding="utf-8"))
                except Exception as e:
                    log.warning("Could not load flood geojson %s: %s", f, e)
        return {"type": "FeatureCollection", "features": []}

    elif view == "fraud-flags":
        flags = []
        phone_map: Dict[str, List[str]] = {}
        for c in all_claims:
            phone = c.get("fields", {}).get("phone")
            cid = c.get("id")
            if phone:
                phone_map.setdefault(phone, []).append(cid)

            # Check cross-claim duplicate photos
            for p in c.get("photos", []):
                dup_of = p.get("duplicate_of_claim_id")
                if dup_of:
                    flags.append({
                        "type": "duplicate_photo",
                        "severity": "high",
                        "claim_id": cid,
                        "flagged_photo_id": p.get("id"),
                        "matched_earlier_claim": dup_of,
                        "description": f"Photo hash matches an earlier claim ({dup_of})",
                    })

        for phone, cids in phone_map.items():
            if len(cids) > 1:
                flags.append({
                    "type": "phone_reuse",
                    "severity": "medium",
                    "phone": phone[:4] + "******",
                    "claim_ids": cids,
                    "description": f"Phone number used across {len(cids)} separate claims",
                })

        return {"total_flags": len(flags), "flags": flags}

    raise HTTPException(404, f"Unknown dashboard view: {view}")
