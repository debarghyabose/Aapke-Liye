"""
Pydantic API Schemas matching frontend contracts
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ClaimCreate(BaseModel):
    language: str = "en"
    disaster_type: Optional[str] = None
    consent_text_version: str = "v1"


class ClaimFields(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    village: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    disaster_type: Optional[str] = None
    date_of_incident: Optional[str] = None
    losses: List[Dict[str, Any]] = Field(default_factory=list)
    documents_lost: List[str] = Field(default_factory=list)
    vulnerability: List[str] = Field(default_factory=list)
    bank_account_available: Optional[bool] = None
    is_hilly: Optional[bool] = False
    crop_insured: Optional[bool] = False
    household_id: Optional[str] = None


class ClaimFieldsUpdate(BaseModel):
    fields: ClaimFields


class ClaimText(BaseModel):
    text: str


class HouseholdLink(BaseModel):
    household_id: str


class StatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None


class SpeechRequest(BaseModel):
    text: str
    language: str = "en"


class VaultDocumentCreate(BaseModel):
    doc_type: str
    source: str = "upload"


class VaultDocumentOut(BaseModel):
    id: str
    doc_type: str
    content_type: str
    source: str
    created_at: str
    file_url: str = ""


class HouseholdCreated(BaseModel):
    household_id: str
    household_token: str


class HouseholdOut(BaseModel):
    household_id: str
    created_at: str
    documents: List[VaultDocumentOut] = Field(default_factory=list)
