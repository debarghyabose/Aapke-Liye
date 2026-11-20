from datetime import date, datetime, timezone
from typing import Annotated, Literal

from pydantic import model_validator, BaseModel, Field, PlainSerializer, field_serializer


def iso_utc(d: datetime) -> str:
    """Always UTC with a Z suffix, e.g. 2026-11-20T04:30:00.000Z. Naive values are UTC
    (SQLite drops the timezone; we only ever store UTC)."""
    if d.tzinfo is not None:
        d = d.astimezone(timezone.utc).replace(tzinfo=None)
    return d.isoformat(timespec="milliseconds") + "Z"


UTCDateTime = Annotated[datetime, PlainSerializer(iso_utc, return_type=str)]

STATUSES = ["Draft", "Submitted", "Verified", "Approved", "Paid", "Rejected"]
# Staff moves claims along this path with PUT /status. Draft -> Submitted happens only
# through POST /claims/{id}/submit, which validates the claim and builds the PDF.
STAFF_TRANSITIONS = {
    "Submitted": {"Verified", "Rejected"},
    "Verified": {"Approved", "Rejected"},
    "Approved": {"Paid"},
}


class Loss(BaseModel):
    model_config = {"extra": "forbid"}
    category: str = Field(max_length=40, examples=["house"])
    item: str = Field(max_length=60, examples=["fully_damaged_plain"])
    quantity: float = Field(1, ge=0, le=100000)
    damage_percent: float | None = Field(None, ge=0, le=100)


Text = Annotated[str, Field(max_length=120)]


class ClaimFields(BaseModel):
    """The claim fields Member 1 extracts and the Review screen edits. Unknown keys are
    rejected on PATCH (and ignored when they come from Member 1)."""
    model_config = {"extra": "forbid"}
    name: Text | None = None
    phone: Annotated[str, Field(max_length=20)] | None = None
    village: Text | None = None
    district: Text | None = None
    state: Text | None = None
    disaster_type: Annotated[str, Field(max_length=40)] | None = None
    date_of_incident: date | None = None
    losses: Annotated[list[Loss], Field(max_length=50)] | None = None
    documents_lost: Annotated[list[Annotated[str, Field(max_length=60)]],
                              Field(max_length=20)] | None = None
    bank_account_available: bool | None = None
    # Who in the household needs help first (officials sort these claims to the top).
    vulnerability: Annotated[list[Literal["elderly", "disabled", "single_mother", "child_under_5"]],
                             Field(max_length=4)] | None = None
    crop_insured: bool | None = None   # PMFBY: enables the crop insurance estimate


class ClaimCreate(BaseModel):
    language: str = Field("en", examples=["bn"])
    disaster_type: str | None = Field(None, max_length=40, examples=["flood"])
    consent: Literal[True] = Field(description="The claimant agreed to the consent text")
    consent_text_version: str = Field(min_length=1, max_length=40, examples=["v1"])


class ClaimText(BaseModel):
    """POST /claims/{id}/text: typed or phone-transcribed input for the claim AI."""
    text: str = Field(min_length=1, max_length=2000)


class ClaimFieldsUpdate(BaseModel):
    """Sent by the Review screen when the user taps Edit and corrects fields."""
    fields: ClaimFields


class StatusUpdate(BaseModel):
    status: str
    note: str | None = Field(None, max_length=300)


class PhotoOut(BaseModel):
    """What the claimant sees. Duplicate flags are for officials only (GET /staff/claims)."""
    id: int
    sha256: str
    lat: float | None
    lon: float | None
    taken_at: UTCDateTime | None
    verification: dict

    model_config = {"from_attributes": True}

    @field_serializer("verification")
    def _hide_duplicate(self, v: dict) -> dict:
        return {k: val for k, val in v.items() if k != "duplicate"}


class StaffPhotoOut(PhotoOut):
    duplicate_of_claim_id: str | None   # same photo already used in this other claim

    @field_serializer("verification")
    def _hide_duplicate(self, v: dict) -> dict:
        return v


class RecordingOut(BaseModel):
    id: int
    status: str   # "pending" = waiting for Member 1; call POST /claims/{id}/audio/retry

    model_config = {"from_attributes": True}


class StatusEventOut(BaseModel):
    status: str
    note: str | None
    at: UTCDateTime

    model_config = {"from_attributes": True}


class StatusOut(BaseModel):
    claim_id: str
    status: str
    updated_at: UTCDateTime
    timeline: list[StatusEventOut]


class ClaimOut(BaseModel):
    id: str
    language: str
    disaster_type: str | None
    transcript: str | None
    fields: dict
    missing_fields: list
    follow_up_questions: list
    relief: dict | None
    proof_suggestions: list
    status: str
    pdf_url: str | None = None
    photos: list[PhotoOut] = []
    recordings: list[RecordingOut] = []
    history: list[StatusEventOut] = []
    consent_text_version: str
    consent_given_at: UTCDateTime
    submitted_at: UTCDateTime | None
    created_at: UTCDateTime
    updated_at: UTCDateTime

    model_config = {"from_attributes": True}


class ClaimCreated(ClaimOut):
    claim_token: str = Field(description="Shown once. Send it as X-Claim-Token on every call "
                                         "for this claim. It cannot be recovered if lost.")


class StaffClaimOut(ClaimOut):
    photos: list[StaffPhotoOut] = []
    vulnerability_flags: dict = {}

    @model_validator(mode="after")
    def _vulnerability(self):
        v = set((self.fields or {}).get("vulnerability") or [])
        self.vulnerability_flags = {"is_elderly": "elderly" in v, "is_disabled": "disabled" in v,
                                    "is_single_mother": "single_mother" in v,
                                    "has_child_under_5": "child_under_5" in v}
        return self
