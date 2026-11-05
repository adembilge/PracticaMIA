"""Append-only audit records for source review and automatic invalidation."""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeReviewEvent(Base):
    __tablename__ = "knowledge_review_events"
    __table_args__ = (
        CheckConstraint(
            "action IN ('approved', 'revoked', 'source_changed')",
            name="ck_knowledge_review_event_action",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    source_id: Mapped[str] = mapped_column(
        String(96), ForeignKey("knowledge_sources.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_source_versions.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    old_source_status: Mapped[str] = mapped_column(String(24), nullable=False)
    new_source_status: Mapped[str] = mapped_column(String(24), nullable=False)
    old_version_status: Mapped[str] = mapped_column(String(24), nullable=False)
    new_version_status: Mapped[str] = mapped_column(String(24), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
