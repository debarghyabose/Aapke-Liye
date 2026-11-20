"""
Translate between Member 1's claim AI (POST /v1/claim/turn) and Member 2's claim fields.

Member 1 describes losses the way people talk ("2 cows died", "kutcha house destroyed",
"1 bigha paddy"). Member 2 (and Member 5's SDRF rules) need rule codes
({"category": "livestock", "item": "milch_large", "quantity": 2}). This module is the only
place that mapping lives.

Anything we cannot map to an SDRF rule is still passed on (e.g. category "vehicle"), so the
relief calculation lists it as "not covered" instead of silently dropping it.
"""
from __future__ import annotations

ACRE_TO_HECTARE = 0.404686

# Member 1 dotted field paths -> Member 2 field names
FIELD_MAP = {
    "claimant.name": "name",
    "claimant.phone": "phone",
    "location.village": "village",
    "location.district": "district",
    "location.state": "state",
    "disaster_type": "disaster_type",
    "incident_date": "date_of_incident",
    "losses": "losses",
}

ANIMALS = {
    "milch_large": ["cow", "buffalo", "camel", "yak", "mithun", "gai", "goru", "bhains", "mohish"],
    "milch_small": ["goat", "sheep", "bakri", "chhagol", "bhera", "pig"],
    "draught_large": ["bullock", "ox", "horse", "bull", "bail", "balad"],
    "draught_small": ["calf", "donkey", "mule", "pony", "bachhur"],
    "poultry": ["hen", "chicken", "duck", "poultry", "bird", "murgi", "hans"],
}

PERENNIAL_CROPS = ["mango", "coconut", "banana", "tea", "coffee", "arecanut", "areca", "rubber",
                   "cashew", "orange", "litchi", "lichi", "jackfruit", "papaya", "betel", "orchard"]

# Member 1 damage_level -> damage percent for the SDRF thresholds. "partial" is left unknown
# on purpose: it may be above or below the 33% crop threshold, so an official must assess it.
DAMAGE_PERCENT = {"destroyed": 100, "severe": 75}


def _animal_item(animal: str | None) -> str | None:
    name = (animal or "").lower()
    for item, words in ANIMALS.items():
        if any(w in name for w in words):
            return item
    return None


def _crop_item(crop: str | None) -> str:
    name = (crop or "").lower()
    return "perennial" if any(c in name for c in PERENNIAL_CROPS) else "rainfed"


def map_loss(loss: dict) -> list[dict]:
    """One Member 1 loss -> zero or more Member 2 / SDRF loss lines."""
    kind = loss.get("type")
    level = loss.get("damage_level")
    pct = DAMAGE_PERCENT.get(level) if level else None

    if kind == "house":
        if level == "partial":
            item = "partially_damaged_pucca" if loss.get("house_kind") in ("pucca", "semi_pucca") \
                else "partially_damaged_kutcha"
            return [{"category": "house", "item": item, "quantity": 1}]
        return [{"category": "house", "item": "fully_damaged_plain", "quantity": 1,
                 "damage_percent": pct if pct is not None else 100}]

    if kind == "crop":
        acres = loss.get("area_acres")
        hectares = round(acres * ACRE_TO_HECTARE, 3) if acres else 1
        return [{"category": "crop", "item": _crop_item(loss.get("crop_name")),
                 "quantity": hectares, "damage_percent": pct}]

    if kind == "livestock":
        item = _animal_item(loss.get("animal"))
        qty = loss.get("count") or 1
        if item:
            return [{"category": "livestock", "item": item, "quantity": qty}]
        return [{"category": "livestock", "item": (loss.get("animal") or "unknown")[:60],
                 "quantity": qty}]

    if kind == "belongings":
        return [{"category": "household", "item": "clothing", "quantity": 1},
                {"category": "household", "item": "utensils", "quantity": 1}]

    if kind == "death":
        return [{"category": "ex_gratia", "item": "death", "quantity": loss.get("count") or 1}]

    # injury (needs a disability %), vehicle, shop, other: not an SDRF line we can price.
    return [{"category": kind or "other", "item": (loss.get("description") or kind or "other")[:60],
             "quantity": 1}]


def to_member2_fields(m1_claim: dict) -> dict:
    claimant = m1_claim.get("claimant") or {}
    location = m1_claim.get("location") or {}
    losses = [line for loss in m1_claim.get("losses") or [] for line in map_loss(loss)]
    return {
        "name": claimant.get("name"),
        "phone": claimant.get("phone"),
        "village": location.get("village"),
        "district": location.get("district"),
        "state": location.get("state"),
        "disaster_type": m1_claim.get("disaster_type"),
        "date_of_incident": m1_claim.get("incident_date"),
        "losses": losses or None,
        "documents_lost": m1_claim.get("documents_lost") or None,
    }


def map_missing(paths: list[str]) -> list[str]:
    """Member 1's dotted paths -> Member 2 field names, in order, without repeats.
    Details inside a loss (e.g. losses[0].area_acres) all become "losses"."""
    out: list[str] = []
    for p in paths or []:
        name = "losses" if p.startswith("losses") else FIELD_MAP.get(p)
        if name and name not in out:
            out.append(name)
    return out


def to_member2_answer(turn: dict) -> dict:
    """Member 1 TurnResponse -> the dict Member 2's claims router expects, plus `ai_state`
    (Member 1's own claim object, sent back on the next turn so the AI remembers)."""
    m1_claim = turn.get("claim") or {}
    q = turn.get("next_question") or {}
    question = q.get("text") if q.get("field") not in (None, "confirm") else None
    return {
        "transcript": turn.get("transcript"),
        "fields": to_member2_fields(m1_claim),
        "missing_fields": map_missing(turn.get("missing_fields") or []),
        "follow_up_questions": [question] if question else [],
        "ai_state": m1_claim,
    }


# Member 2 / SDRF category -> Member 1 loss type (only used when the AI state has no losses,
# e.g. losses typed on the Review screen).
CATEGORY_TO_TYPE = {"house": "house", "crop": "crop", "livestock": "livestock",
                    "household": "belongings", "ex_gratia": "death"}


def to_member1_claim(claim_id: str, language: str, fields: dict, ai_state: dict | None) -> dict:
    """The claim in Member 1's format for letter drafting: Member 1's own state from the
    conversation, with the claimant's latest Review-screen edits laid on top."""
    c = dict(ai_state or {})
    c["session_id"] = claim_id
    c["language"] = language
    c["claimant"] = {**(c.get("claimant") or {}),
                     **{k: fields[k] for k in ("name", "phone") if fields.get(k)}}
    c["location"] = {**(c.get("location") or {}),
                     **{k: fields[k] for k in ("village", "district", "state") if fields.get(k)}}
    if fields.get("date_of_incident"):
        c["incident_date"] = fields["date_of_incident"]
    if fields.get("disaster_type"):
        c["disaster_type"] = fields["disaster_type"]
    if fields.get("documents_lost"):
        c["documents_lost"] = fields["documents_lost"]
    if not c.get("losses") and fields.get("losses"):
        c["losses"] = [{"type": CATEGORY_TO_TYPE.get(l.get("category"), "other"),
                        "description": str(l.get("item", "")).replace("_", " "),
                        "count": int(l["quantity"]) if l.get("category") == "livestock" else None}
                       for l in fields["losses"]]
    return c
