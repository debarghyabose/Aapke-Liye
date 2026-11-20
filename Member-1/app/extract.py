"""Claim extraction: transcript + current claim -> updated claim.

Live mode asks Gemini for a schema-valid update. Mock mode uses keyword rules
so the rest of the team can integrate without API keys.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from typing import Any

from . import llm
from .config import Settings
from .gaps import clean_phone
from .languages import LANGUAGES, NO_WORDS, YES_WORDS
from .normalize import native_digits_to_ascii
from .schemas import Claim, Loss

DISASTERS = ["flood", "cyclone", "earthquake", "landslide", "fire", "drought", "storm", "other"]
LOSS_TYPES = ["house", "crop", "livestock", "vehicle", "belongings", "shop", "injury", "death", "other"]
HOUSE_KINDS = {"kutcha", "pucca", "semi_pucca"}
DAMAGE_LEVELS = {"partial", "severe", "destroyed"}

# ---------------------------------------------------------------- live (Gemini)

_LOSS_SCHEMA = llm.obj({
    "type": {"type": "string", "enum": LOSS_TYPES},
    "description": llm.nullable("string"),
    "amount_inr": llm.nullable("number"),
    "house_kind": llm.nullable("string", description="kutcha | pucca | semi_pucca"),
    "damage_level": llm.nullable("string", description="partial | severe | destroyed"),
    "crop_name": llm.nullable("string"),
    "area_acres": llm.nullable("number"),
    "animal": llm.nullable("string"),
    "count": llm.nullable("integer"),
    "vehicle_kind": llm.nullable("string"),
})

UPDATE_SCHEMA = llm.obj({
    "claimant_name": llm.nullable("string"),
    "phone": llm.nullable("string"),
    "village": llm.nullable("string"),
    "district": llm.nullable("string"),
    "state": llm.nullable("string"),
    "pincode": llm.nullable("string"),
    "disaster_type": llm.nullable("string", description=" | ".join(DISASTERS)),
    "incident_date": llm.nullable("string", description="YYYY-MM-DD"),
    "losses": {"type": "array", "items": _LOSS_SCHEMA},
    "documents_lost": {"type": "array", "items": {"type": "string"}},
    "confirmation": {"type": "string", "enum": ["yes", "no", "none"]},
    "field_confidence": {
        "type": "array",
        "items": llm.obj({"field": {"type": "string"}, "confidence": {"type": "number"}}),
    },
})

SYSTEM = """You fill in disaster relief claims for people in India from what they say.

You get: the claim so far (JSON), and the newest thing the person said (original transcript,
plus a version with spoken amounts already turned into digits). Return the COMPLETE updated claim.

Rules:
- Only use facts the person actually said, in this utterance or earlier ones (already in the claim).
  Never guess. If something was not said, return null for it.
- Keep every value from the claim so far unless the person corrects it now.
- Write names and places in Latin script (e.g. "Ramesh Kumar", "Puri", "Odisha"), spelled the usual way.
- Amounts are in rupees. "do lakh" = 200000, "dedh lakh" = 150000, "pachas hazaar" = 50000.
- Convert relative dates ("kal", "yesterday", "last Tuesday") to YYYY-MM-DD using today's date.
- losses: one entry per thing lost. Include earlier losses too. Map: ghar/makaan -> house,
  fasal/kheti -> crop, gaay/bhains/bakri -> livestock, bike/gaadi/tractor -> vehicle,
  dukaan -> shop, saman -> belongings.
  house_kind: kutcha (mud, thatch), pucca (brick, cement), semi_pucca.
  damage_level: partial, severe, or destroyed (fully collapsed / washed away).
- documents_lost: short ids such as aadhaar, ration_card, land_record, bank_passbook, voter_id.
- confirmation: "yes" if the person is agreeing that the read-back summary is correct,
  "no" if they say it is wrong or want a change, otherwise "none".
- field_confidence: for each field you set or changed in this turn, how sure you are (0 to 1),
  using paths like "claimant.name", "location.district", "losses[0].amount_inr".
