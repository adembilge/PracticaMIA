"""Persist thread ownership and explicit links to saved cases."""

from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import DateTime, ForeignKey, Integer, String, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.auth.tokens import Principal
from app.cases.model import CaseRecord
from app.database import Base


class AgentThread(Base):
    __tablename__ = "agent_threads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, server_default="1")


class AgentThreadCase(Base):
    __tablename__ = "agent_thread_cases"

    thread_id: Mapped[str] = mapped_column(
        ForeignKey("agent_threads.id", ondelete="CASCADE"), primary_key=True,
    )
    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True, index=True,
    )


def active_case_links(thread_id: UUID, principal: Principal):
    """Read currently active cases linked to an owned thread."""
    return (
        select(CaseRecord)
        .join(AgentThreadCase, AgentThreadCase.case_id == CaseRecord.id)
        .join(AgentThread, AgentThread.id == AgentThreadCase.thread_id)
        .where(
            AgentThread.id == str(thread_id), AgentThread.owner_subject == principal.subject,
            CaseRecord.owner_subject == principal.subject, CaseRecord.archived_at.is_(None),
        )
        .execution_options(populate_existing=True)
    )


def create_thread(db: Session, *, principal: Principal) -> UUID:
    """Create a server-identified thread inside the caller's transaction."""
    thread_id = uuid4()
    db.add(AgentThread(
        id=str(thread_id), owner_subject=principal.subject, created_at=datetime.now(timezone.utc),
    ))
    return thread_id


def create_thread_for_message(db: Session, *, principal: Principal, message_id: UUID) -> UUID:
    """Atomically reuse a first-message thread when its acknowledgement is lost."""
    thread_id = uuid5(NAMESPACE_URL, f"urn:practicamia:first-message:{principal.subject}:{message_id}")
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        insert = pg_insert
    elif dialect == "sqlite":
        insert = sqlite_insert
    else:
        raise RuntimeError("Agent threads require PostgreSQL or SQLite")
    db.execute(
        insert(AgentThread)
        .values(id=str(thread_id), owner_subject=principal.subject, created_at=datetime.now(timezone.utc))
        .on_conflict_do_nothing(index_elements=["id"])
    )
    return thread_id


def link_case_to_thread(
    db: Session, *, principal: Principal, thread_id: UUID, case_id: UUID,
) -> bool:
    """Attach an owned case. Duplicate links succeed and foreign IDs return False."""
    target = db.execute(
        select(AgentThread.id, CaseRecord.id)
        .join(CaseRecord, CaseRecord.id == str(case_id))
        .where(
            AgentThread.id == str(thread_id),
            AgentThread.owner_subject == principal.subject,
            CaseRecord.owner_subject == principal.subject,
        )
        # Keep both rows present until the link is inserted or the caller rolls back.
        .with_for_update(read=True, of=(AgentThread, CaseRecord))
    ).one_or_none()
    if target is None:
        return False
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        insert = pg_insert
    elif dialect == "sqlite":
        insert = sqlite_insert
    else:
        raise RuntimeError("Agent thread links require PostgreSQL")
    db.execute(
        insert(AgentThreadCase)
        .values(thread_id=target[0], case_id=target[1])
        .on_conflict_do_nothing(index_elements=["thread_id", "case_id"])
    )
    return True
