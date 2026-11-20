"""Follow-up questions and the read-back summary, in the user's language.

Templates are the reliable default and the fallback when the LLM fails.
Native speakers should review every non-English line before the demo.
"""
from __future__ import annotations

import json
import logging
import re

from . import llm
from .config import Settings
from .languages import DISASTER_NAMES, LANGUAGES, LOSS_NAMES, name_of
from .schemas import Claim, NextQuestion

log = logging.getLogger("aapke_liye.questions")

T: dict[str, dict[str, str]] = {
    "claimant.name": {
        "en": "What is your full name?",
        "hi": "आपका पूरा नाम क्या है?",
        "bn": "আপনার পুরো নাম কী?",
        "mr": "तुमचे पूर्ण नाव काय आहे?",
        "te": "మీ పూర్తి పేరు ఏమిటి?",
        "ta": "உங்கள் முழு பெயர் என்ன?",
    },
    "claimant.phone": {
        "en": "What is your mobile number?",
        "hi": "आपका मोबाइल नंबर क्या है?",
        "bn": "আপনার মোবাইল নম্বর কত?",
        "mr": "तुमचा मोबाईल नंबर काय आहे?",
        "te": "మీ మొబైల్ నంబర్ ఏమిటి?",
        "ta": "உங்கள் மொபைல் எண் என்ன?",
    },
    "location.village": {
        "en": "Which village or town do you live in?",
        "hi": "आप किस गाँव या शहर में रहते हैं?",
        "bn": "আপনি কোন গ্রাম বা শহরে থাকেন?",
        "mr": "तुम्ही कोणत्या गावात किंवा शहरात राहता?",
        "te": "మీరు ఏ గ్రామం లేదా పట్టణంలో ఉంటారు?",
        "ta": "நீங்கள் எந்த கிராமம் அல்லது ஊரில் வசிக்கிறீர்கள்?",
    },
    "location.district": {
        "en": "Which district is that in?",
        "hi": "यह किस ज़िले में है?",
        "bn": "এটি কোন জেলায়?",
        "mr": "हे कोणत्या जिल्ह्यात आहे?",
        "te": "అది ఏ జిల్లాలో ఉంది?",
        "ta": "அது எந்த மாவட்டத்தில் உள்ளது?",
    },
    "location.state": {
        "en": "Which state is that in?",
        "hi": "यह किस राज्य में है?",
        "bn": "এটি কোন রাজ্যে?",
        "mr": "हे कोणत्या राज्यात आहे?",
        "te": "అది ఏ రాష్ట్రంలో ఉంది?",
        "ta": "அது எந்த மாநிலத்தில் உள்ளது?",
    },
    "disaster_type": {
        "en": "What happened: flood, cyclone, earthquake, landslide, fire or something else?",
        "hi": "क्या हुआ था: बाढ़, चक्रवात, भूकंप, भूस्खलन, आग या कुछ और?",
        "bn": "কী হয়েছিল: বন্যা, ঘূর্ণিঝড়, ভূমিকম্প, ভূমিধস, আগুন নাকি অন্য কিছু?",
        "mr": "काय घडले: पूर, चक्रीवादळ, भूकंप, भूस्खलन, आग की आणखी काही?",
        "te": "ఏమి జరిగింది: వరద, తుఫాను, భూకంపం, కొండచరియలు విరిగిపడటం, అగ్ని ప్రమాదం లేదా మరేదైనా?",
        "ta": "என்ன நடந்தது: வெள்ளம், புயல், நிலநடுக்கம், நிலச்சரிவு, தீ அல்லது வேறு ஏதாவது?",
    },
    "incident_date": {
        "en": "On what date did this happen?",
        "hi": "यह किस तारीख को हुआ?",
        "bn": "এটি কোন তারিখে হয়েছিল?",
        "mr": "हे कोणत्या तारखेला घडले?",
        "te": "ఇది ఏ తేదీన జరిగింది?",
        "ta": "இது எந்த தேதியில் நடந்தது?",
    },
    "losses": {
        "en": "What did you lose: house, crops, animals, vehicle or belongings?",
        "hi": "आपका क्या नुकसान हुआ: घर, फसल, पशु, वाहन या सामान?",
        "bn": "আপনার কী ক্ষতি হয়েছে: বাড়ি, ফসল, গবাদি পশু, গাড়ি নাকি জিনিসপত্র?",
        "mr": "तुमचे काय नुकसान झाले: घर, पीक, जनावरे, वाहन की सामान?",
        "te": "మీకు ఏమి నష్టం జరిగింది: ఇల్లు, పంట, పశువులు, వాహనం లేదా సామాన్లు?",
        "ta": "உங்களுக்கு என்ன இழப்பு: வீடு, பயிர், கால்நடைகள், வாகனம் அல்லது பொருட்கள்?",
    },
    "amount_inr": {
        "en": "Roughly how many rupees is the {item} loss worth?",
        "hi": "{item} के नुकसान की कीमत लगभग कितने रुपये है?",
        "bn": "{item} ক্ষতির আনুমানিক মূল্য কত টাকা?",
        "mr": "{item} नुकसानीची अंदाजे किंमत किती रुपये आहे?",
        "te": "{item} నష్టం విలువ సుమారు ఎన్ని రూపాయలు?",
        "ta": "{item} இழப்பின் மதிப்பு சுமார் எத்தனை ரூபாய்?",
    },
    "house_kind": {
        "en": "Was the house kutcha (mud or thatch) or pucca (brick or cement)?",
        "hi": "घर कच्चा था या पक्का?",
        "bn": "বাড়িটি কাঁচা ছিল নাকি পাকা?",
        "mr": "घर कच्चे होते की पक्के?",
        "te": "ఇల్లు మట్టి ఇల్లా లేక పక్కా ఇల్లా?",
        "ta": "வீடு குடிசை வீடா அல்லது கான்கிரீட் வீடா?",
    },
    "damage_level": {
        "en": "Is it partly damaged or fully destroyed?",
        "hi": "क्या यह थोड़ा टूटा है या पूरी तरह नष्ट हो गया?",
        "bn": "এটি আংশিক ক্ষতিগ্রস্ত নাকি পুরোপুরি ধ্বংস?",
        "mr": "हे अंशतः खराब झाले की पूर्णपणे उद्ध्वस्त झाले?",
        "te": "ఇది కొంత దెబ్బతిన్నదా లేక పూర్తిగా నాశనమైందా?",
        "ta": "இது பகுதியாக சேதமடைந்ததா அல்லது முழுமையாக அழிந்ததா?",
    },
    "crop_name": {
        "en": "Which crop was damaged?",
        "hi": "कौन सी फसल खराब हुई?",
        "bn": "কোন ফসল নষ্ট হয়েছে?",
        "mr": "कोणते पीक खराब झाले?",
        "te": "ఏ పంట దెబ్బతిన్నది?",
        "ta": "எந்த பயிர் சேதமடைந்தது?",
    },
    "area_acres": {
        "en": "How many acres of crop were damaged?",
        "hi": "कितने एकड़ फसल खराब हुई?",
        "bn": "কত একর ফসল নষ্ট হয়েছে?",
        "mr": "किती एकर पीक खराब झाले?",
        "te": "ఎన్ని ఎకరాల పంట దెబ్బతిన్నది?",
        "ta": "எத்தனை ஏக்கர் பயிர் சேதமடைந்தது?",
    },
    "animal": {
        "en": "Which animals did you lose?",
        "hi": "आपके कौन से पशु मरे या खो गए?",
        "bn": "আপনার কোন পশু মারা গেছে বা হারিয়েছে?",
        "mr": "तुमची कोणती जनावरे मेली किंवा हरवली?",
        "te": "మీ ఏ పశువులు చనిపోయాయి లేదా తప్పిపోయాయి?",
        "ta": "உங்கள் எந்த கால்நடைகள் இறந்தன அல்லது காணாமல் போயின?",
    },
    "count": {
        "en": "How many animals?",
        "hi": "कितने पशु?",
        "bn": "কতগুলি পশু?",
        "mr": "किती जनावरे?",
        "te": "ఎన్ని పశువులు?",
        "ta": "எத்தனை கால்நடைகள்?",
    },
    "vehicle_kind": {
        "en": "What kind of vehicle was damaged: bicycle, two-wheeler, auto, car or tractor?",
        "hi": "कौन सा वाहन खराब हुआ: साइकिल, दोपहिया, ऑटो, कार या ट्रैक्टर?",
        "bn": "কোন গাড়ি ক্ষতিগ্রস্ত হয়েছে: সাইকেল, বাইক, অটো, গাড়ি নাকি ট্রাক্টর?",
        "mr": "कोणते वाहन खराब झाले: सायकल, दुचाकी, रिक्षा, कार की ट्रॅक्टर?",
        "te": "ఏ వాహనం దెబ్బతిన్నది: సైకిల్, బైక్, ఆటో, కారు లేదా ట్రాక్టర్?",
        "ta": "எந்த வாகனம் சேதமடைந்தது: சைக்கிள், பைக், ஆட்டோ, கார் அல்லது டிராக்டர்?",
    },
    "description": {
        "en": "Please describe what was lost.",
        "hi": "कृपया बताइए क्या नुकसान हुआ।",
        "bn": "অনুগ্রহ করে কী ক্ষতি হয়েছে বলুন।",
        "mr": "कृपया काय नुकसान झाले ते सांगा.",
        "te": "దయచేసి ఏమి నష్టం జరిగిందో చెప్పండి.",
        "ta": "தயவுசெய்து என்ன இழப்பு என்று சொல்லுங்கள்.",
    },
    "confirm": {
        "en": "Please check: {summary}. Is this correct?",
        "hi": "कृपया जाँच लें: {summary}। क्या यह सही है?",
        "bn": "অনুগ্রহ করে মিলিয়ে নিন: {summary}। এটা কি ঠিক আছে?",
        "mr": "कृपया तपासा: {summary}. हे बरोबर आहे का?",
        "te": "దయచేసి సరిచూడండి: {summary}. ఇది సరైనదేనా?",
        "ta": "தயவுசெய்து சரிபார்க்கவும்: {summary}. இது சரியா?",
    },
    "correct_what": {
        "en": "What should I correct?",
        "hi": "क्या सुधारना है? कृपया सही जानकारी बताइए।",
        "bn": "কী সংশোধন করতে হবে? সঠিক তথ্যটি বলুন।",
        "mr": "काय दुरुस्त करायचे आहे? कृपया बरोबर माहिती सांगा.",
        "te": "ఏమి సరిచేయాలి? దయచేసి సరైన వివరాలు చెప్పండి.",
        "ta": "எதைத் திருத்த வேண்டும்? சரியான தகவலைச் சொல்லுங்கள்.",
    },
    "repeat": {
        "en": "Sorry, I could not hear that clearly. Could you please say it again?",
        "hi": "माफ़ कीजिए, मैं ठीक से सुन नहीं पाया। क्या आप फिर से बोल सकते हैं?",
        "bn": "দুঃখিত, আমি পরিষ্কার শুনতে পাইনি। আবার বলবেন?",
        "mr": "माफ करा, मला नीट ऐकू आले नाही. कृपया पुन्हा सांगाल का?",
        "te": "క్షమించండి, నాకు స్పష్టంగా వినిపించలేదు. దయచేసి మళ్ళీ చెప్పగలరా?",
        "ta": "மன்னிக்கவும், எனக்கு சரியாகக் கேட்கவில்லை. மீண்டும் சொல்ல முடியுமா?",
    },
    "done": {
        "en": "Thank you. Your claim has been recorded.",
        "hi": "धन्यवाद। आपका दावा दर्ज हो गया है।",
        "bn": "ধন্যবাদ। আপনার দাবি নথিভুক্ত হয়েছে।",
        "mr": "धन्यवाद. तुमचा दावा नोंदवला गेला आहे.",
        "te": "ధన్యవాదాలు. మీ క్లెయిమ్ నమోదు చేయబడింది.",
        "ta": "நன்றி. உங்கள் கோரிக்கை பதிவு செய்யப்பட்டது.",
    },
}

