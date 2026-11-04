"""Synthetic-case model; only authenticated owners can access new records."""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CaseRecord(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Nullable only so old, ownerless demo records survive the migration.
    # Existing NULL-owner records are inaccessible through the API.
    owner_subject: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    procedure: Mapped[str] = mapped_column(
        String(64), nullable=False, default="milan_residence_change"
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    scope_answers: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
