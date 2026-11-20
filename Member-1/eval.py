"""Score the claim pipeline against tests/golden/cases.json.

    python eval.py              # uses CLAIM_AI_MODE from env (live by default)
    python eval.py --mock       # offline rule-based extractor
    python eval.py --audio      # use tests/samples/<lang>/<id>.wav when present (live only)

Live mode calls Gemini (and local Whisper with --audio), so each run costs a little.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).parent
FIELDS = ["name", "district", "state", "disaster_type", "loss_types", "total_amount"]


def similar(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    a, b = a.lower().strip(), b.lower().strip()
    return a == b or a in b or b in a or SequenceMatcher(None, a, b).ratio() >= 0.75


def score(claim: dict, exp: dict) -> dict[str, bool]:
    losses = claim["losses"]
    total = sum(l.get("amount_inr") or 0 for l in losses)
    return {
        "name": similar(claim["claimant"]["name"], exp["name"]),
        "district": similar(claim["location"]["district"], exp["district"]),
        "state": similar(claim["location"]["state"], exp["state"]),
        "disaster_type": claim["disaster_type"] == exp["disaster_type"],
        "loss_types": sorted({l["type"] for l in losses}) == sorted(exp["loss_types"]),
        "total_amount": bool(total) and abs(total - exp["total_amount"]) <= 0.1 * exp["total_amount"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--audio", action="store_true")
    ap.add_argument("--only", help="comma-separated language codes")
    args = ap.parse_args()
    if args.mock:
        os.environ["CLAIM_AI_MODE"] = "mock"

    sys.path.insert(0, str(ROOT))
    from app.config import get_settings
    from app.pipeline import run_turn
    from app.schemas import TurnRequest

    settings = get_settings()
    cases = json.loads((ROOT / "tests/golden/cases.json").read_text(encoding="utf-8"))
    if args.only:
        keep = set(args.only.split(","))
        cases = [c for c in cases if c["language"] in keep]

    per_lang: dict[str, list[dict[str, bool]]] = defaultdict(list)
    print(f"mode={settings.mode} model={settings.llm_model} cases={len(cases)}\n")
    for case in cases:
        req = dict(session_id=case["id"], language=case["language"])
        wav = ROOT / "tests/samples" / case["language"] / f"{case['id']}.wav"
        if args.audio and wav.exists():
            req["audio_base64"] = base64.b64encode(wav.read_bytes()).decode()
            src = "audio"
        else:
            req["text"] = case["script"]
            src = "text"
        resp = run_turn(TurnRequest(**req), settings)
        s = score(resp.claim.model_dump(), case["expected"])
        per_lang[case["language"]].append(s)
        bad = [f for f, ok in s.items() if not ok]
        q = resp.next_question.field if resp.next_question else "-"
        ms = sum(resp.timings_ms.values())
        print(f"{case['id']:<14} {src:<5} {sum(s.values())}/{len(s)}  next={q:<22} {ms:>5} ms"
              + (f"  wrong: {', '.join(bad)}" if bad else ""))
        if resp.message:
            print(f"{'':<14} note: {resp.message}")

    print("\nField accuracy by language")
    print("lang  " + "  ".join(f"{f[:8]:>8}" for f in FIELDS) + "   overall")
    overall_all = []
    for lang, rows in per_lang.items():
        accs = [sum(r[f] for r in rows) / len(rows) for f in FIELDS]
        overall = sum(accs) / len(accs)
        overall_all.append(overall)
        print(f"{lang:<5} " + "  ".join(f"{a:>8.0%}" for a in accs) + f"   {overall:>6.0%}")
    if overall_all:
        print(f"\nmean overall: {sum(overall_all) / len(overall_all):.0%}  (target: 80% per language)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
