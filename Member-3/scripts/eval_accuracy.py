"""Measure damage-vision accuracy against human labels (e.g. from the MEDIC dataset).

Prepare a CSV with two columns, no real victims' data:
    path,label
    photos/img001.jpg,severe
    photos/img002.jpg,mild
    photos/img003.jpg,none

Labels: none | mild | severe (MEDIC's "damage_severity" labels).
Run from Member-3/ (each photo is one paid API call, so start with ~20):
    python scripts/eval_accuracy.py labels.csv --limit 20
"""
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.vision import assess_damage  # noqa: E402


def to_label(damage_type: str, severity: float) -> str:
    if damage_type == "unknown":
        return "unknown"
    if damage_type == "none" or severity < 0.1:
        return "none"
    return "mild" if severity < 0.6 else "severe"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_file")
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    base = Path(args.csv_file).resolve().parent
    rows = list(csv.DictReader(open(args.csv_file, newline="", encoding="utf-8")))[: args.limit]
    confusion: Counter = Counter()
    correct = unknown = 0

    for i, row in enumerate(rows, 1):
        photo = (base / row["path"]).read_bytes()
        result = assess_damage(photo)
        pred, truth = to_label(result.type, result.severity), row["label"].strip().lower()
        confusion[(truth, pred)] += 1
        correct += pred == truth
        unknown += pred == "unknown"
        print(f"[{i}/{len(rows)}] {row['path']}: human={truth} model={pred} ({result.description})")

    assessed = len(rows) - unknown
    print("\n=== Results ===")
    print(f"Photos: {len(rows)} | not assessed: {unknown}")
    if assessed:
        print(f"Agreement with human labels: {correct}/{assessed} = {100 * correct / assessed:.1f}%")
    print("\nConfusion (human -> model): count")
    for (truth, pred), n in sorted(confusion.items()):
        print(f"  {truth:>7} -> {pred:<7} {n}")


if __name__ == "__main__":
    main()