LOSS_IDX = re.compile(r"^losses\[(\d+)\]\.(\w+)$")


def _key_for(field: str) -> tuple[str, int | None]:
    m = LOSS_IDX.match(field)
    if m:
        return m.group(2), int(m.group(1))
    return field, None


def template(key: str, lang: str, **fmt) -> str:
    row = T[key]
    return row.get(lang, row["en"]).format(**fmt)


def template_question(field: str, claim: Claim) -> NextQuestion:
    key, idx = _key_for(field)
    lang = claim.language
    item = item_en = ""
    if idx is not None and idx < len(claim.losses):
        loss = claim.losses[idx]
        label = loss.crop_name or loss.animal or loss.vehicle_kind
        item = label or name_of(LOSS_NAMES, loss.type, lang)
        item_en = label or name_of(LOSS_NAMES, loss.type, "en")
    return NextQuestion(field=field, text=template(key, lang, item=item), text_en=template(key, "en", item=item_en))


def summary(claim: Claim, lang: str) -> str:
    parts = []
    if claim.claimant.name:
        parts.append(claim.claimant.name)
    place = ", ".join(p for p in [claim.location.village, claim.location.district, claim.location.state] if p)
    if place:
        parts.append(place)
    if claim.disaster_type:
        d = name_of(DISASTER_NAMES, claim.disaster_type, lang)
        parts.append(f"{d} {claim.incident_date or ''}".strip())
    for loss in claim.losses:
        label = name_of(LOSS_NAMES, loss.type, lang)
        extra = loss.crop_name or loss.animal or loss.vehicle_kind or ""
        if loss.area_acres:
            extra += f" {loss.area_acres:g} ac"
        if loss.count:
            extra = f"{loss.count} {extra}"
        amt = f" ₹{_inr(loss.amount_inr)}" if loss.amount_inr else ""
        parts.append(f"{label} {extra}".strip() + amt)
    if claim.claimant.phone:
        parts.append(claim.claimant.phone)
    return "; ".join(parts)


