"""
Real Gemini Multilingual AI Service
Speech-to-Text, Claim Entity Extraction, and Dynamic Contextual Questioning
"""
import base64
import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple

from . import config

log = logging.getLogger(__name__)

MANDATORY_FIELDS = ["name", "phone", "village", "district", "state", "disaster_type", "losses"]

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi (हिंदी)",
    "bn": "Bengali (বাংলা)",
    "mr": "Marathi (मराठी)",
    "ta": "Tamil (தமிழ்)",
    "te": "Telugu (తెలుగు)",
}


def _build_prompt(input_text: str, existing_json: str, language: str, lang_name: str) -> str:
    return f"""You are Aapke Liye's Relief AI. A disaster victim in India spoke or typed the following text in their language:
"{input_text}"

Current known fields (if any):
{existing_json}

The preferred response language is "{language}" ({lang_name}).

Carefully analyze the transcript, recognize dialect and colloquial terms for loss (e.g. कच्चा घर, कांचा बाड़ी, कूलीपोयिन्दी, పశువులు, ஆடு மாடு, पिके, शेतजमीन).
Extract or update the claim details in valid JSON with this exact schema:
{{
  "transcript": "Full accurate transcription/translation of what was said or typed",
  "fields": {{
    "name": "Applicant Full Name" or null,
    "phone": "10-digit mobile number" or null,
    "village": "Village / Gram Panchayat / Ward name" or null,
    "district": "District name" or null,
    "state": "Indian state name" or null,
    "disaster_type": "flood" | "cyclone" | "earthquake" | "fire" | "landslide" | "drought" | "hail" or null,
    "date_of_incident": "YYYY-MM-DD" or null,
    "losses": [
      {{
        "category": "house" | "crop" | "livestock" | "household" | "ex_gratia",
        "item": "fully_damaged_plain" | "fully_damaged_hilly" | "partially_damaged_pucca" | "partially_damaged_kutcha" | "hut_damaged" | "cattle_shed" | "rainfed" | "irrigated" | "perennial" | "milch_large" | "milch_small" | "draught_large" | "draught_small" | "poultry" | "clothing" | "utensils" | "death",
        "quantity": 1,
        "damage_percent": 100,
        "claimed_amount": 100000
      }}
    ],
    "documents_lost": ["aadhaar", "ration_card", "land_record", "bank_passbook", "voter_id"],
    "vulnerability": ["widow", "elderly", "disabled", "small_marginal_farmer", "child_headed_household"],
    "bank_account_available": true,
    "is_hilly": false
  }},
  "follow_up_questions": [
    "One or two brief, helpful, compassionate questions in {lang_name} asking specifically for any missing details such as phone number, village, or whether the house was pucca or kutcha"
  ]
}}
"""


def _call_gemini(parts: List[Dict[str, Any]]) -> Optional[str]:
    """Calls Gemini with configured fallback models."""
    for model in config.GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={config.GEMINI_API_KEY}"
        body = {
            "contents": [{"parts": parts}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2},
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                candidates = res.get("candidates", [])
                if candidates:
                    return candidates[0]["content"]["parts"][0]["text"]
        except Exception as e:
            log.warning("Gemini model %s failed: %s, trying next model", model, e)
    return None


async def process_audio_claim(audio_bytes: bytes, mime_type: str, language: str, existing_fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Transcribes audio directly via Gemini multimodal and extracts relief claim fields.
    """
    existing_json = json.dumps(existing_fields or {}, ensure_ascii=False)
    lang_name = LANGUAGE_NAMES.get(language, "English")
    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")

    prompt = f"Listen carefully to this audio recording of a disaster victim in India speaking in {lang_name}.\n" + _build_prompt(
        "(From audio attachment)", existing_json, language, lang_name
    )

    parts = [
        {"text": prompt},
        {"inline_data": {"mime_type": mime_type.split(";")[0], "data": b64_audio}},
    ]

    raw_response = _call_gemini(parts)
    if raw_response:
        try:
            data = json.loads(raw_response)
            return _normalize_result(data, existing_fields, language)
        except Exception as e:
            log.error("Failed to parse Gemini JSON: %s", e)

    return _rule_based_fallback("(Audio recording saved)", existing_fields, language)


async def process_text_claim(text: str, language: str, existing_fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extracts structured relief claim details from typed or dictated text.
    """
    existing_json = json.dumps(existing_fields or {}, ensure_ascii=False)
    lang_name = LANGUAGE_NAMES.get(language, "English")

    prompt = _build_prompt(text, existing_json, language, lang_name)
    parts = [{"text": prompt}]

    raw_response = _call_gemini(parts)
    if raw_response:
        try:
            data = json.loads(raw_response)
            return _normalize_result(data, existing_fields, language)
        except Exception as e:
            log.error("Failed to parse Gemini JSON: %s", e)

    return _rule_based_fallback(text, existing_fields, language)


def _normalize_result(data: Dict[str, Any], existing_fields: Optional[Dict[str, Any]], language: str) -> Dict[str, Any]:
    fields = data.get("fields", {})
    if existing_fields:
        merged = {**existing_fields}
        for k, v in fields.items():
            if v not in (None, "", []):
                merged[k] = v
        fields = merged

    # Calculate missing fields
    missing = []
    for f in MANDATORY_FIELDS:
        val = fields.get(f)
        if val in (None, "", []):
            missing.append(f)

    # Ensure questions exist
    questions = data.get("follow_up_questions", [])
    if not questions and missing:
        questions = [_default_question(missing[0], language)]

    return {
        "transcript": data.get("transcript") or fields.get("transcript") or "",
        "fields": fields,
        "missing_fields": missing,
        "follow_up_questions": questions,
        "ai_state": {"last_turn_data": data},
    }


def _default_question(field: str, language: str) -> str:
    templates = {
        "hi": {
            "phone": "कृपया अपना संपर्क फोन नंबर बताएं।",
            "village": "आप किस गाँव या वार्ड में रहते हैं?",
            "losses": "आपदा में क्या नुकसान हुआ? कृपया अपने घर, फसल या मवेशी का विवरण दें।",
            "name": "कृपया अपना पूरा नाम बताएं।",
        },
        "bn": {
            "phone": "দয়া করে আপনার ফোন নম্বরটি বলুন।",
            "village": "আপনি কোন গ্রামে বা ওয়ার্ডে বাস করেন?",
            "losses": "দুর্যোগে আপনার কী কী ক্ষতি হয়েছে? বাড়ি, ফসল বা গবাদি পশুর বিবরণ দিন।",
            "name": "দয়া করে আপনার পুরো নামটি বলুন।",
        },
        "en": {
            "phone": "Please share your 10-digit mobile phone number.",
            "village": "Which village or ward do you live in?",
            "losses": "Please describe what was damaged — your house, crops, or livestock.",
            "name": "What is your full name?",
        },
    }
    lang_t = templates.get(language, templates["en"])
    return lang_t.get(field, f"Please provide your {field.replace('_', ' ')}.")


def _rule_based_fallback(text: str, existing_fields: Optional[Dict[str, Any]], language: str) -> Dict[str, Any]:
    fields = dict(existing_fields or {})
    import re
    phone_match = re.search(r"\b[6-9]\d{9}\b", text)
    if phone_match:
        fields["phone"] = phone_match.group(0)

    missing = [f for f in MANDATORY_FIELDS if fields.get(f) in (None, "", [])]
    return {
        "transcript": text,
        "fields": fields,
        "missing_fields": missing,
        "follow_up_questions": [_default_question(missing[0], language)] if missing else [],
        "ai_state": {},
    }
