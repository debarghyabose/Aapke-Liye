"""
Legal Document Drafting & Escalation Framework for Aapke Liye
Generates RTI Applications, Reissue Requests, Grievance Petitions & Insurance Intimations.
"""
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config

log = logging.getLogger(__name__)

TITLES = {
    "aadhaar_reissue": "Request for reprint of lost Aadhaar card",
    "ration_card_reissue": "Application for duplicate ration card",
    "land_record_reissue": "Application for certified copy of land records",
    "insurance_home": "Home insurance claim intimation",
    "insurance_vehicle": "Motor insurance claim intimation",
    "insurance_crop": "Crop loss intimation (PMFBY / crop insurance)",
    "followup_letter": "Follow-up on pending relief claim",
    "grievance": "Grievance petition: delay in disaster relief disbursement",
    "rti_application": "Application under Section 6(1) of the Right to Information Act, 2005",
}

PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def draft_legal_document(doc_type: str, claim: Dict[str, Any], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    template_file = config.TEMPLATES_DIR / f"{doc_type}.en.txt"
    if not template_file.exists():
        template_text = f"TO THE COMPETENT RELIEF OFFICER\nRef: Claim {claim.get('id', '')}\nApplicant: {claim.get('fields', {}).get('name', '')}\nLoss suffered in disaster. Please process relief promptly.\nDate: {date.today().strftime('%d-%m-%Y')}"
    else:
        template_text = template_file.read_text(encoding="utf-8")

    fields = claim.get("fields", {})
    relief = claim.get("relief", {})
    extra_data = extra or {}

    total_relief = relief.get("total", 0)
    losses = fields.get("losses", [])
    losses_text = "\n".join([f"  - {l.get('category')}: {l.get('item', '').replace('_', ' ')} (Qty: {l.get('quantity', 1)})" for l in losses]) or "Property loss"

    replacements = {
        "name": fields.get("name") or "[TO FILL: Name]",
        "phone": fields.get("phone") or "[TO FILL: Phone]",
        "village": fields.get("village") or "[TO FILL: Village]",
        "district": fields.get("district") or "[TO FILL: District]",
        "state": fields.get("state") or "[TO FILL: State]",
        "disaster": (fields.get("disaster_type") or claim.get("disaster_type") or "disaster").title(),
        "incident_date": fields.get("date_of_incident") or "[TO FILL: Date of Incident]",
        "today": date.today().strftime("%d-%m-%Y"),
        "losses_table": losses_text,
        "total_loss": f"₹{total_relief:,.2f}" if total_relief > 0 else "[TO FILL: Estimated Loss]",
        "documents_lost": ", ".join(fields.get("documents_lost", [])) or "Identity and land records",
        "claim_id": claim.get("id") or "[TO FILL: Claim ID]",
        "days_pending": str(extra_data.get("days_pending", 30)),
        "bank_account": "[Registered bank account with Aadhaar link]",
        "ration_card_no": "[PDS NFSA Beneficiary]",
    }
    replacements.update(extra_data)

    def _replace(match):
        key = match.group(1)
        return str(replacements.get(key, f"[TO FILL: {key}]"))

    rendered = PLACEHOLDER.sub(_replace, template_text)

    # Detect remaining placeholders
    missing = [m.group(1) for m in PLACEHOLDER.finditer(rendered)]

    return {
        "doc_type": doc_type,
        "title": TITLES.get(doc_type, doc_type.replace("_", " ").title()),
        "text": rendered,
        "missing_fields": list(set(missing)),
    }


def get_escalation_status(claim: Dict[str, Any]) -> Dict[str, Any]:
    submitted_at_str = claim.get("submitted_at")
    days_pending = 1
    if submitted_at_str:
        try:
            submitted_at = datetime.fromisoformat(submitted_at_str.replace("Z", "+00:00"))
            days_pending = max(1, (datetime.now(timezone.utc) - submitted_at).days)
        except Exception:
            pass

    if days_pending < 30:
        next_step = "followup_letter"
        reason = "Claim is under initial field verification survey."
    elif days_pending < 45:
        next_step = "grievance"
        reason = "Verification delayed beyond standard 30-day citizen charter."
    else:
        next_step = "rti_application"
        reason = "Disbursement overdue. Citizen entitled to seek survey report and sanction order via RTI."

    return {
        "days_pending": days_pending,
        "next_step": next_step,
        "reason": reason,
        "steps_done": claim.get("escalation_steps_done", []),
    }
