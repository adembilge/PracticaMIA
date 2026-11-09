"""Owner-scoped structured intake. No addresses, identifiers, or document bytes."""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CaseIntake(Base):
    __tablename__ = "case_intakes"

    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True
    )
    owner_subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    facts: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
