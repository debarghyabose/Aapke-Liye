"""Member 5: Command Line Interface (CLI) for Entitlement, Policy & Pitch.
Usage:
  python Member-5/cli.py status
  python Member-5/cli.py calculate
  python Member-5/cli.py multi-scheme
  python Member-5/cli.py proofs --docs aadhaar,land_record --state "West Bengal"
  python Member-5/cli.py rti --name "Ramesh Mondal" --claim-id "CLM-8921"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Fix Windows console encoding crash on emojis
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add Member-5 to sys.path so engine imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.entitlement import EntitlementEngine
from engine.proofs import ProofEngine
from engine.multi_scheme import MultiSchemeAggregator
from engine.templates_validator import TemplateValidator
from engine.connector import SystemConnector


def cmd_status(_args):
    conn = SystemConnector()
    res = conn.check_connection_status()
    print("=" * 65)
    print("🤝 Aapke Liye — Member 5 Cross-System Integration Health")
    print("=" * 65)
    for member, info in res.items():
        name = member.replace("_", " ").title()
        sync_st = info.get("sync_status", "Unknown")
        icon = "✅" if info["connected"] else "⚠️"
        print(f"{icon} {name}: [{sync_st.upper()}]")
        for d in info["details"]:
            print(f"   • {d}")
    print("=" * 65)


def cmd_calculate(_args):
    engine = EntitlementEngine()
    sample_losses = [
        {"category": "house", "item": "fully_damaged_plain", "quantity": 1},
        {"category": "crop", "item": "rainfed", "quantity": 1.2, "damage_percent": 100},
        {"category": "livestock", "item": "milch_small", "quantity": 2},
        {"category": "household", "item": "clothing", "quantity": 1},
        {"category": "household", "item": "utensils", "quantity": 1}
    ]
    res = engine.calculate(sample_losses)
    print("=" * 65)
    print(f"⚖️ SDRF Entitlement Calculation ({res['version']})")
    print("=" * 65)
    for idx, line in enumerate(res["lines"], 1):
        print(f"{idx}. {line['category'].title()} -> {line['item']}: ₹{line['amount']:,} ({line['unit']})")
        if line.get("note"):
            print(f"   [Note: {line['note']}]")
    print("-" * 65)
    print(f"TOTAL RELIEF ENTITLEMENT: ₹{res['total_inr_formatted']}")
    print("=" * 65)


def cmd_multi_scheme(_args):
    agg = MultiSchemeAggregator()
    sample_claim = {
        "claimant": {"name": "Smt. Rina Das"},
        "location": {"village": "Gosaba", "district": "South 24 Parganas", "state": "West Bengal", "is_hilly": False},
        "disaster_type": "cyclone",
        "losses": [
            {"category": "house", "item": "fully_damaged_plain", "quantity": 1},
            {"category": "crop", "item": "rainfed", "quantity": 1.5, "damage_percent": 90},
            {"category": "household", "item": "clothing", "quantity": 1}
        ],
        "is_pmfby_insured": True,
        "crop_insured_name": "paddy"
    }
    res = agg.evaluate_all(sample_claim)
    print("=" * 65)
    print(f"🏛️ Multi-Scheme Disaster Entitlement: {res['claimant_name']} ({res['village']})")
    print("=" * 65)
    for s in res["qualifying_schemes"]:
        print(f"\n📦 [{s['scheme_code']}] {s['scheme_name']}")
        print(f"   Category: {s['category']}")
        print(f"   Sanctioning Authority: {s['statutory_authority']}")
        print(f"   Estimated Amount: ₹{s['formatted_amount']}")
    print("\n" + "=" * 65)
    print(f"🌟 COMBINED MULTI-SCHEME PACKAGE: ₹{res['grand_total_formatted']}")
    print("=" * 65)


def cmd_proofs(args):
    proofs_engine = ProofEngine()
    docs = [d.strip() for d in args.docs.split(",") if d.strip()]
    subs = proofs_engine.suggest_substitutes(docs, state=args.state)
    print("=" * 65)
    print(f"🛡️ Statutory Proof Substitutes (State: {args.state or 'National SDRF'})")
    print("=" * 65)
    for item in subs:
        print(f"\nDocument Lost: {item['document'].upper()}")
        if item.get("state_portal"):
            print(f"Official State Portal: {item['state_portal']}")
        if item.get("state_specific_authority"):
            print(f"Competent State Officer: {item['state_specific_authority']}")
        print("Accepted Statutory Substitutes:")
        for alt in item["alternatives"]:
            print(f"  ✓ {alt}")
    print("=" * 65)


def cmd_rti(args):
    validator = TemplateValidator()
    path = validator.templates_dir / "rti_application.en.txt"
    rendered = validator.render_mock(path, {
        "name": args.name,
        "claim_id": args.claim_id,
        "office_name": args.office,
        "office_address": "Block Development Office, Gosaba, South 24 Parganas",
        "application_date": "2026-11-16",
        "today": "2026-11-20",
        "address": "Village Gosaba, Ward 4, Sundarbans",
        "phone": "+91 9800000000",
        "rti_fee_details": "Exempt under Section 7(5) - BPL Beneficiary"
    })
    print(rendered)


def main():
    parser = argparse.ArgumentParser(description="Member 5 Policy & Entitlement CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Check cross-member system connections")
    p_status.set_defaults(func=cmd_status)

    # calculate
    p_calc = subparsers.add_parser("calculate", help="Run SDRF calculation")
    p_calc.set_defaults(func=cmd_calculate)

    # multi-scheme
    p_multi = subparsers.add_parser("multi-scheme", help="Run multi-scheme entitlement aggregator")
    p_multi.set_defaults(func=cmd_multi_scheme)

    # proofs
    p_proofs = subparsers.add_parser("proofs", help="Resolve accepted proof substitutes")
    p_proofs.add_argument("--docs", default="aadhaar,land_record", help="Comma-separated lost document codes")
    p_proofs.add_argument("--state", default=None, help="State name (e.g. 'West Bengal', 'Odisha')")
    p_proofs.set_defaults(func=cmd_proofs)

    # rti
    p_rti = subparsers.add_parser("rti", help="Generate emergency 48-hour RTI notice")
    p_rti.add_argument("--name", default="Ramesh Mondal", help="Claimant name")
    p_rti.add_argument("--claim-id", default="CLM-2026-WB-8921", help="Claim ID")
    p_rti.add_argument("--office", default="Office of the Block Development Officer (BDO)", help="Public Authority Office")
    p_rti.set_defaults(func=cmd_rti)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