def _inr(n: float) -> str:
    """Indian digit grouping: 250000 -> 2,50,000."""
    s = str(int(round(n)))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups) + "," + tail


def confirm_question(claim: Claim) -> NextQuestion:
    return NextQuestion(
        field="confirm",
        text=template("confirm", claim.language, summary=summary(claim, claim.language)),
        text_en=template("confirm", "en", summary=summary(claim, "en")),
    )


# ---------------------------------------------------------------- LLM phrasing

_Q_SCHEMA = llm.obj({"text": {"type": "string"}, "text_en": {"type": "string"}})

_Q_SYSTEM = """You help disaster victims in India file relief claims by voice.
Write ONE short, kind follow-up question that asks only for the requested field.
The person may be distressed: be warm, plain and brief (under 20 words). No greetings, no lists
unless the field is a choice. Write `text` in the requested language and script, and `text_en`
as its English meaning. If a reference wording is given, keep its meaning."""


def llm_question(field: str, claim: Claim, settings: Settings) -> NextQuestion:
    ref = template_question(field, claim)
    payload = {
        "language": LANGUAGES.get(claim.language, claim.language),
        "field_needed": field,
        "reference_wording": ref.text_en,
        "what_we_know": summary(claim, "en"),
    }
    try:
        out = llm.structured(settings, system=_Q_SYSTEM, content=json.dumps(payload, ensure_ascii=False),
                             schema=_Q_SCHEMA, max_tokens=1000)
        return NextQuestion(field=field, text=out["text"], text_en=out["text_en"])
    except llm.LLMError as exc:
        log.warning("LLM question failed, using template: %s", exc)
        return ref


def next_question(field: str, claim: Claim, settings: Settings) -> NextQuestion:
    if settings.is_mock or settings.question_mode != "llm":
        return template_question(field, claim)
    return llm_question(field, claim, settings)
