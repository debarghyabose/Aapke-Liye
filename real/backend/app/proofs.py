"""
Statutory Proof Substitution Matrix under Section 12, Disaster Management Act 2005
"""
import json
from typing import Any, Dict, List
from . import config

def load_proof_rules() -> Dict[str, Any]:
    proof_path = config.RULES_DIR / "proof_substitution.json"
    if proof_path.exists():
        return json.loads(proof_path.read_text(encoding="utf-8"))
    return {}

def suggest_proofs(lost_docs: List[str]) -> List[Dict[str, Any]]:
    rules = load_proof_rules()
    defaults = rules.get("_default", [
        "Attestation certificate by Gram Panchayat Pradhan / Ward Member",
        "Geo-tagged, time-stamped damage photos submitted through Aapke Liye",
        "Two neighbor joint attestations confirming residency and loss"
    ])
    
    suggestions = []
    for doc in lost_docs:
        doc_key = doc.lower().replace(" ", "_").strip()
        alternatives = rules.get(doc_key, defaults)
        suggestions.append({
            "document": doc,
            "alternatives": alternatives,
            "suggestions": alternatives,
        })
    return suggestions
