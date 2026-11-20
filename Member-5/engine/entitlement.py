"""Member 5: Statutory Entitlement Calculation Engine.
Calculates disaster relief under Ministry of Home Affairs (MHA) SDRF/NDRF guidelines.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "sdrf_rules.json"


def inr(amount: float | int) -> str:
    """Format numbers into Indian numbering format (e.g. 1,43,200)."""
    n = int(round(amount))
    digits, sign = str(abs(n)), "-" if n < 0 else ""
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return sign + ",".join(([head] if head else []) + groups + [tail])


class EntitlementEngine:
    def __init__(self, rules_file: Path | str | None = None):
        self.rules_path = Path(rules_file) if rules_file else RULES_PATH
        self.rules = self.load_rules()

    def load_rules(self) -> dict[str, Any]:
        if not self.rules_path.exists():
            raise FileNotFoundError(f"SDRF rules not found at: {self.rules_path}")
        with open(self.rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.validate_schema(data)
        return data

    @staticmethod
    def validate_schema(data: dict[str, Any]) -> None:
        if not isinstance(data.get("version"), str):
            raise ValueError("Rules must specify a 'version' string")
        categories = data.get("categories")
        if not isinstance(categories, dict) or not categories:
            raise ValueError("'categories' must be a non-empty mapping")
        for cat_name, cat in categories.items():
            if not isinstance(cat, dict) or "unit" not in cat or "items" not in cat:
                raise ValueError(f"Category '{cat_name}' must have 'unit' and 'items'")
            for item_name, rate in cat["items"].items():
                if not isinstance(rate, (int, float)) or rate < 0:
                    raise ValueError(f"Rate for '{cat_name}.{item_name}' must be >= 0")

    def calculate(self, losses: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Evaluate list of loss records:
        [{"category": "house", "item": "fully_damaged_plain", "quantity": 1, "damage_percent": 100}, ...]
        Returns itemized calculation, notes, unmatched entries, and total INR amount.
        """
        categories = self.rules.get("categories", {})
        lines: list[dict[str, Any]] = []
        unmatched: list[dict[str, Any]] = []
        total = 0

        for loss in losses:
            cat_name = loss.get("category")
            item_name = loss.get("item")
            cat = categories.get(cat_name)

            if not cat:
                unmatched.append({**loss, "reason": f"Unknown category '{cat_name}'"})
                continue

            rate = cat["items"].get(item_name)
            if rate is None:
                unmatched.append({**loss, "reason": f"Unknown item '{item_name}' in category '{cat_name}'"})
                continue

            try:
                qty = float(loss.get("quantity") or 1)
                damage_pct = loss.get("damage_percent")
                damage_pct = float(damage_pct) if damage_pct is not None else None
            except (ValueError, TypeError):
                unmatched.append({**loss, "reason": "Invalid quantity or damage percentage"})
                continue

            notes: list[str] = []
            min_pct = cat.get("min_damage_percent")
            if min_pct is not None and damage_pct is not None and damage_pct < min_pct:
                lines.append({
                    **loss,
                    "quantity": qty,
                    "rate": rate,
                    "unit": cat["unit"],
                    "amount": 0,
                    "eligible": False,
                    "note": f"Ineligible: damage {damage_pct}% below statutory threshold of {min_pct}%"
                })
                continue

            max_qty = cat.get("max_quantity")
            if max_qty is not None and qty > max_qty:
                notes.append(f"Quantity capped at {max_qty:g} {cat['unit'].replace('per ', '')}")
                qty = max_qty

            amount = rate * qty

            min_floor = cat.get("min_amount", {}).get(item_name)
            if min_floor is not None and amount < min_floor:
                amount = min_floor
                notes.append(f"Adjusted to statutory minimum floor of ₹{inr(min_floor)}")

            max_ceiling = cat.get("max_amount", {}).get(item_name)
            if max_ceiling is not None and amount > max_ceiling:
                amount = max_ceiling
                notes.append(f"Capped at statutory maximum limit of ₹{inr(max_ceiling)}")

            amount_int = int(round(amount))
            total += amount_int

            lines.append({
                **loss,
                "quantity": qty,
                "rate": rate,
                "unit": cat["unit"],
                "amount": amount_int,
                "eligible": True,
                "note": "; ".join(notes) if notes else None
            })

        return {
            "version": self.rules.get("version"),
            "currency": self.rules.get("currency", "INR"),
            "lines": lines,
            "unmatched": unmatched,
            "total": total,
            "total_inr_formatted": inr(total)
        }
