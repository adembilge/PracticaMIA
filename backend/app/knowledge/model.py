"""Versioned official-source registry, separate from private user cases.

A discovered source is not a reviewed source. No candidate can be retrieved as
trusted evidence without an explicitly approved, active, hash-bound version.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"
    __table_args__ = (
        CheckConstraint(
            "status IN ('candidate', 'approved', 'revoked')",
            name="ck_knowledge_sources_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    institution: Mapped[str] = mapped_column(String(160), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    procedure_id: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(5), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    official_url: Mapped[str] = mapped_column(String(700), nullable=False, unique=True)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="candidate")
    active_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    versions: Mapped[list["KnowledgeSourceVersion"]] = relationship(
        back_populates="source"
    )


class KnowledgeSourceVersion(Base):
    __tablename__ = "knowledge_source_versions"
    __table_args__ = (
        UniqueConstraint("source_id", "revision", name="uq_source_revision"),
        CheckConstraint(
            "status IN ('pending_review', 'approved', 'revoked', 'superseded')",
            name="ck_source_version_status",
        ),
        CheckConstraint("revision > 0", name="ck_source_revision_positive"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String(96), ForeignKey("knowledge_sources.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="pending_review"
    )
    source: Mapped[KnowledgeSource] = relationship(back_populates="versions")
