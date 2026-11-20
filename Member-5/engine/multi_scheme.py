"""Member 5: Multi-Scheme Entitlement Aggregator.
Evaluates disaster victims' losses across separate statutory and insurance schemes:
1. Relief Owed: State Disaster Response Fund (SDRF / NDRF - universal relief)
2. May Also Qualify For:
   - Pradhan Mantri Awaas Yojana - Gramin (PMAY-G Disaster Reconstruction Window)
   - Pradhan Mantri Fasal Bima Yojana (PMFBY Crop Insurance)
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
        Returns two distinct blocks: 'relief_owed' (SDRF) and 'may_also_qualify' (conditional).
        """
        losses = claim.get("losses", [])

        # ----------------------------------------------------
        # 1. Relief Owed (SDRF / NDRF universal statutory assistance)
        # ----------------------------------------------------
        sdrf_res = self.sdrf_engine.calculate(losses)
        relief_owed = {
            "scheme_code": "SDRF",
            "scheme_name": "State Disaster Response Fund (SDRF / NDRF)",
            "statutory_authority": "Ministry of Home Affairs",
            "category": "Immediate Emergency Relief",
            "estimated_amount": sdrf_res["total"],
            "formatted_amount": sdrf_res["total_inr_formatted"],
            "lines": sdrf_res["lines"],
            "unmatched": sdrf_res["unmatched"],
            "conditions": [
                "Subject to official on-site verification by Revenue Inspector / Tehsildar",
                "Incident must fall within an officially declared disaster area"
            ]
        }

        # ----------------------------------------------------
        # 2. May Also Qualify (Conditional Schemes)
        # ----------------------------------------------------
        may_also_qualify: list[dict[str, Any]] = []

        # PMAY-G Disaster Reconstruction Window
        has_fully_damaged_house = any(
            loss.get("category") == "house" and "fully_damaged" in loss.get("item", "")
            for loss in losses
        )
        if has_fully_damaged_house and self.pmay_rules:
            is_hilly = bool(claim.get("location", {}).get("is_hilly", False))
            grant_amounts = self.pmay_rules.get("grant_amounts", {})
            pkg = self.pmay_rules.get("total_package", {})

            unit_grant = (
                grant_amounts.get("hilly_tribal_iap_grant", 130000)
                if is_hilly
                else grant_amounts.get("plain_areas_unit_grant", 120000)
            )
            mgnrega_grant = grant_amounts.get("mgnrega_labor_amount", 24750)
            toilet_grant = grant_amounts.get("swachh_bharat_toilet_grant", 12000)
            total_pmay = (
                pkg.get("hilly_tribal_areas", unit_grant + mgnrega_grant + toilet_grant)
                if is_hilly
                else pkg.get("plain_areas", unit_grant + mgnrega_grant + toilet_grant)
            )

            may_also_qualify.append({
                "scheme_code": "PMAY_G_DISASTER",
                "scheme_name": self.pmay_rules.get("scheme_name"),
                "statutory_authority": self.pmay_rules.get("ministry"),
                "category": "Long-Term Permanent Housing Reconstruction",
                "estimated_amount": total_pmay,
                "formatted_amount": inr(total_pmay),
                "breakdown": [
                    {"component": "Housing Construction Unit Grant", "amount": unit_grant},
                    {"component": "90 Days MGNREGA Unskilled Labor Allowance", "amount": mgnrega_grant},
                    {"component": "Swachh Bharat Gramin Toilet Grant", "amount": toilet_grant}
                ],
                "conditions": self.pmay_rules.get("eligibility_conditions", [
                    "Family must be registered on the SECC / Awaas+ waitlist",
                    "Family must not own any other pucca house in India",
                    "Dwelling must be located in an eligible rural Gram Panchayat area",
                    "House must be officially verified as fully destroyed"
                ])
            })

        # PMFBY Crop Insurance
        crop_losses = [l for l in losses if l.get("category") == "crop"]
        if crop_losses and claim.get("is_pmfby_insured") and self.pmfby_rules:
            crop_name = (claim.get("crop_insured_name") or "paddy").lower()
            sum_insured_ha = self.pmfby_rules.get("sum_insured_per_hectare", {}).get(crop_name, 65000)
            indemnity = float(self.pmfby_rules.get("default_indemnity_level", 0.80))
            total_crop_insurance = 0
            pmfby_breakdown = []

            for cl in crop_losses:
                raw_pct = cl.get("damage_percent")
                if raw_pct is None:
                    continue
                try:
                    damage_pct = float(raw_pct) / 100.0
                except (ValueError, TypeError):
                    continue

                if damage_pct <= 0:
                    continue

                area = float(cl.get("quantity") or 1.0)
                claim_payout = int(round(area * sum_insured_ha * damage_pct * indemnity))
                total_crop_insurance += claim_payout
                pmfby_breakdown.append({
                    "crop": crop_name,
                    "area_hectares": area,
                    "sum_insured_per_ha_benchmark": sum_insured_ha,
                    "indemnity_level": indemnity,
                    "assessed_damage_percent": int(damage_pct * 100),
                    "estimated_claim": claim_payout
                })

            if total_crop_insurance > 0:
                may_also_qualify.append({
                    "scheme_code": "PMFBY",
                    "scheme_name": self.pmfby_rules.get("scheme_name"),
                    "statutory_authority": self.pmfby_rules.get("ministry"),
                    "category": "Agricultural Risk & Crop Insurance",
                    "estimated_amount": total_crop_insurance,
                    "formatted_amount": inr(total_crop_insurance),
                    "breakdown": pmfby_breakdown,
                    "conditions": [
                        "Cultivated plot must be enrolled under PMFBY for the current cropping season",
                        "Loss intimation must be registered within 72 hours of localized disaster",
                        "Subject to joint loss survey by Agriculture Department & Insurance Surveyor",
                        "Sum insured values are benchmark estimates; district-notified scale of finance applies"
                    ]
                })

        return {
            "claimant_name": claim.get("claimant", {}).get("name", "Beneficiary"),
            "village": claim.get("location", {}).get("village", ""),
            "relief_owed": relief_owed,
            "may_also_qualify": may_also_qualify,
            "may_also_qualify_count": len(may_also_qualify)
        }
