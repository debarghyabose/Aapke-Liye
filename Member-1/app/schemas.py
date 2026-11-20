"""Shared data contracts. This file is the one Member 2 and Member 4 sign off on.

Bump SCHEMA_VERSION whenever a field is renamed or removed.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"

LanguageCode = Literal["en", "hi", "bn", "mr", "te", "ta"]
DisasterType = Literal["flood", "cyclone", "earthquake", "landslide", "fire", "drought", "storm", "other"]
LossType = Literal["house", "crop", "livestock", "vehicle", "belongings", "shop", "injury", "death", "other"]
ClaimStatus = Literal["incomplete", "needs_confirmation", "complete"]


class Claimant(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


class Location(BaseModel):
    village: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None


class Loss(BaseModel):
    type: LossType
    description: Optional[str] = None
    amount_inr: Optional[float] = None
    # house / shop
    house_kind: Optional[Literal["kutcha", "pucca", "semi_pucca"]] = None
    damage_level: Optional[Literal["partial", "severe", "destroyed"]] = None
    # crop
    crop_name: Optional[str] = None
    area_acres: Optional[float] = None
    # livestock
    animal: Optional[str] = None
    count: Optional[int] = None
    # vehicle
    vehicle_kind: Optional[str] = None


class Transcript(BaseModel):
    original: str
    english: Optional[str] = None
    normalized: Optional[str] = None
    language: Optional[str] = None
    asr_provider: Optional[str] = None
    confidence: Optional[float] = None


class Claim(BaseModel):
    schema_version: str = SCHEMA_VERSION
    session_id: str
    language: LanguageCode = "hi"
    status: ClaimStatus = "incomplete"
    claimant: Claimant = Field(default_factory=Claimant)
    location: Location = Field(default_factory=Location)
    disaster_type: Optional[DisasterType] = None
    incident_date: Optional[str] = None  # ISO YYYY-MM-DD
    losses: list[Loss] = Field(default_factory=list)
    documents_lost: list[str] = Field(default_factory=list)
    field_confidence: dict[str, float] = Field(default_factory=dict)
    transcripts: list[Transcript] = Field(default_factory=list)


class NextQuestion(BaseModel):
    field: str  # dotted path, e.g. "claimant.phone", "losses[0].area_acres", or "confirm"
    text: str  # in the user's language
    text_en: str
    audio_base64: Optional[str] = None  # filled when TTS is on


# ---------- API: speech ----------


class TranscribeRequest(BaseModel):
    audio_base64: Optional[str] = None
    audio_url: Optional[str] = None
    language: Optional[LanguageCode] = None


class TranscribeResponse(BaseModel):
    text: str
    language: str
    confidence: float
    provider: str
    duration_s: Optional[float] = None


# ---------- API: claim turn ----------


class TurnRequest(BaseModel):
    session_id: str
    language: Optional[LanguageCode] = None
    audio_base64: Optional[str] = None
    audio_url: Optional[str] = None
    text: Optional[str] = None  # typed input, or a transcript Member 2 already has
    claim: Optional[Claim] = None  # current state; omit on the first turn
    confirmed: Optional[bool] = None  # set by Member 4's Confirm / Edit buttons


class TurnResponse(BaseModel):
    claim: Claim
    transcript: Optional[str] = None
    missing_fields: list[str]
    next_question: Optional[NextQuestion] = None
    status: ClaimStatus
    message: Optional[str] = None  # e.g. "please repeat", "claim recorded"
    timings_ms: dict[str, int] = Field(default_factory=dict)


# ---------- API: Phase 2 ----------


class DamageCompareRequest(BaseModel):
    baseline_image_base64: str
    damage_image_base64: str
    baseline_media_type: str = "image/jpeg"
    damage_media_type: str = "image/jpeg"
    context: Optional[str] = None  # e.g. "kutcha house, cyclone"


class DamageCompareResponse(BaseModel):
    same_property: bool
    damage_score: int  # 0-100
    level: Literal["none", "partial", "severe", "destroyed"]
    damaged_items: list[str]
    reason: str
    confidence: float
    needs_human_review: bool


DocType = Literal[
    "aadhaar_reissue",
    "ration_card_reissue",
    "land_record_reissue",
    "insurance_home",
    "insurance_vehicle",
    "insurance_crop",
    "followup_letter",
    "grievance",
    "rti_application",
]


class DraftRequest(BaseModel):
    doc_type: DocType
    claim: Claim
    extra: dict[str, str] = Field(default_factory=dict)  # policy_no, claim_id, office, ...
    language: Literal["en", "hi"] = "en"


class DraftResponse(BaseModel):
    doc_type: str
    title: str
    text: str
    missing_fields: list[str]  # placeholders left as [TO FILL: ...]
    template_source: str


class EscalationRequest(BaseModel):
    days_pending: int
    steps_done: list[Literal["followup_letter", "grievance", "rti_application"]] = Field(default_factory=list)


class EscalationResponse(BaseModel):
    next_step: Optional[Literal["followup_letter", "grievance", "rti_application"]]
    reason: str
