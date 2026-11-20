from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

STATUSES = ["Draft", "Submitted", "Verified", "Approved", "Paid", "Rejected"]


class ClaimCreate(BaseModel):
    language: str = Field("en", examples=["bn"])
    disaster_type: str | None = Field(None, examples=["flood"])


class ClaimFieldsUpdate(BaseModel):
    """Sent by the Review screen when the user taps Edit and corrects fields."""
    fields: dict[str, Any]


class StatusUpdate(BaseModel):
    status: str
    note: str | None = None


class PhotoOut(BaseModel):
    id: int
    sha256: str
    lat: float | None
    lon: float | None
    taken_at: str | None
    verification: dict

    model_config = {"from_attributes": True}


class StatusEventOut(BaseModel):
    status: str
    note: str | None
    at: datetime

    model_config = {"from_attributes": True}


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
    history: list[StatusEventOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
