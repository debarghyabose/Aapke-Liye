"""Relief calculation from Member 5's SDRF rules JSON, plus proof substitution.
All rupee amounts come from rules/sdrf_rules.json; none are written in Python."""
import json
from functools import lru_cache

from ..config import RULES_DIR


def inr(amount) -> str:
    """Indian digit grouping: 198605 -> '1,98,605', 12000000 -> '1,20,00,000'."""
    n = int(round(amount))
    digits, sign = str(abs(n)), "-" if n < 0 else ""
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return sign + ",".join(([head] if head else []) + groups + [tail])


def validate_rules(rules: dict) -> None:
    """Fail at startup if Member 5's file has the wrong structure."""
    def need(ok, msg):
        if not ok:
            raise ValueError(f"rules/sdrf_rules.json: {msg}")

    def is_amount(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0

    need(isinstance(rules.get("version"), str) and rules["version"], "'version' must be a string")
    cats = rules.get("categories")
    need(isinstance(cats, dict) and cats, "'categories' must be a non-empty object")
    for name, cat in cats.items():
        need(isinstance(cat, dict), f"category '{name}' must be an object")
        need(isinstance(cat.get("unit"), str), f"category '{name}' needs a 'unit' string")
        items = cat.get("items")
        need(isinstance(items, dict) and items, f"category '{name}' needs non-empty 'items'")
        for item, rate in items.items():
            need(is_amount(rate), f"rate for '{name}.{item}' must be a number >= 0")
        for key in ("max_quantity", "min_damage_percent"):
            need(key not in cat or is_amount(cat[key]), f"'{name}.{key}' must be a number")
        for key in ("min_amount", "max_amount"):
            for item, amount in cat.get(key, {}).items():
                need(item in items, f"'{name}.{key}' names unknown item '{item}'")
                need(is_amount(amount), f"'{name}.{key}.{item}' must be a number")


@lru_cache
def load_sdrf_rules() -> dict:
    rules = json.loads((RULES_DIR / "sdrf_rules.json").read_text(encoding="utf-8"))
    validate_rules(rules)
    return rules


@lru_cache
def load_proof_rules() -> dict:
    return json.loads((RULES_DIR / "proof_substitution.json").read_text(encoding="utf-8"))


def rules_are_sample() -> bool:
    return load_sdrf_rules()["version"].lower().startswith("sample")


def calculate_relief(losses: list[dict]) -> dict:
    """
    losses: [{"category": "house", "item": "fully_damaged_plain", "quantity": 1,
              "damage_percent": 100}, ...]
    Returns line items, a total, and every loss that could not be matched to a rule
    (with the reason), so nothing is silently dropped.
    """
    rules = load_sdrf_rules()
    cats = rules["categories"]
    lines, unmatched, total = [], [], 0

    for loss in losses or []:
        cat_name, item = loss.get("category"), loss.get("item")
        cat = cats.get(cat_name or "")
        if cat is None:
            unmatched.append({**loss, "reason": f"Unknown category '{cat_name}'"})
            continue
        rate = cat["items"].get(item)
        if rate is None:
            unmatched.append({**loss, "reason": f"Unknown item '{item}' in '{cat_name}'"})
            continue
        try:
            qty = float(loss.get("quantity") or 1)
            pct = loss.get("damage_percent")
            pct = None if pct is None else float(pct)
        except (TypeError, ValueError):
            unmatched.append({**loss, "reason": "Quantity or damage percent is not a number"})
            continue

        notes = []
        min_pct = cat.get("min_damage_percent")
        if min_pct is not None and pct is not None and pct < min_pct:
            lines.append({**loss, "quantity": qty, "rate": rate, "unit": cat["unit"],
                          "amount": 0, "note": f"Not eligible: damage below {min_pct:g}%"})
            continue

        if cat.get("max_quantity") and qty > cat["max_quantity"]:
            notes.append(f"Capped at {cat['max_quantity']:g} {cat['unit'].replace('per ', '')}")
            qty = cat["max_quantity"]

        amount = rate * qty
        if (floor := cat.get("min_amount", {}).get(item)) and amount < floor:
            amount = floor
            notes.append(f"Raised to minimum ₹{inr(floor)}")
        if (ceiling := cat.get("max_amount", {}).get(item)) and amount > ceiling:
            amount = ceiling
            notes.append(f"Capped at ₹{inr(ceiling)}")

        amount = int(round(amount))
        total += amount
        lines.append({**loss, "quantity": qty, "rate": rate, "unit": cat["unit"],
                      "amount": amount, "note": "; ".join(notes) or None})

    return {"rules_version": rules["version"], "estimate_only": rules_are_sample(),
            "lines": lines, "unmatched": unmatched, "total": total}


def suggest_proofs(documents_lost: list[str]) -> list[dict]:
    rules = load_proof_rules()
    return [{"document": d, "alternatives": rules.get(d, rules["_default"])}
            for d in documents_lost or []]
