"""Private synthetic-only preparation state, separated from demo scope records."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class CasePreparation(Base):
    __tablename__ = "case_preparations"

    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True,
    )
    owner_subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    facts_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, default=lambda: b"")
    review_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now,
    )


class CaseDocument(Base):
    __tablename__ = "case_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                     default=lambda: str(uuid4()))
    case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    owner_subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    media_type: Mapped[str] = mapped_column(String(40), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    review_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, default=lambda: b"")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now,
    )
