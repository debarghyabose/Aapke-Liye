"""
SDRF & Central Schemes Entitlement Calculation Engine
Implements Ministry of Home Affairs (MHA) SDRF/NDRF 2022-26 Norms
"""
import json
import logging
from typing import Any, Dict, List, Optional
from . import config

log = logging.getLogger(__name__)

def load_sdrf_rules() -> Dict[str, Any]:
    rules_path = config.RULES_DIR / "sdrf_rules.json"
    if rules_path.exists():
        return json.loads(rules_path.read_text(encoding="utf-8"))
    return {}

def load_labels() -> Dict[str, Any]:
    labels_path = config.RULES_DIR / "labels.json"
    if labels_path.exists():
        return json.loads(labels_path.read_text(encoding="utf-8"))
    return {"categories": {}, "items": {}, "documents": {}}


def calculate_relief(losses: List[Dict[str, Any]], crop_insured: Optional[bool] = False, is_hilly: Optional[bool] = False) -> Dict[str, Any]:
    rules = load_sdrf_rules()
    categories = rules.get("categories", {})
    
    total = 0.0
    claimed_total = 0.0
    lines = []
    unmatched = []

    # Caps counters per category
    milch_large_count = 0
    milch_small_count = 0
    draught_large_count = 0
    draught_small_count = 0
    poultry_total = 0.0
    clothing_given = False
    utensils_given = False
    crop_hectares_total = 0.0

    for loss in losses:
        cat = loss.get("category", "")
        item = loss.get("item", "")
        qty = float(loss.get("quantity", 1.0) or 1.0)
        damage_pct = float(loss.get("damage_percent") or 100.0)
        claimed_amt = float(loss.get("claimed_amount") or 0.0)
        claimed_total += claimed_amt

        cat_rules = categories.get(cat)
        if not cat_rules:
            unmatched.append({
                "category": cat,
                "item": item,
                "quantity": qty,
                "reason": f"Category '{cat}' is not covered under SDRF norms"
            })
            continue

        items_map = cat_rules.get("items", {})

        # 1. House assistance
        if cat == "house":
            if is_hilly and item == "fully_damaged_plain":
                item = "fully_damaged_hilly"
            rate = float(items_map.get(item, 0.0))
            if rate > 0:
                amt = rate * qty
                total += amt
                lines.append({
                    "category": cat,
                    "item": item,
                    "quantity": qty,
                    "rate": rate,
                    "amount": amt,
                    "claimed_amount": claimed_amt if claimed_amt > 0 else None,
                    "note": f"Housing assistance ({item.replace('_', ' ')})"
                })
            else:
                unmatched.append({"category": cat, "item": item, "quantity": qty, "reason": "Unrecognized house damage type"})

        # 2. Crop assistance (requires min 33% damage)
        elif cat == "crop":
            if crop_insured:
                unmatched.append({
                    "category": cat,
                    "item": item,
                    "quantity": qty,
                    "reason": "Crop is covered by PMFBY insurance; SDRF input subsidy is duplicate"
                })
                continue
            if damage_pct < 33:
                unmatched.append({
                    "category": cat,
                    "item": item,
                    "quantity": qty,
                    "reason": f"Damage ({damage_pct}%) is below 33% threshold for SDRF crop assistance"
                })
                continue

            rate = float(items_map.get(item, 8500.0))
            min_amt = float(cat_rules.get("min_amount", {}).get(item, 1000.0))
            eligible_ha = min(qty, max(0.0, 2.0 - crop_hectares_total))
            if eligible_ha > 0:
                amt = max(min_amt, rate * eligible_ha)
                crop_hectares_total += eligible_ha
                total += amt
                lines.append({
                    "category": cat,
                    "item": item,
                    "quantity": eligible_ha,
                    "rate": rate,
                    "amount": amt,
                    "claimed_amount": claimed_amt if claimed_amt > 0 else None,
                    "note": f"Crop input subsidy (capped at 2 ha per farmer)"
                })
            else:
                unmatched.append({"category": cat, "item": item, "quantity": qty, "reason": "Exceeded 2 hectare SDRF farmer ceiling"})

        # 3. Livestock assistance
        elif cat == "livestock":
            rate = float(items_map.get(item, 0.0))
            if item == "milch_large":
                eligible = min(qty, max(0.0, 3.0 - milch_large_count))
                milch_large_count += eligible
            elif item == "milch_small":
                eligible = min(qty, max(0.0, 30.0 - milch_small_count))
                milch_small_count += eligible
            elif item == "draught_large":
                eligible = min(qty, max(0.0, 3.0 - draught_large_count))
                draught_large_count += eligible
            elif item == "draught_small":
                eligible = min(qty, max(0.0, 6.0 - draught_small_count))
                draught_small_count += eligible
            elif item == "poultry":
                eligible = qty
            else:
                eligible = qty

            if eligible > 0 and rate > 0:
                amt = rate * eligible
                if item == "poultry":
                    amt = min(amt, 10000.0 - poultry_total)
                    poultry_total += amt
                total += amt
                lines.append({
                    "category": cat,
                    "item": item,
                    "quantity": eligible,
                    "rate": rate,
                    "amount": amt,
                    "claimed_amount": claimed_amt if claimed_amt > 0 else None,
                    "note": "Animal husbandry replacement assistance"
                })
            else:
                unmatched.append({"category": cat, "item": item, "quantity": qty, "reason": "Exceeded livestock quota ceiling"})

        # 4. Household essentials
        elif cat == "household":
            rate = float(items_map.get(item, 2500.0))
            if item == "clothing" and not clothing_given:
                clothing_given = True
                total += rate
                lines.append({"category": cat, "item": item, "quantity": 1, "rate": rate, "amount": rate, "note": "Emergency clothing grant"})
            elif item == "utensils" and not utensils_given:
                utensils_given = True
                total += rate
                lines.append({"category": cat, "item": item, "quantity": 1, "rate": rate, "amount": rate, "note": "Emergency household utensils grant"})

        # 5. Ex-gratia
        elif cat == "ex_gratia":
            rate = float(items_map.get(item, 400000.0))
            amt = rate * qty
            total += amt
            lines.append({"category": cat, "item": item, "quantity": qty, "rate": rate, "amount": amt, "note": "Statutory disaster ex-gratia assistance"})

    # Additional Central Schemes
    may_also_qualify = []
    has_house_destroyed = any(l.get("item") in ["fully_damaged_plain", "fully_damaged_hilly", "hut_damaged"] for l in losses if l.get("category") == "house")
    if has_house_destroyed:
        may_also_qualify.append({
            "scheme_code": "PMAY_G_DISASTER",
            "name": "Pradhan Mantri Awaas Yojana - Gramin (Disaster Reconstruction)",
            "description": "Permanent pucca house reconstruction grant of ₹1,20,000 for rural disaster victims."
        })
    if crop_insured:
        may_also_qualify.append({
            "scheme_code": "PMFBY",
            "name": "Pradhan Mantri Fasal Bima Yojana",
            "description": "Insurance payout based on notified area yield loss and localized calamity claim."
        })

    return {
        "total": round(total, 2),
        "currency": "INR",
        "lines": lines,
        "unmatched": unmatched,
        "may_also_qualify": may_also_qualify,
        "estimate_only": True,
        "claimed_total": round(claimed_total, 2) if claimed_total > 0 else None,
    }
