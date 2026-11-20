import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now():
    return datetime.now(timezone.utc)


def new_claim_id():
    return "AL-" + uuid.uuid4().hex[:8].upper()


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(20), primary_key=True, default=new_claim_id)
    language: Mapped[str] = mapped_column(String(5), default="en")
    disaster_type: Mapped[str | None] = mapped_column(String(40))
    transcript: Mapped[str | None] = mapped_column(Text)
    fields: Mapped[dict] = mapped_column(JSON, default=dict)        # from Member 1 (+ user edits)
    missing_fields: Mapped[list] = mapped_column(JSON, default=list)
    follow_up_questions: Mapped[list] = mapped_column(JSON, default=list)
    relief: Mapped[dict | None] = mapped_column(JSON)               # SDRF calculation
    proof_suggestions: Mapped[list] = mapped_column(JSON, default=list)
    pdf_path: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    photos: Mapped[list["Photo"]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    history: Mapped[list["StatusEvent"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan", order_by="StatusEvent.at"
    )


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    path: Mapped[str] = mapped_column(String(300))
    sha256: Mapped[str] = mapped_column(String(64), index=True)   # for duplicate checks
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    taken_at: Mapped[str | None] = mapped_column(String(40))
    verification: Mapped[dict] = mapped_column(JSON, default=dict)  # from Member 3

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
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[str | None] = mapped_column(String(20), index=True)
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