"""


def _claim_view(claim: Claim) -> dict[str, Any]:
    return claim.model_dump(exclude={"transcripts", "field_confidence", "schema_version", "session_id"})


def extract_live(claim: Claim, original: str, normalized: str, amounts: list[int],
                 english: str | None, settings: Settings) -> dict[str, Any]:
    payload = {
        "today": date.today().isoformat(),
        "language": LANGUAGES.get(claim.language, claim.language),
        "claim_so_far": _claim_view(claim),
        "awaiting_confirmation": claim.status == "needs_confirmation",
        "utterance": {
            "original": original,
            "with_numbers": normalized,
            "amounts_detected": amounts,
            **({"english_translation": english} if english else {}),
        },
    }
    return llm.structured(
        settings,
        system=SYSTEM,
        content=json.dumps(payload, ensure_ascii=False),
        schema=UPDATE_SCHEMA,
    )


# ---------------------------------------------------------------- mock (rules)

KW_DISASTER: dict[str, list[str]] = {
    "flood": ["flood", "baadh", "badh", "बाढ़", "बाढ", "বন্যা", "पूर$", "पुरात", "पुरामुळे", "వరద", "வெள்ள"],
    "cyclone": ["cyclone", "toofan", "tufan", "chakravat", "चक्रवात", "तूफान", "तूफ़ान", "ঘূর্ণিঝড়",
                "चक्रीवादळ", "తుఫాన", "புயல"],
    "earthquake": ["earthquake", "bhukamp", "भूकंप", "ভূমিকম্প", "భూకంప", "நிலநடுக்க"],
    "landslide": ["landslide", "bhuskhalan", "भूस्खलन", "ভূমিধস", "కొండచరియ", "நிலச்சரிவு"],
    "fire": ["fire", "aag", "आग$", "आगीत", "আগুন", "అగ్ని", "தீ$", "தீயில்"],
    "drought": ["drought", "sookha", "sukha", "सूखा", "খরা", "दुष्काळ", "కరువు", "வறட்சி"],
}
KW_LOSS: dict[str, list[str]] = {
    "house": ["house", "home", "ghar", "makaan", "मकान", "घर", "বাড়ি", "বাড়ি", "ఇల్లు", "ఇంటి", "வீடு", "வீட்"],
    "crop": ["crop", "fasal", "kheti", "फसल", "खेती", "পীক", "पीक", "ফসল", "పంట", "பயிர்", "நெல்"],
    "livestock": ["cow", "buffalo", "goat", "cattle", "gaay", "gai", "bhains", "bakri", "गाय", "भैंस",
                  "बकरी", "पशु", "गाई", "म्हैस", "जनावर", "গরু", "ছাগল", "ఆవు", "గేదె", "పశువు", "மாடு", "ஆடு", "கால்நடை"],
    "vehicle": ["vehicle", "bike", "scooter", "tractor", "car", "gaadi", "गाड़ी", "ट्रैक्टर", "বাইক",
                "auto", "ఆటో", "బైక్", "వాహన", "வாகன", "ஆட்டோ", "டிராக்டர்"],
    "shop": ["shop", "dukaan", "dukan", "दुकान", "দোকান", "దుకాణ", "கடை"],
    "belongings": ["belongings", "saman", "samaan", "सामान", "জিনিস", "సామాన్", "பொருட்"],
}
KW_HOUSE_KIND = {
    "kutcha": ["kutcha", "kachcha", "kacha", "कच्चा", "कच्चे", "কাঁচা", "కచ్చా", "మట్టి", "குடிசை", "mud", "thatch"],
    "pucca": ["pucca", "pakka", "pucka", "पक्का", "पक्के", "পাকা", "పక్కా", "கான்கிரீட்", "brick", "cement"],
}
KW_DAMAGE = {
    "destroyed": ["destroyed", "collapsed", "washed away", "poora toot", "pura toot", "puri tarah",
                  "पूरा टूट", "पूरी तरह", "बह गया", "পুরোপুরি", "पूर्णपणे", "పూర్తిగా", "முழுமையாக"],
    "partial": ["partial", "partly", "thoda", "aadha", "थोड़ा", "आंशिक", "आधा", "আংশিক", "अंशतः", "కొంత", "பகுதி"],
    "severe": ["badly", "severe", "bahut", "बहुत", "भारी", "খুব", "జాస్తి", "மோசமாக"],
}
KW_DOCS = {
    "aadhaar": ["aadhaar", "aadhar", "आधार", "আধার", "ఆధార్", "ஆதார்"],
    "ration_card": ["ration", "राशन", "रेशन", "রেশন", "రేషన్", "ரேஷன்"],
    "land_record": ["land record", "patta", "khatauni", "7/12", "पट्टा", "खतौनी", "দলিল", "పట్టా", "பட்டா"],
}
STATES = ["Andhra Pradesh", "Assam", "Bihar", "Gujarat", "Karnataka", "Kerala", "Maharashtra", "Odisha",
          "Tamil Nadu", "Telangana", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Himachal Pradesh",
          "Jharkhand", "Madhya Pradesh", "Rajasthan", "Punjab", "Haryana", "Chhattisgarh", "Goa", "Tripura"]
STATE_ALIASES = {"orissa": "Odisha", "ओडिशा": "Odisha", "बिहार": "Bihar", "महाराष्ट्र": "Maharashtra",
                 "পশ্চিমবঙ্গ": "West Bengal", "bengal": "West Bengal", "తెలంగాణ": "Telangana",
                 "ఆంధ్ర": "Andhra Pradesh", "தமிழ்நாடு": "Tamil Nadu", "असम": "Assam", "उत्तराखंड": "Uttarakhand"}

NAME_PATTERNS = [
    r"my name is ([A-Za-z][A-Za-z .]{1,40}?)(?:[,.]| and | from |$)",
    r"i am ([A-Z][a-z]+(?: [A-Z][a-z]+)?)",
    r"mera naam ([A-Za-z][A-Za-z ]{1,40}?) hai",
    r"मेरा नाम ([ऀ-ॿ ]{2,40}?) (?:है|हे)",
    r"माझे नाव ([ऀ-ॿ ]{2,40}?) (?:आहे)",
    r"আমার নাম ([ঀ-৿ ]{2,40}?)(?:।|,| এবং|$)",
    r"నా పేరు ([ఀ-౿ ]{2,40}?)(?:\.|,|$| )",
    r"என் பெயர் ([஀-௿ ]{2,40}?)(?:\.|,|$| )",
]
DISTRICT_PATTERNS = [
    r"([A-Za-z]+) district", r"district ([A-Za-z]+)", r"([A-Za-z]+) (?:zila|jila|jilla)",
    r"([ऀ-ॿ]+) (?:ज़िला|जिला|जिल्हा|ज़िले|जिले)", r"([ঀ-৿]+) জেলা",
    r"([ఀ-౿]+) జిల్లా", r"([஀-௿]+) மாவட்ட",
]
VILLAGE_PATTERNS = [
    r"village ([A-Za-z]+)", r"([A-Za-z]+) village", r"([A-Za-z]+) (?:gaon|gaanv|gram)",
    r"([ऀ-ॿ]+) (?:गाँव|गांव|गाव)", r"([ঀ-৿]+) গ্রাম", r"([ఀ-౿]+) గ్రామ",
    r"([஀-௿]+) கிராம",
]


_TOKEN = re.compile(r"[\wऀ-෿]+")


def _has(text: str, words: list[str]) -> bool:
    """Keyword match. Phrases: substring. ASCII: whole word ("car" must not hit "card").
    Indic: token prefix, so suffixes match ("ఇంటి" in "ఇంటికి"); a trailing "$" means exact token
    ("पूर$" must not hit "पूरी")."""
    tokens = _TOKEN.findall(text)
    for w in words:
        w = w.strip()
        if " " in w:
            if w in text:
                return True
        elif w.endswith("$"):
            if w[:-1] in tokens:
                return True
        elif w.isascii():
            if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", text):
                return True
        elif any(t.startswith(w) for t in tokens):
            return True
    return False


def _first(patterns: list[str], text: str) -> str | None:
    for p in patterns:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip().title() if m.group(1).isascii() else m.group(1).strip()
    return None


def _yes_no(text: str, lang: str) -> str:
    words = set(re.findall(r"[\wऀ-෿]+", text.lower()))
    no = set(NO_WORDS.get(lang, [])) | set(NO_WORDS["en"])
    yes = set(YES_WORDS.get(lang, [])) | set(YES_WORDS["en"])
    if words & no:
        return "no"
    if words & yes:
        return "yes"
    return "none"


def extract_mock(claim: Claim, original: str, normalized: str, amounts: list[int]) -> dict[str, Any]:
    t = normalized
    tl = t.lower()
    out: dict[str, Any] = {k: None for k in ["claimant_name", "phone", "village", "district", "state",
                                             "pincode", "disaster_type", "incident_date"]}
    conf: list[dict[str, Any]] = []

    out["claimant_name"] = _first(NAME_PATTERNS, original) or _first(NAME_PATTERNS, t)
    m = re.search(r"(?:\+?91[\s-]?)?([6-9]\d{4}[\s-]?\d{5})", t)
    if m:
        out["phone"] = clean_phone(m.group(0))
    # pincode: a 6-digit number the person actually said as digits, that isn't an amount
    m = re.search(r"(?<![\d,])([1-9]\d{5})(?![\d,])", native_digits_to_ascii(original))
    if m and int(m.group(1)) not in amounts and not (out["phone"] and m.group(1) in out["phone"]):
        out["pincode"] = m.group(1)
    out["district"] = _first(DISTRICT_PATTERNS, t)
    out["village"] = _first(VILLAGE_PATTERNS, t)
    for s in STATES:
        if s.lower() in tl:
            out["state"] = s
    for alias, s in STATE_ALIASES.items():
        if alias in tl:
            out["state"] = s
    for d, words in KW_DISASTER.items():
        if _has(tl, words):
            out["disaster_type"] = d
            break

    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", t)
    if m:
        try:
            out["incident_date"] = date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            pass
    elif _has(tl, ["yesterday", "kal", "कल$", "গতকাল", "काल$", "నిన్న", "நேற்று"]):
        out["incident_date"] = (date.today() - timedelta(days=1)).isoformat()
    elif _has(tl, ["today", "aaj", "आज$", "আজ$", "ఈరోజు", "இன்று"]):
        out["incident_date"] = date.today().isoformat()

    # losses: start from existing, add new types mentioned now
    losses = [l.model_dump() for l in claim.losses]
    mentioned = [lt for lt, words in KW_LOSS.items() if _has(tl, words)]
    for lt in mentioned:
        if not any(l["type"] == lt for l in losses):
            losses.append(Loss(type=lt).model_dump())
    # The loss this utterance is about: the one mentioned now, else the first one still missing data
    target = None
    if mentioned:
        target = next(l for l in losses if l["type"] == mentioned[0])
    elif losses:
        target = next((l for l in losses if l.get("amount_inr") is None), losses[-1])

    if target is not None:
        idx = losses.index(target)
        if amounts:
            target["amount_inr"] = float(max(amounts))
            conf.append({"field": f"losses[{idx}].amount_inr", "confidence": 0.7})
        for k, words in KW_HOUSE_KIND.items():
            if _has(tl, words) and target["type"] in ("house", "shop"):
                target["house_kind"] = k
        for k, words in KW_DAMAGE.items():
            if _has(tl, words) and target["type"] in ("house", "shop"):
                target["damage_level"] = k
                break
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:acre|acres|ekad|एकड़|एकर|একর|ఎకరా|ఏకర|ஏக்கர்)", tl)
        if m and target["type"] == "crop":
            target["area_acres"] = float(m.group(1))
        for crop in ["paddy", "rice", "dhan", "wheat", "gehu", "cotton", "kapas", "sugarcane", "ganna",
                     "maize", "makka", "धान", "गेहूं", "कपास", "गन्ना", "ধান", "కపాస్", "వరి", "நெல்"]:
            if crop in tl and target["type"] == "crop":
                target["crop_name"] = crop
        m = re.search(r"(\d+)\s*(cow|cows|buffalo|buffaloes|goat|goats|gaay|bhains|bakri|गाय|भैंस|बकरी|"
                      r"গরু|ছাগল|ఆవు|గేదె|மாடு|ஆடு)", tl)
        if m and target["type"] == "livestock":
            target["count"] = int(m.group(1))
            target["animal"] = m.group(2)
        for v in ["tractor", "bike", "scooter", "car", "auto", "cycle", "ट्रैक्टर", "बाइक"]:
            if v in tl and target["type"] == "vehicle":
                target["vehicle_kind"] = v

    docs = [d for d, words in KW_DOCS.items() if _has(tl, words)]

    for f, v in [("claimant.name", out["claimant_name"]), ("claimant.phone", out["phone"]),
                 ("location.district", out["district"]), ("location.village", out["village"]),
                 ("location.state", out["state"]), ("disaster_type", out["disaster_type"])]:
        if v:
            conf.append({"field": f, "confidence": 0.7})

    out.update(losses=losses, documents_lost=docs, confirmation=_yes_no(original, claim.language),
               field_confidence=conf)
    return out


# ---------------------------------------------------------------- merge


def _pick(old, new, old_conf: float, new_conf: float, force: bool):
    if new in (None, ""):
        return old
    if old in (None, "") or force or new_conf >= old_conf or new_conf >= 0.8:
        return new
    return old


def apply_update(claim: Claim, upd: dict[str, Any], force: bool = False) -> Claim:
    """Merge an extractor update into the claim. `force` = user is correcting the read-back."""
    c = claim.model_copy(deep=True)
    confs = {fc["field"]: float(fc["confidence"]) for fc in upd.get("field_confidence") or []}
    old = c.field_confidence

    def set_(path: str, current, value):
        new_conf = confs.get(path, 0.6)
        chosen = _pick(current, value, old.get(path, 0.0), new_conf, force)
        if chosen is not current and chosen != current:
            old[path] = new_conf
        return chosen

    c.claimant.name = set_("claimant.name", c.claimant.name, upd.get("claimant_name"))
    phone = clean_phone(upd.get("phone")) or (upd.get("phone") if upd.get("phone") else None)
    c.claimant.phone = set_("claimant.phone", c.claimant.phone, phone)
    c.location.village = set_("location.village", c.location.village, upd.get("village"))
    c.location.district = set_("location.district", c.location.district, upd.get("district"))
    c.location.state = set_("location.state", c.location.state, upd.get("state"))
    c.location.pincode = set_("location.pincode", c.location.pincode, upd.get("pincode"))

    dt = upd.get("disaster_type")
    if dt and dt not in DISASTERS:
        dt = "other"
    c.disaster_type = set_("disaster_type", c.disaster_type, dt)

    inc = upd.get("incident_date")
    if inc:
        try:
            date.fromisoformat(inc)
        except ValueError:
            inc = None
    c.incident_date = set_("incident_date", c.incident_date, inc)

    # losses: match by type (+ crop/animal), update fields, append new ones
    for raw in upd.get("losses") or []:
        if raw.get("type") not in LOSS_TYPES:
            continue
        if raw.get("house_kind") not in HOUSE_KINDS:
            raw["house_kind"] = None
        if raw.get("damage_level") not in DAMAGE_LEVELS:
            raw["damage_level"] = None
        idx = next((i for i, l in enumerate(c.losses) if l.type == raw["type"]
                    and (raw.get("crop_name") in (None, l.crop_name) or l.crop_name is None)
                    and (raw.get("animal") in (None, l.animal) or l.animal is None)), None)
        if idx is None:
            c.losses.append(Loss(**{k: v for k, v in raw.items() if k in Loss.model_fields}))
            idx = len(c.losses) - 1
            for k, v in raw.items():
                if v is not None and k != "type":
                    old[f"losses[{idx}].{k}"] = confs.get(f"losses[{idx}].{k}", 0.6)
            continue
        loss = c.losses[idx]
        for k in Loss.model_fields:
            if k == "type":
                continue
            setattr(loss, k, set_(f"losses[{idx}].{k}", getattr(loss, k), raw.get(k)))

    for d in upd.get("documents_lost") or []:
        d = str(d).strip().lower().replace(" ", "_")
        if d and d not in c.documents_lost:
            c.documents_lost.append(d)
    return c


def extract(claim: Claim, original: str, normalized: str, amounts: list[int],
            english: str | None, settings: Settings) -> dict[str, Any]:
    if settings.is_mock:
        return extract_mock(claim, original, normalized, amounts)
    return extract_live(claim, original, normalized, amounts, english, settings)
