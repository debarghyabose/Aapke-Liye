"""Phase 2: draft reissue requests, insurance claims and escalation letters.

Legal wording lives ONLY in the template files (owned by Member 5). Code fills
{{placeholders}} from the claim; the LLM may only write the short factual
{{incident_narrative}} paragraph. Anything we don't know stays [TO FILL: ...].
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path

from . import llm
from .config import Settings
from .languages import DISASTER_NAMES, LOSS_NAMES, name_of
from .questions import _inr
from .schemas import Claim, DraftRequest, DraftResponse, EscalationRequest, EscalationResponse

log = logging.getLogger("aapke_liye.documents")

TEMPLATE_DIR = Path(__file__).parent / "templates"
PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")

TITLES = {
    "aadhaar_reissue": "Request for reprint of lost Aadhaar card",
    "ration_card_reissue": "Application for duplicate ration card",
    "land_record_reissue": "Application for certified copy of land records",
    "insurance_home": "Home insurance claim intimation",
    "insurance_vehicle": "Motor insurance claim intimation",
    "insurance_crop": "Crop loss intimation (PMFBY / crop insurance)",
    "followup_letter": "Follow-up on pending relief claim",
    "grievance": "Grievance: delay in disaster relief",
    "rti_application": "Application under Section 6(1) of the RTI Act, 2005",
}

# Escalation ladder (days since the claim was filed)
LADDER = [("followup_letter", 30), ("grievance", 45), ("rti_application", 60)]


def _losses_table(claim: Claim) -> str:
    rows = []
    for i, l in enumerate(claim.losses, 1):
        detail = ", ".join(str(x) for x in [
            l.description, l.house_kind, l.damage_level, l.crop_name,
            f"{l.area_acres:g} acres" if l.area_acres else None,
            f"{l.count} {l.animal or ''}".strip() if l.count else l.animal,
            l.vehicle_kind,
        ] if x)
        amt = f"Rs. {_inr(l.amount_inr)}" if l.amount_inr else "amount not assessed"
        rows.append(f"  {i}. {name_of(LOSS_NAMES, l.type, 'en').title()}" + (f" ({detail})" if detail else "") +
                    f": {amt}")
    return "\n".join(rows) if rows else "  [TO FILL: losses]"


def _fallback_narrative(c: Claim) -> str:
    d = name_of(DISASTER_NAMES, c.disaster_type, "en") or "a disaster"
    where = ", ".join(p for p in [c.location.village, c.location.district, c.location.state] if p)
    when = f" on {c.incident_date}" if c.incident_date else ""
    kinds = ", ".join(name_of(LOSS_NAMES, l.type, "en") for l in c.losses) or "property"
    return f"Due to the {d} at {where or 'my place of residence'}{when}, I suffered loss of {kinds}."


_NARR_SCHEMA = llm.obj({"narrative": {"type": "string"}})
_NARR_SYSTEM = """Write a 2-3 sentence first-person factual account of the disaster loss for a formal
letter in India, using ONLY the facts in the JSON. No legal claims, no demands, no invented details,
no amounts other than those given. Plain formal English."""


def _narrative(c: Claim, settings: Settings) -> str:
    if settings.is_mock:
        return _fallback_narrative(c)
    facts = c.model_dump(exclude={"transcripts", "field_confidence", "schema_version", "session_id", "status"})
    try:
        out = llm.structured(settings, system=_NARR_SYSTEM, content=json.dumps(facts, ensure_ascii=False),
                             schema=_NARR_SCHEMA, max_tokens=1000)
        return out["narrative"].strip()
    except llm.LLMError as exc:
        log.warning("narrative LLM failed: %s", exc)
        return _fallback_narrative(c)


def _values(c: Claim, extra: dict[str, str], settings: Settings, need_narrative: bool) -> dict[str, str]:
    total = sum(l.amount_inr or 0 for l in c.losses)
    v = {
        "name": c.claimant.name,
        "phone": c.claimant.phone,
        "village": c.location.village,
        "district": c.location.district,
        "state": c.location.state,
        "pincode": c.location.pincode,
        "address": ", ".join(p for p in [c.location.village, c.location.district, c.location.state,
                                         c.location.pincode] if p) or None,
        "disaster": name_of(DISASTER_NAMES, c.disaster_type, "en") or None,
        "incident_date": c.incident_date,
        "today": date.today().strftime("%d-%m-%Y"),
        "losses_table": _losses_table(c),
        "total_loss": f"Rs. {_inr(total)}" if total else None,
        "documents_lost": ", ".join(d.replace("_", " ") for d in c.documents_lost) or None,
        "claim_id": c.session_id,
    }
    if need_narrative:
        v["incident_narrative"] = _narrative(c, settings)
    v.update({k: s for k, s in extra.items() if s})
    return {k: s for k, s in v.items() if s not in (None, "")}


def list_doc_types() -> list[dict[str, str]]:
    return [{"doc_type": k, "title": t} for k, t in TITLES.items()]


def draft(req: DraftRequest, settings: Settings) -> DraftResponse:
    path = TEMPLATE_DIR / f"{req.doc_type}.{req.language}.txt"
    if not path.exists():
        path = TEMPLATE_DIR / f"{req.doc_type}.en.txt"
    tpl = path.read_text(encoding="utf-8")
    needed = set(PLACEHOLDER.findall(tpl))
    vals = _values(req.claim, req.extra, settings, "incident_narrative" in needed)
    missing: list[str] = []

    def fill(m: re.Match) -> str:
        key = m.group(1)
        if key in vals:
            return str(vals[key])
        if key not in missing:
            missing.append(key)
        return f"[TO FILL: {key}]"

    text = PLACEHOLDER.sub(fill, tpl)
    return DraftResponse(doc_type=req.doc_type, title=TITLES[req.doc_type], text=text,
                         missing_fields=missing, template_source=path.name)


def next_escalation(req: EscalationRequest) -> EscalationResponse:
    for step, after_days in LADDER:
        if step in req.steps_done:
            continue
        if req.days_pending >= after_days:
            return EscalationResponse(next_step=step, reason=f"claim pending {req.days_pending} days "
                                                             f"(>= {after_days}); {step} not sent yet")
        return EscalationResponse(next_step=None, reason=f"wait until day {after_days} before {step}")
    return EscalationResponse(next_step=None, reason="all escalation steps already taken")
