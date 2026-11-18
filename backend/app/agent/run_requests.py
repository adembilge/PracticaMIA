"""Accept and recover encrypted agent messages before worker execution."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from os import urandom
from typing import Literal
from uuid import UUID, uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index,
    Integer, LargeBinary, String, UniqueConstraint, and_, select, text,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.agent.contract import Language, SendMessage
from app.agent.threads import AgentThread, AgentThreadCase
from app.auth.tokens import Principal
from app.cases.model import CaseRecord
from app.database import Base

ACTIVE_STATUSES = ("queued", "running", "waiting_for_information", "waiting_for_approval", "stopping")
ALL_STATUSES = (*ACTIVE_STATUSES, "completed", "failed", "stopped")


class AgentRunRequest(Base):
    __tablename__ = "agent_run_requests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["thread_id", "case_id"], ["agent_thread_cases.thread_id", "agent_thread_cases.case_id"],
            ondelete="CASCADE", name="fk_agent_runs_linked_case",
        ),
        UniqueConstraint("thread_id", "client_message_id", name="uq_agent_runs_client_message"),
        CheckConstraint(f"status IN {ALL_STATUSES}", name="ck_agent_run_requests_status"),
        Index(
            "uq_agent_runs_active_thread", "thread_id", unique=True,
            postgresql_where=text(f"status IN {ACTIVE_STATUSES}"),
            sqlite_where=text(f"status IN {ACTIVE_STATUSES}"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    thread_id: Mapped[str] = mapped_column(ForeignKey("agent_threads.id", ondelete="CASCADE"))
    case_id: Mapped[str | None] = mapped_column(String(36))
    client_message_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(32))
    accepted_revision: Mapped[int] = mapped_column(Integer)
    message_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


@dataclass(frozen=True)
class RunAcceptance:
    outcome: Literal["accepted", "unavailable", "message_conflict", "stale_thread", "active_run"]
    run_id: UUID | None = None
    accepted_revision: int | None = None


@dataclass(frozen=True)
class StoredMessage:
    text: str
    language: Language
    case_id: UUID | None


def _associated_data(run: AgentRunRequest, subject: str) -> bytes:
    return json.dumps([
        "practicamia-agent-request/v1", subject, run.thread_id,
        run.id, run.client_message_id, run.case_id, run.accepted_revision,
    ], separators=(",", ":")).encode()


def _message_cipher(key: bytes) -> AESGCM:
    if len(key) != 32:
        raise ValueError("Agent messages require a 256-bit encryption key")
    return AESGCM(key)


def _decode(run: AgentRunRequest, principal: Principal, key: bytes) -> StoredMessage:
    nonce, payload = run.message_ciphertext[:12], run.message_ciphertext[12:]
    message, language = json.loads(_message_cipher(key).decrypt(
        nonce, payload, _associated_data(run, principal.subject),
    ))
    return StoredMessage(message, language, UUID(run.case_id) if run.case_id else None)


def _owned_link(thread: str, case: str, principal: Principal):
    return (
        select(CaseRecord.id)
        .join(AgentThreadCase, AgentThreadCase.case_id == CaseRecord.id)
        .where(
            AgentThreadCase.thread_id == thread,
            CaseRecord.id == case,
            CaseRecord.owner_subject == principal.subject,
        )
    )


def accept_message(
    db: Session, *, thread_id: UUID, principal: Principal, message: SendMessage, key: bytes,
) -> RunAcceptance:
    """Create an encrypted queued run within the caller's transaction."""
    thread = db.scalar(
        select(AgentThread)
        .where(AgentThread.id == str(thread_id), AgentThread.owner_subject == principal.subject)
        .execution_options(populate_existing=True)
        .with_for_update()
    )
    if thread is None:
        return RunAcceptance("unavailable")
    case_id = str(message.case_id) if message.case_id else None
    if case_id and db.scalar(
        _owned_link(thread.id, case_id, principal)
        .with_for_update(read=True, of=(CaseRecord, AgentThreadCase))
    ) is None:
        return RunAcceptance("unavailable")

    prior = db.scalar(select(AgentRunRequest).where(
        AgentRunRequest.thread_id == thread.id,
        AgentRunRequest.client_message_id == str(message.client_message_id),
    ))
    if prior:
        if _decode(prior, principal, key) != StoredMessage(message.text, message.language, message.case_id):
            return RunAcceptance("message_conflict")
        return RunAcceptance("accepted", UUID(prior.id), prior.accepted_revision)
    if message.expected_thread_revision is not None and message.expected_thread_revision != thread.revision:
        return RunAcceptance("stale_thread")
    if db.scalar(select(AgentRunRequest.id).where(
        AgentRunRequest.thread_id == thread.id,
        AgentRunRequest.status.in_(ACTIVE_STATUSES),
    )) is not None:
        return RunAcceptance("active_run")

    run = AgentRunRequest(
        id=str(uuid4()), thread_id=thread.id, case_id=case_id,
        client_message_id=str(message.client_message_id), status="queued",
        accepted_revision=thread.revision + 1, accepted_at=datetime.now(timezone.utc),
    )
    nonce = urandom(12)
    payload = json.dumps([message.text, message.language], ensure_ascii=False).encode()
    run.message_ciphertext = nonce + _message_cipher(key).encrypt(
        nonce, payload, _associated_data(run, principal.subject),
    )
    thread.revision = run.accepted_revision
    db.add(run)
    db.flush()
    return RunAcceptance("accepted", UUID(run.id), run.accepted_revision)


def read_run_message(
    db: Session, *, thread_id: UUID, run_id: UUID, principal: Principal, key: bytes,
) -> StoredMessage | None:
    """Recover a saved request only while its thread and linked case are owned."""
    run = db.scalar(
        select(AgentRunRequest)
        .join(AgentThread)
        .outerjoin(AgentThreadCase, and_(
            AgentThreadCase.thread_id == AgentRunRequest.thread_id,
            AgentThreadCase.case_id == AgentRunRequest.case_id,
        ))
        .outerjoin(CaseRecord, and_(
            CaseRecord.id == AgentThreadCase.case_id, CaseRecord.owner_subject == principal.subject,
        ))
        .where(
            AgentRunRequest.id == str(run_id),
            AgentThread.id == str(thread_id),
            AgentThread.owner_subject == principal.subject,
            AgentRunRequest.case_id.is_(None) | CaseRecord.id.is_not(None),
        )
        .execution_options(populate_existing=True)
    )
    return _decode(run, principal, key) if run else None
