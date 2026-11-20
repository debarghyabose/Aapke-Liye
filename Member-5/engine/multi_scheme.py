"""Member 5: Multi-Scheme Entitlement Aggregator.
Evaluates disaster victims' losses across all applicable government relief and reconstruction schemes:
1. State Disaster Response Fund (SDRF)
2. Pradhan Mantri Fasal Bima Yojana (PMFBY)
3. Pradhan Mantri Awaas Yojana - Gramin (PMAY-G Disaster Reconstruction)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .entitlement import EntitlementEngine, inr

SCHEMES_DIR = Path(__file__).resolve().parent.parent / "rules" / "schemes"


class MultiSchemeAggregator:
    def __init__(self):
        self.sdrf_engine = EntitlementEngine()
        self.pmfby_rules = self._load_scheme("pmfby.json")
        self.pmay_rules = self._load_scheme("pmay_g_disaster.json")

    @staticmethod
    def _load_scheme(filename: str) -> dict[str, Any]:
        p = SCHEMES_DIR / filename
        if not p.exists():
            return {}
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def evaluate_all(self, claim: dict[str, Any]) -> dict[str, Any]:
        """
        Takes full claim data:
        {
            "claimant": {"name": "..."},
            "location": {"village": "...", "district": "...", "state": "...", "is_hilly": False},
            "disaster_type": "flood",
            "incident_date": "2026-11-15",
            "losses": [...],
            "is_pmfby_insured": True,
            "crop_insured_name": "paddy"
        }
        """
        losses = claim.get("losses", [])
        qualifying_schemes = []

        # 1. Evaluate SDRF Relief (Universal statutory relief)
        sdrf_res = self.sdrf_engine.calculate(losses)
        if sdrf_res["total"] > 0:
            qualifying_schemes.append({
                "scheme_code": "SDRF",
                "scheme_name": "State Disaster Response Fund (SDRF / NDRF)",
                "statutory_authority": "Ministry of Home Affairs",
                "estimated_entitlement": sdrf_res["total"],
                "formatted_amount": sdrf_res["total_inr_formatted"],
                "breakdown": sdrf_res["lines"],
                "category": "Immediate Emergency Relief"
            })

        # 2. Evaluate PMAY-G Disaster Reconstruction Window
        # Qualified if house is fully destroyed
        has_fully_damaged_house = any(
            loss.get("category") == "house" and "fully_damaged" in loss.get("item", "")
            for loss in losses
        )
        if has_fully_damaged_house and self.pmay_rules:
            is_hilly = claim.get("location", {}).get("is_hilly", False)
            pkg = self.pmay_rules.get("total_package", {})
            amt = pkg.get("hilly_tribal_areas", 166750) if is_hilly else pkg.get("plain_areas", 156750)
            qualifying_schemes.append({
                "scheme_code": "PMAY_G_DISASTER",
                "scheme_name": self.pmay_rules.get("scheme_name"),
                "statutory_authority": self.pmay_rules.get("ministry"),
                "estimated_entitlement": amt,
                "formatted_amount": inr(amt),
                "breakdown": [
                    {"component": "Housing Construction Grant", "amount": 130000 if is_hilly else 120000},
                    {"component": "90 Days MGNREGA Unskilled Labor Allowance", "amount": 24750},
                    {"component": "Swachh Bharat Gramin Toilet Grant", "amount": 12000}
                ],
                "category": "Long-Term Permanent Housing Reconstruction"
            })

        # 3. Evaluate PMFBY Crop Insurance Payout
        crop_losses = [l for l in losses if l.get("category") == "crop"]
        if crop_losses and claim.get("is_pmfby_insured") and self.pmfby_rules:
            crop_name = (claim.get("crop_insured_name") or "paddy").lower()
            sum_insured_ha = self.pmfby_rules.get("sum_insured_per_hectare", {}).get(crop_name, 65000)
            total_crop_insurance = 0
            pmfby_breakdown = []

            for cl in crop_losses:
                area = float(cl.get("quantity") or 1.0)
                damage_pct = float(cl.get("damage_percent") or 100.0) / 100.0
                claim_payout = int(round(area * sum_insured_ha * damage_pct))
                total_crop_insurance += claim_payout
                pmfby_breakdown.append({
                    "crop": crop_name,
                    "area_hectares": area,
                    "sum_insured_per_ha": sum_insured_ha,
                    "assessed_damage_percent": int(damage_pct * 100),
                    "estimated_claim": claim_payout
                })

            if total_crop_insurance > 0:
                qualifying_schemes.append({
                    "scheme_code": "PMFBY",
                    "scheme_name": self.pmfby_rules.get("scheme_name"),
                    "statutory_authority": self.pmfby_rules.get("ministry"),
                    "estimated_entitlement": total_crop_insurance,
                    "formatted_amount": inr(total_crop_insurance),
                    "breakdown": pmfby_breakdown,
                    "category": "Agricultural Risk & Crop Insurance"
                })

        grand_total = sum(s["estimated_entitlement"] for s in qualifying_schemes)

        return {
            "claimant_name": claim.get("claimant", {}).get("name", "Beneficiary"),
            "village": claim.get("location", {}).get("village", ""),
            "qualifying_schemes": qualifying_schemes,
            "total_schemes_count": len(qualifying_schemes),
            "grand_total_estimated_inr": grand_total,
            "grand_total_formatted": inr(grand_total)
        }
