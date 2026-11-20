"""Language codes and the localized words the pipeline needs.

All non-English strings here should be reviewed by a native speaker before
the demo (search for TODO-REVIEW in tests/README).
"""
from __future__ import annotations

LANGUAGES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "mr": "Marathi",
    "te": "Telugu",
    "ta": "Tamil",
}

INDIC = {"hi", "bn", "mr", "te", "ta"}

# Words that mean "yes / correct" and "no / wrong" in each language (lowercase).
YES_WORDS: dict[str, list[str]] = {
    "en": ["yes", "correct", "right", "ok", "okay", "yeah", "yep"],
    "hi": ["हाँ", "हां", "हा", "जी", "सही", "ठीक", "haan", "han", "ha", "sahi", "theek", "thik", "ji"],
    "bn": ["হ্যাঁ", "হ্যা", "ঠিক", "সঠিক", "হাঁ", "ha", "thik"],
    "mr": ["हो", "होय", "बरोबर", "ठीक", "ho", "hoy", "barobar"],
    "te": ["అవును", "సరే", "సరైనది", "avunu", "sare"],
    "ta": ["ஆம்", "சரி", "ஆமாம்", "aam", "sari"],
}
NO_WORDS: dict[str, list[str]] = {
    "en": ["no", "wrong", "incorrect", "not", "change"],
    "hi": ["नहीं", "नही", "गलत", "ग़लत", "nahi", "nahin", "galat"],
    "bn": ["না", "ভুল", "na", "bhul"],
    "mr": ["नाही", "चूक", "nahi", "chuk"],
    "te": ["కాదు", "లేదు", "తప్పు", "kaadu", "ledu", "tappu"],
    "ta": ["இல்லை", "தவறு", "illai", "thavaru"],
}

DISASTER_NAMES: dict[str, dict[str, str]] = {
    "flood": {"en": "flood", "hi": "बाढ़", "bn": "বন্যা", "mr": "पूर", "te": "వరద", "ta": "வெள்ளம்"},
    "cyclone": {"en": "cyclone", "hi": "चक्रवात", "bn": "ঘূর্ণিঝড়", "mr": "चक्रीवादळ", "te": "తుఫాను", "ta": "புயல்"},
    "earthquake": {"en": "earthquake", "hi": "भूकंप", "bn": "ভূমিকম্প", "mr": "भूकंप", "te": "భూకంపం", "ta": "நிலநடுக்கம்"},
    "landslide": {"en": "landslide", "hi": "भूस्खलन", "bn": "ভূমিধস", "mr": "भूस्खलन", "te": "కొండచరియలు", "ta": "நிலச்சரிவு"},
    "fire": {"en": "fire", "hi": "आग", "bn": "আগুন", "mr": "आग", "te": "అగ్ని ప్రమాదం", "ta": "தீ"},
    "drought": {"en": "drought", "hi": "सूखा", "bn": "খরা", "mr": "दुष्काळ", "te": "కరువు", "ta": "வறட்சி"},
    "storm": {"en": "storm", "hi": "आंधी", "bn": "ঝড়", "mr": "वादळ", "te": "గాలివాన", "ta": "சூறாவளி"},
    "other": {"en": "other disaster", "hi": "अन्य आपदा", "bn": "অন্য দুর্যোগ", "mr": "इतर आपत्ती", "te": "ఇతర విపత్తు", "ta": "பிற பேரிடர்"},
}

LOSS_NAMES: dict[str, dict[str, str]] = {
    "house": {"en": "house", "hi": "घर", "bn": "বাড়ি", "mr": "घर", "te": "ఇల్లు", "ta": "வீடு"},
    "crop": {"en": "crop", "hi": "फसल", "bn": "ফসল", "mr": "पीक", "te": "పంట", "ta": "பயிர்"},
    "livestock": {"en": "livestock", "hi": "पशु", "bn": "গবাদি পশু", "mr": "जनावरे", "te": "పశువులు", "ta": "கால்நடைகள்"},
    "vehicle": {"en": "vehicle", "hi": "वाहन", "bn": "গাড়ি", "mr": "वाहन", "te": "వాహనం", "ta": "வாகனம்"},
    "belongings": {"en": "belongings", "hi": "सामान", "bn": "জিনিসপত্র", "mr": "सामान", "te": "సామాన్లు", "ta": "பொருட்கள்"},
    "shop": {"en": "shop", "hi": "दुकान", "bn": "দোকান", "mr": "दुकान", "te": "దుకాణం", "ta": "கடை"},
    "injury": {"en": "injury", "hi": "चोट", "bn": "আঘাত", "mr": "दुखापत", "te": "గాయం", "ta": "காயம்"},
    "death": {"en": "death in family", "hi": "परिवार में मृत्यु", "bn": "পরিবারে মৃত্যু", "mr": "कुटुंबातील मृत्यू", "te": "కుటుంబంలో మరణం", "ta": "குடும்பத்தில் மரணம்"},
    "other": {"en": "other loss", "hi": "अन्य नुकसान", "bn": "অন্য ক্ষতি", "mr": "इतर नुकसान", "te": "ఇతర నష్టం", "ta": "பிற இழப்பு"},
}


def name_of(table: dict[str, dict[str, str]], key: str | None, lang: str) -> str:
    if not key:
        return ""
    row = table.get(key, {})
    return row.get(lang) or row.get("en") or key


def normalize_lang(code: str | None) -> str | None:
    if not code:
        return None
    code = code.lower().split("-")[0].split("_")[0]
    return code if code in LANGUAGES else None
