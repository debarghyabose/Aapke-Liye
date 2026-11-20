"""Member 5: Statutory Proof Substitution Engine.
Resolves alternative accepted proofs when primary documents are lost in disasters,
including state-specific administrative authorities and land records portals.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROOFS_PATH = Path(__file__).resolve().parent.parent / "rules" / "proof_substitution.json"
STATES_DIR = Path(__file__).resolve().parent.parent / "rules" / "states"


class ProofEngine:
    STATE_MAPPING = {
        "west bengal": "west_bengal.json",
        "wb": "west_bengal.json",
        "odisha": "odisha.json",
        "orissa": "odisha.json",
        "od": "odisha.json",
        "assam": "assam.json",
        "as": "assam.json",
        "maharashtra": "maharashtra.json",
        "mh": "maharashtra.json",
        "tamil nadu": "tamil_nadu.json",
        "tn": "tamil_nadu.json"
    }

    def __init__(self, proofs_file: Path | str | None = None):
        self.proofs_path = Path(proofs_file) if proofs_file else PROOFS_PATH
        self.rules = self.load_proofs()

    def load_proofs(self) -> dict[str, Any]:
        if not self.proofs_path.exists():
            raise FileNotFoundError(f"Proof substitution rules not found at: {self.proofs_path}")
        with open(self.proofs_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_state_rules(self, state_name: str | None) -> dict[str, Any] | None:
        if not state_name:
            return None
        key = state_name.lower().strip()
        filename = self.STATE_MAPPING.get(key)
        if not filename:
            return None
        p = STATES_DIR / filename
        if not p.exists():
            return None
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def suggest_substitutes(self, documents_lost: list[str], state: str | None = None) -> list[dict[str, Any]]:
        """
        Maps a list of lost document codes to statutory alternative proofs.
        If a state is supplied (e.g. 'West Bengal', 'Odisha'), includes official state portals and officers.
        """
        defaults = self.rules.get("_default", [])
        state_rules = self.load_state_rules(state)
        state_subs = state_rules.get("accepted_substitutes", {}) if state_rules else {}

        results = []
        for doc in documents_lost or []:
            doc_key = doc.lower().strip()
            # Start with national SDRF default substitutes
            base_alts = list(self.rules.get(doc_key, defaults))

            # Prepend or blend state-specific pathways if available
            if doc_key in state_subs:
                combined_alts = state_subs[doc_key] + [a for a in base_alts if a not in state_subs[doc_key]]
            else:
                combined_alts = base_alts

            results.append({
                "document": doc,
                "document_normalized": doc_key,
                "alternatives": combined_alts,
                "has_statutory_substitute": doc_key in self.rules or doc_key in state_subs,
                "state_specific_authority": state_rules.get("land_authority") if (state_rules and doc_key == "land_record") else None,
                "state_portal": state_rules.get("land_portal") if (state_rules and doc_key == "land_record") else None
            })
        return results
