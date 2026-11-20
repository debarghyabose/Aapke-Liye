"""Relief calculation from Member 5's SDRF rules JSON, plus proof substitution."""
import json
from functools import lru_cache

from ..config import RULES_DIR


@lru_cache
def load_sdrf_rules() -> dict:
    return json.loads((RULES_DIR / "sdrf_rules.json").read_text(encoding="utf-8"))


@lru_cache
def load_proof_rules() -> dict:
    return json.loads((RULES_DIR / "proof_substitution.json").read_text(encoding="utf-8"))


def calculate_relief(losses: list[dict]) -> dict:
    """
    losses: [{"category": "house", "item": "fully_damaged_plain", "quantity": 1,
              "damage_percent": 100}, ...]
    Returns line items, a total and anything that could not be matched to a rule.
    """
    cats = load_sdrf_rules()["categories"]
    lines, unmatched, total = [], [], 0

    for loss in losses or []:
        cat_name, item = loss.get("category"), loss.get("item")
        cat = cats.get(cat_name or "")
        rate = cat["items"].get(item) if cat else None
        if rate is None:
            unmatched.append(loss)
            continue

        qty = float(loss.get("quantity") or 1)
        notes = []

        min_pct = cat.get("min_damage_percent")
        pct = loss.get("damage_percent")
        if min_pct is not None and pct is not None and float(pct) < min_pct:
            lines.append({**loss, "rate": rate, "amount": 0,
                          "note": f"Not eligible: damage below {min_pct}%"})
            continue

        if cat.get("max_quantity") and qty > cat["max_quantity"]:
            notes.append(f"Capped at {cat['max_quantity']} {cat['unit'].replace('per ', '')}")
            qty = cat["max_quantity"]

        amount = rate * qty
        if (floor := cat.get("min_amount", {}).get(item)) and amount < floor:
            amount, _ = floor, notes.append(f"Raised to minimum ₹{floor}")
        if (ceiling := cat.get("max_amount", {}).get(item)) and amount > ceiling:
            amount, _ = ceiling, notes.append(f"Capped at ₹{ceiling}")

        amount = int(round(amount))
        total += amount
        lines.append({**loss, "quantity": qty, "rate": rate, "unit": cat["unit"],
                      "amount": amount, "note": "; ".join(notes) or None})

    return {"rules_version": load_sdrf_rules().get("version"), "lines": lines,
            "unmatched": unmatched, "total": total}


def suggest_proofs(documents_lost: list[str]) -> list[dict]:
    rules = load_proof_rules()
    return [{"document": d, "alternatives": rules.get(d, rules["_default"])}
            for d in documents_lost or []]
