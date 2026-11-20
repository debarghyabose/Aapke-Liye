"""Measure damage-vision accuracy against human labels (e.g. CrisisMMD or MEDIC damage severity).

Prepare a CSV with columns path,label (and optionally event); paths are relative to the CSV:
    path,label,event
    photos/img001.jpg,severe,hurricane_harvey
    photos/img002.jpg,mild,srilanka_floods
Labels: none | mild | severe  (CrisisMMD: little_or_no_damage | mild_damage | severe_damage).

Run from Member-3/ (each photo is one AI call; on the free tier start with ~30):
    python scripts/eval_accuracy.py labels.csv [--limit 30] [--out results.csv]
"""
import argparse
import csv
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402
from app.vision import assess_damage  # noqa: E402

LEVELS = ["none", "mild", "severe"]
BUSY = {"vision daily limit reached, retry later", "vision rate limited, retry later",
        "vision service unreachable", "vision service error"}
ALIASES = {"little_or_no_damage": "none", "mild_damage": "mild", "severe_damage": "severe"}


def to_label(damage_type: str, severity: float) -> str:
    """Our 0-1 severity -> the benchmark's three levels (bands match the prompt in app/vision.py)."""
    if damage_type == "unknown":
        return "unknown"
    if damage_type == "none" or severity < 0.1:
        return "none"
    return "mild" if severity < 0.6 else "severe"


def assess_with_retry(photo: bytes, tries: int = 4, wait_s: int = 20):
    """Free-tier AI is often busy: wait and retry, so 'busy' is never scored as a wrong answer."""
    for attempt in range(tries):
        result = assess_damage(photo)
        if not (result.type == "unknown" and result.description in BUSY):
            return result
        if attempt < tries - 1:
            print(f"    AI busy ({result.description}), retrying in {wait_s} s...")
            time.sleep(wait_s)
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_file")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--out", default="", help="write every answer to this CSV")
    ap.add_argument("--pause", type=float, default=4.0, help="seconds between photos (free-tier limits)")
    args = ap.parse_args()

    base = Path(args.csv_file).resolve().parent
    rows = list(csv.DictReader(open(args.csv_file, newline="", encoding="utf-8")))[: args.limit]
    print(f"Provider: {config.VISION_PROVIDER} | photos: {len(rows)}\n")
    results = []
    for i, row in enumerate(rows, 1):
        truth = ALIASES.get(row["label"].strip().lower(), row["label"].strip().lower())
        r = assess_with_retry((base / row["path"]).read_bytes())
        pred = to_label(r.type, r.severity)
        results.append({**row, "truth": truth, "pred": pred, "type": r.type, "severity": r.severity,
                        "real_photo": r.real_photo, "description": r.description})
        mark = "✓" if pred == truth else "✗"
        print(f"[{i:2}/{len(rows)}] {mark} human={truth:6} model={pred:7} sev={r.severity:.2f} "
              f"{row.get('event', '')[:20]:20} {r.description[:70]}")
        time.sleep(args.pause)

    scored = [x for x in results if x["pred"] != "unknown"]
    print("\n=== Results ===")
    print(f"Photos: {len(results)} | assessed: {len(scored)} | not assessed: {len(results) - len(scored)}")
    if scored:
        exact = sum(x["pred"] == x["truth"] for x in scored)
        near = sum(abs(LEVELS.index(x["pred"]) - LEVELS.index(x["truth"])) <= 1 for x in scored)
        damage_hit = sum((x["pred"] != "none") == (x["truth"] != "none") for x in scored)
        print(f"Exact agreement with human labels: {exact}/{len(scored)} = {100 * exact / len(scored):.0f}%")
        print(f"Within one level:                  {near}/{len(scored)} = {100 * near / len(scored):.0f}%")
        print(f"Damage vs no damage correct:       {damage_hit}/{len(scored)} = {100 * damage_hit / len(scored):.0f}%")
        print("\nPer human label (how often the model agreed):")
        for lvl in LEVELS:
            sub = [x for x in scored if x["truth"] == lvl]
            if sub:
                ok = sum(x["pred"] == lvl for x in sub)
                print(f"  {lvl:6}: {ok}/{len(sub)} = {100 * ok / len(sub):.0f}%")
        print("\nConfusion (rows = human, columns = model):")
        conf = Counter((x["truth"], x["pred"]) for x in scored)
        print("          " + "".join(f"{p:>8}" for p in LEVELS))
        for t in LEVELS:
            print(f"  {t:7} " + "".join(f"{conf[(t, p)]:>8}" for p in LEVELS))
        by_event = defaultdict(list)
        for x in scored:
            by_event[x.get("event", "?")].append(x["pred"] == x["truth"])
        print("\nPer disaster: " + ", ".join(f"{e} {sum(v)}/{len(v)}" for e, v in sorted(by_event.items())))
    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(results[0]))
            w.writeheader(); w.writerows(results)
        print(f"\nEvery answer saved to {args.out}")


if __name__ == "__main__":
    main()
