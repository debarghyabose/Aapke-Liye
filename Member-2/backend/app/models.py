import base64
import secrets
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .logs import request_id_var


def now():
    """All timestamps are stored in UTC."""
    return datetime.now(timezone.utc)


def new_claim_id():
    """e.g. AL-K7Q2MZX4P9TB: 12 random base32 characters (60 bits), not guessable."""
    return "AL-" + base64.b32encode(secrets.token_bytes(10)).decode()[:12]


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(20), primary_key=True, default=new_claim_id)
    token_hash: Mapped[str] = mapped_column(String(64))           # sha256 of the claim_token
    language: Mapped[str] = mapped_column(String(5), default="en")
    disaster_type: Mapped[str | None] = mapped_column(String(40))
    transcript: Mapped[str | None] = mapped_column(Text)
    fields: Mapped[dict] = mapped_column(JSON, default=dict)        # from Member 1 (+ user edits)
    missing_fields: Mapped[list] = mapped_column(JSON, default=list)
    follow_up_questions: Mapped[list] = mapped_column(JSON, default=list)
    ai_state: Mapped[dict | None] = mapped_column(JSON)  # Member 1's claim; sent back each turn
    relief: Mapped[dict | None] = mapped_column(JSON)               # SDRF calculation
    proof_suggestions: Mapped[list] = mapped_column(JSON, default=list)
    pdf_path: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    consent_text_version: Mapped[str] = mapped_column(String(40))
    consent_given_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    # lazy="selectin": always loaded with the claim (async sessions cannot lazy-load)
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan", lazy="selectin", order_by="Photo.id"
    )
    recordings: Mapped[list["AudioRecording"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan", lazy="selectin",
        order_by="AudioRecording.id"
    )
    history: Mapped[list["StatusEvent"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan", lazy="selectin",
        order_by="StatusEvent.id"
    )


class AudioRecording(Base):
    """Every recording is kept, so one that failed at Member 1 can be retried."""
    __tablename__ = "audio_recordings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    path: Mapped[str] = mapped_column(String(300))
    content_type: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | processed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    claim: Mapped[Claim] = relationship(back_populates="recordings")


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    path: Mapped[str] = mapped_column(String(300))
    content_type: Mapped[str] = mapped_column(String(60))
    sha256: Mapped[str] = mapped_column(String(64), index=True)   # for duplicate checks
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # UTC
    verification: Mapped[dict] = mapped_column(JSON, default=dict)  # from Member 3 + "status"
    duplicate_of_claim_id: Mapped[str | None] = mapped_column(String(20))  # officials only

    claim: Mapped[Claim] = relationship(back_populates="photos")


class StatusEvent(Base):
    """Status history. Member 4's GET/PUT /status APIs can read/write this table."""
    __tablename__ = "claim_status_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(String(300))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    claim: Mapped[Claim] = relationship(back_populates="history")


class AuditLog(Base):
    """Every action on a claim. `detail` holds IDs, keys and statuses only, never personal data
    (no names, phone numbers, transcripts or addresses)."""
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[str | None] = mapped_column(String(20), index=True)
    actor: Mapped[str] = mapped_column(String(80))   # "claimant", "staff:<label>" or "system"
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    request_id: Mapped[str | None] = mapped_column(String(64))  # matches the X-Request-ID log
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def audit(db, claim_id: str | None, action: str, actor: str = "claimant", **detail):
    """Record an action. Pass only IDs, field names and statuses in `detail`."""
    db.add(AuditLog(claim_id=claim_id, actor=actor, action=action, detail=detail,
                    request_id=request_id_var.get()))
