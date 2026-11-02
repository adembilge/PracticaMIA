"""Tables named by the schema note. No credential column."""
from sqlalchemy import Boolean, CheckConstraint, Computed, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import Vector

DIM = 32


class Base(DeclarativeBase):
    pass


class Person(Base):
    __tablename__ = "person"
    id: Mapped[str] = mapped_column(Text, primary_key=True)


class Case(Base):
    __tablename__ = "case"
    __table_args__ = (
        CheckConstraint("stop IN ('not ready', 'ready to hand over')", name="case_stop"),
        Index("case_one_open", "person_id", unique=True, postgresql_where=text("open")),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("person.id", ondelete="CASCADE"))
    language: Mapped[str | None] = mapped_column(Text)
    f02: Mapped[str | None] = mapped_column(Text)
    f03: Mapped[str | None] = mapped_column(Text)
    f04: Mapped[str | None] = mapped_column(Text)
    f05: Mapped[str | None] = mapped_column(Text)
    f06: Mapped[str | None] = mapped_column(Text)
    missing_field: Mapped[str | None] = mapped_column(Text)
    stop: Mapped[str] = mapped_column(Text)
    named_name: Mapped[str | None] = mapped_column(Text)
    named_address: Mapped[str | None] = mapped_column(Text)
    open: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class Message(Base):
    __tablename__ = "message"
    __table_args__ = (Index("message_order", "case_id", "position", unique=True),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("case.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    body: Mapped[str] = mapped_column(Text)


class Upload(Base):
    __tablename__ = "upload"
    __table_args__ = (
        CheckConstraint("role IN ('title', 'identity')", name="upload_role"),
        CheckConstraint("status IN ('failed', 'unreadable', 'read')", name="upload_status"),
        CheckConstraint(
            "status = 'read' OR (extracted_name IS NULL AND extracted_address IS NULL)",
            name="upload_extraction",
        ),
        Index("upload_one_current", "case_id", "role", unique=True, postgresql_where=text("current")),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("case.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    path: Mapped[str | None] = mapped_column(Text)
    extracted_name: Mapped[str | None] = mapped_column(Text)
    extracted_address: Mapped[str | None] = mapped_column(Text)
    current: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class Session(Base):
    __tablename__ = "session"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("case.id", ondelete="CASCADE"))
    missing_field: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))


class SourceRecord(Base):
    __tablename__ = "source_record"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    file: Mapped[str] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(Text, server_default=text("'unreviewed'"))


class ProcedureRow(Base):
    __tablename__ = "procedure_row"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    file: Mapped[str] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(Text, server_default=text("'unreviewed'"))


class RequirementRow(Base):
    __tablename__ = "requirement_row"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    file: Mapped[str] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(Text, server_default=text("'unreviewed'"))


class SourceDocument(Base):
    __tablename__ = "source_document"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    review_status: Mapped[str] = mapped_column(Text, server_default=text("'unreviewed'"))


class SourceVersion(Base):
    __tablename__ = "source_version"
    __table_args__ = (
        CheckConstraint("review_status IN ('unreviewed', 'trusted')", name="source_version_review"),
        Index(
            "source_version_one_trusted",
            "source_document_id",
            unique=True,
            postgresql_where=text("review_status = 'trusted'"),
        ),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    source_document_id: Mapped[str] = mapped_column(ForeignKey("source_document.id"))
    review_status: Mapped[str] = mapped_column(Text, server_default=text("'unreviewed'"))


class Passage(Base):
    __tablename__ = "passage"
    __table_args__ = (
        Index("passage_body_gin", "body_tsv", postgresql_using="gin"),
        Index(
            "passage_lookup",
            "source_version_id",
            "jurisdiction",
            "procedure",
            "language",
            "review_status",
        ),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    source_version_id: Mapped[str] = mapped_column(ForeignKey("source_version.id"))
    source_id: Mapped[str] = mapped_column(Text)
    section: Mapped[str | None] = mapped_column(Text)
    jurisdiction: Mapped[str | None] = mapped_column(Text)
    procedure: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(Text, server_default=text("'unreviewed'"))
    body: Mapped[str] = mapped_column(Text)
    body_tsv: Mapped[str] = mapped_column(TSVECTOR, Computed("to_tsvector('simple', body)", persisted=True))


class Embedding(Base):
    __tablename__ = "embedding"
    passage_id: Mapped[str] = mapped_column(ForeignKey("passage.id"), primary_key=True)
    model_name: Mapped[str] = mapped_column(Text)
    embedding_version: Mapped[str] = mapped_column(Text)
    vector: Mapped[list[float]] = mapped_column(Vector(DIM))


class Citation(Base):
    __tablename__ = "citation"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    requirement_row_id: Mapped[str] = mapped_column(ForeignKey("requirement_row.id"))
    passage_id: Mapped[str] = mapped_column(ForeignKey("passage.id"))
    review_status: Mapped[str] = mapped_column(Text, server_default=text("'unreviewed'"))


class AuditEvent(Base):
    __tablename__ = "audit_event"
    __table_args__ = (
        CheckConstraint(
            "action IN ('opened', 'answer saved', 'upload replaced', 'value named', 'stop became ready')",
            name="audit_action",
        ),
        Index("audit_by_case", "case_id"),
    )
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("case.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(Text)
