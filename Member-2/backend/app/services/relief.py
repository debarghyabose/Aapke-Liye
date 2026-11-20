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
        for key in ("min_amount", "max_amount", "max_quantity_per_household"):
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


def _unit_word(cat: dict) -> str:
    return cat["unit"].replace("per ", "")


def calculate_relief(losses: list[dict], crop_insured: bool | None = None,
                     is_hilly: bool | None = None) -> dict:
    """
    losses: [{"category": "house", "item": "fully_damaged_plain", "quantity": 1,
              "damage_percent": 100}, ...]
    Returns line items, a total, and every loss that could not be matched to a rule
    (with the reason), so nothing is silently dropped. Same rules as Member 5's engine:
    - a category with min_damage_percent (crops: 33%) needs a damage percent to be priced;
    - max_quantity is a household-wide cap across all lines of that category (2 ha of crops);
    - max_quantity_per_household caps one item across lines (3 large milch animals, one
      clothing grant per family).
    """
    rules = load_sdrf_rules()
    cats = rules["categories"]
    # Apply hilly-area rate swap before pricing
    if is_hilly:
        losses = [
            {**l, "item": "fully_damaged_hilly"}
            if l.get("category") == "house" and l.get("item") == "fully_damaged_plain"
            else l
            for l in (losses or [])
        ]
    lines, unmatched, total = [], [], 0
    cat_used: dict[str, float] = {}
    item_used: dict[str, float] = {}

    def zero(loss, qty, rate, cat, note):
        lines.append({**loss, "quantity": qty, "rate": rate, "unit": cat["unit"],
                      "amount": 0, "note": note})

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
            raw_qty = loss.get("quantity")
            qty = 1.0 if raw_qty is None else float(raw_qty)
            pct = loss.get("damage_percent")
            pct = None if pct is None else float(pct)
        except (TypeError, ValueError):
            unmatched.append({**loss, "reason": "Quantity or damage percent is not a number"})
            continue
        if qty < 0:
            unmatched.append({**loss, "reason": "Quantity cannot be negative"})
            continue

        min_pct = cat.get("min_damage_percent")
        if min_pct is not None and pct is None:
            unmatched.append({**loss, "reason": f"Damage percent needed (relief needs "
                                                f"at least {min_pct:g}% damage)"})
            continue
        if min_pct is not None and pct < min_pct:
            zero(loss, qty, rate, cat, f"Not eligible: damage below {min_pct:g}%")
            continue

        notes = []
        if (cap := cat.get("max_quantity")) is not None:
            left = max(0.0, cap - cat_used.get(cat_name, 0.0))
            if left <= 0:
                zero(loss, 0.0, rate, cat, f"Household limit of {cap:g} {_unit_word(cat)} reached")
                continue
            if qty > left:
                notes.append(f"Capped at {cap:g} {_unit_word(cat)} per household")
                qty = left
            cat_used[cat_name] = cat_used.get(cat_name, 0.0) + qty

        if (cap := cat.get("max_quantity_per_household", {}).get(item)) is not None:
            key = f"{cat_name}.{item}"
            left = max(0.0, cap - item_used.get(key, 0.0))
            if left <= 0:
                zero(loss, 0.0, rate, cat, f"Household limit of {cap:g} already reached")
                continue
            if qty > left:
                notes.append(f"Capped at {cap:g} per household")
                qty = left
            item_used[key] = item_used.get(key, 0.0) + qty

        amount = rate * qty
        if amount > 0:
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

    claimed = [l.get("claimed_amount") for l in losses or [] if l.get("claimed_amount")]
    return {"rules_version": rules["version"], "estimate_only": rules_are_sample(),
            "lines": lines, "unmatched": unmatched, "total": total,
            # What the person said they lost, for comparison. SDRF relief is fixed by MHA
            # norms per item, so it is usually much lower than the real loss.
            "claimed_total": int(round(sum(claimed))) if claimed else None,
            "may_also_qualify": other_schemes(losses, crop_insured)}


@lru_cache
def load_scheme(name: str) -> dict:
    path = RULES_DIR / "schemes" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def other_schemes(losses: list[dict], crop_insured: bool | None = None) -> list[dict]:
    """Schemes the family may also qualify for (Member 5's multi-scheme rules). Not added to
    the SDRF total: each needs its own application and eligibility checks."""
    out = []
    pmay = load_scheme("pmay_g_disaster")
    if pmay and any((l.get("category") == "house" and "fully_damaged" in (l.get("item") or ""))
                    for l in losses or []):
        amount = pmay.get("total_package", {}).get("plain_areas")
        out.append({"scheme_code": "PMAY_G_DISASTER", "scheme_name": pmay.get("scheme_name"),
                    "authority": pmay.get("ministry"), "estimated_amount": amount,
                    "conditions": pmay.get("eligibility_conditions", [])})
    pmfby = load_scheme("pmfby")
    crops = [l for l in losses or [] if l.get("category") == "crop"
             and l.get("damage_percent") not in (None, 0)]
    if pmfby and crop_insured and crops:
        per_ha = pmfby.get("sum_insured_per_hectare", {}).get("paddy", 65000)
        indemnity = float(pmfby.get("default_indemnity_level", 0.8))
        amount = sum(round(float(l.get("quantity") or 0) * per_ha * float(l["damage_percent"]) / 100
                           * indemnity) for l in crops)
        out.append({"scheme_code": "PMFBY", "scheme_name": pmfby.get("scheme_name"),
                    "authority": pmfby.get("ministry"), "estimated_amount": amount,
                    "conditions": [
                        f"Report the loss to the insurer or bank within "
                        f"{pmfby.get('localized_calamity_window_hours', 72)} hours",
                        "Sum insured per hectare is set each year for your district; this uses "
                        "a sample value",
                        f"Assumes {round(indemnity * 100)}% indemnity level"]})
    return out


def suggest_proofs(documents_lost: list[str]) -> list[dict]:
    rules = load_proof_rules()
    return [{"document": d, "alternatives": rules.get(d) if isinstance(rules.get(d), list)
             else rules["_default"]}
            for d in documents_lost or []]
