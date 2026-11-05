"""Immutable-intended HTML snapshots and exact-offset extracted passages.

Snapshots are untrusted until their parent source version is reviewed and
explicitly activated. Raw bytes are never returned through a public API.
"""
from sqlalchemy import (
    CheckConstraint, ForeignKey, Integer, LargeBinary, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class KnowledgeSnapshot(Base):
    __tablename__ = "knowledge_source_snapshots"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="ck_snapshot_positive_size"),
        CheckConstraint("capture_method IN ('original_http','browser_rendered_text')",
                        name="ck_snapshot_capture_method"),
    )

    version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_source_versions.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    fetched_url: Mapped[str] = mapped_column(String(700), nullable=False)
    media_type: Mapped[str] = mapped_column(String(60), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    extraction_version: Mapped[str] = mapped_column(String(24), nullable=False)
    raw_body: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    capture_method: Mapped[str] = mapped_column(
        String(32), nullable=False, default="original_http", server_default="original_http"
    )
    observed_url: Mapped[str | None] = mapped_column(String(700))
    observed_title: Mapped[str | None] = mapped_column(String(300))
    observed_last_updated: Mapped[str | None] = mapped_column(String(10))
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)


class KnowledgePassage(Base):
    __tablename__ = "knowledge_source_passages"
    __table_args__ = (
        UniqueConstraint("version_id", "ordinal", name="uq_passage_version_ordinal"),
        CheckConstraint("ordinal >= 0", name="ck_passage_ordinal_nonnegative"),
        CheckConstraint("start_offset >= 0 AND end_offset > start_offset",
                        name="ck_passage_valid_span"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_source_versions.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    section_path: Mapped[str] = mapped_column(String(300), nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
