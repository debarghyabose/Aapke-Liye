"""Turn spoken amounts into numbers: "do lakh pachas hazaar" -> 250000.

The normalized text and the amount hints are given to the LLM alongside the
original transcript, so mistakes here are a hint, not the final answer.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# Number words -> value, all languages in one table (keys are lowercase).
NUMBER_WORDS: dict[str, float] = {
    # English
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "fifteen": 15, "twenty": 20, "twenty-five": 25, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "half": 0.5, "a": 1,
    # Hindi (romanized)
    "ek": 1, "do": 2, "teen": 3, "tin": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5, "chhe": 6,
    "che": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10, "pandrah": 15, "bees": 20, "pachees": 25,
    "pachchis": 25, "tees": 30, "chalees": 40, "chalis": 40, "pachas": 50, "pachaas": 50, "saath": 60,
    "sattar": 70, "assi": 80, "nabbe": 90, "dedh": 1.5, "dhai": 2.5, "dhaai": 2.5,
    # Hindi (Devanagari)
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "छह": 6, "छः": 6, "सात": 7, "आठ": 8,
    "नौ": 9, "दस": 10, "पंद्रह": 15, "बीस": 20, "पच्चीस": 25, "तीस": 30, "चालीस": 40, "पचास": 50,
    "साठ": 60, "सत्तर": 70, "अस्सी": 80, "नब्बे": 90, "डेढ़": 1.5, "ढाई": 2.5,
    # Marathi
    "दोन": 2, "पाच": 5, "सहा": 6, "नऊ": 9, "दहा": 10, "वीस": 20, "पंचवीस": 25, "चाळीस": 40,
    "पन्नास": 50, "दीड": 1.5, "अडीच": 2.5,
    # Bengali
    "এক": 1, "দুই": 2, "দু": 2, "তিন": 3, "চার": 4, "পাঁচ": 5, "ছয়": 6, "সাত": 7, "আট": 8, "নয়": 9,
    "দশ": 10, "বিশ": 20, "পঁচিশ": 25, "ত্রিশ": 30, "চল্লিশ": 40, "পঞ্চাশ": 50, "ষাট": 60, "সত্তর": 70, "আশি": 80, "নব্বই": 90, "দেড়": 1.5, "আড়াই": 2.5,
    # Telugu
    "ఒకటి": 1, "ఒక": 1, "రెండు": 2, "మూడు": 3, "నాలుగు": 4, "ఐదు": 5, "ఆరు": 6, "ఏడు": 7,
    "ఎనిమిది": 8, "తొమ్మిది": 9, "పది": 10, "ఇరవై": 20, "ముప్పై": 30, "నలభై": 40, "యాభై": 50,
    # Tamil
    "ஒன்று": 1, "ஒரு": 1, "இரண்டு": 2, "மூன்று": 3, "நான்கு": 4, "ஐந்து": 5, "ஆறு": 6, "ஏழு": 7,
    "எட்டு": 8, "ஒன்பது": 9, "பத்து": 10, "இருபது": 20, "முப்பது": 30, "நாற்பது": 40, "ஐம்பது": 50,
}

# Multiplier word stems (prefix match so inflections like "లక్షలు", "লাখের" work).
MULTIPLIERS: list[tuple[float, tuple[str, ...]]] = [
    (1e7, ("crore", "karod", "करोड़", "करोड", "कोटी", "কোটি", "కోటి", "కోట్ల", "கோடி")),
    (1e5, ("lakh", "lac", "laakh", "लाख", "লাখ", "লক্ষ", "లక్ష", "லட்ச", "லட்சம்")),
    (1e3, ("thousand", "hazaar", "hazar", "hajar", "हज़ार", "हजार", "হাজার", "వేల", "వేయి", "వెయ్యి", "ஆயிர")),
    (1e2, ("hundred", "sau", "सौ", "शे", "শো", "শত", "వంద", "நூறு", "நூற்")),
]

_PUNCT = ".,;:!?।॥()[]\"'“”‘’"
_NUM_RE = re.compile(r"^[₹]?\d[\d,]*(\.\d+)?$")


@dataclass
class Normalized:
    text: str
    amounts: list[int] = field(default_factory=list)  # every money-like value >= 100


def native_digits_to_ascii(text: str) -> str:
    """Convert Devanagari/Bengali/Telugu/Tamil digits to 0-9."""
    out = []
    for ch in text:
        if ch.isdigit() and not ch.isascii():
            try:
                out.append(str(unicodedata.decimal(ch)))
                continue
            except ValueError:
                pass
        out.append(ch)
    return "".join(out)


def _word_value(tok: str) -> float | None:
    t = tok.lower().strip(_PUNCT)
    t = t.lstrip("₹").replace("rs", "") if t.startswith(("₹", "rs")) and any(c.isdigit() for c in t) else t
    if _NUM_RE.match(t):
        return float(t.replace(",", "").lstrip("₹"))
    return NUMBER_WORDS.get(t)


def _multiplier(tok: str) -> float | None:
    t = tok.lower().strip(_PUNCT)
    for value, stems in MULTIPLIERS:
        if any(t.startswith(s) for s in stems):
            return value
    return None


def normalize_text(text: str) -> Normalized:
    text = native_digits_to_ascii(text)
    # split "2lakh" / "50हजार" into "2 lakh"
    text = re.sub(r"(\d)([^\W\d_])", r"\1 \2", text)
    tokens = text.split()
    out: list[str] = []
    amounts: list[int] = []

    i = 0
    while i < len(tokens):
        # Read a compound number: (value multiplier)+ [value]
        total = 0.0
        j = i
        last_mult = float("inf")
        consumed_any = False
        while j < len(tokens):
            val = _word_value(tokens[j])
            mult = _multiplier(tokens[j + 1]) if (val is not None and j + 1 < len(tokens)) else None
            if val is not None and mult is not None and mult < last_mult:
                # "a lakh" only counts with a multiplier; plain "a" stays a word
                total += val * mult
                last_mult = mult
                j += 2
                consumed_any = True
                continue
            if val is None and _multiplier(tokens[j]) and not consumed_any:
                # bare "lakh" = 1 lakh
                m = _multiplier(tokens[j])
                total += m
                last_mult = m
                j += 1
                consumed_any = True
                continue
            break

        if consumed_any:
            n = int(round(total))
            out.append(str(n))
            if n >= 100:
                amounts.append(n)
            i = j
            continue

        tok = tokens[i]
        val = _word_value(tok)
        if val is not None and _NUM_RE.match(tok.lower().strip(_PUNCT)):
            n = val
            if n >= 100 and not _looks_like_phone_or_year(tok):
                amounts.append(int(round(n)))
            out.append(str(int(n)) if n == int(n) else str(n))
        else:
            out.append(tok)
        i += 1

    return Normalized(text=" ".join(out), amounts=amounts)


def _looks_like_phone_or_year(tok: str) -> bool:
    digits = re.sub(r"\D", "", tok)
    if len(digits) >= 10:
        return True
    if len(digits) == 4 and digits.startswith(("19", "20")) and "," not in tok and "₹" not in tok:
        return True
    return False
