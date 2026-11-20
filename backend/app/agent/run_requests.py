"""Accept and recover encrypted agent messages before worker execution."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from os import urandom
from typing import Literal
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import Field, ValidationError, model_validator
from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index,
    Integer, LargeBinary, String, UniqueConstraint, and_, or_, select, text,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.agent.case_context import WorkerCaseContext
from app.agent.contract import (
    ActiveRunCursor, ActiveRunPage, ActiveRunSummary, AnswerCompleted, AnswerResult, ApprovalApplied,
    ApprovalDecided, ApprovalRequested, ClarifyingQuestion, ClarificationDisposition, ClarificationText,
    ContractModel, FieldValue, Identifier, Language, PositiveInt, QuestionAnswered, QuestionRequested,
    RunFailed, RunStatus, RunStopped, SendMessage, ShortText,
)
from app.agent.destination_correction import DestinationCorrection, destination_correction_name
from app.agent.threads import AgentThread, AgentThreadCase
from app.auth.tokens import Principal
from app.cases.model import CaseRecord
from app.database import Base
from app.rules.engine import PROCEDURE

WORKER_RUN_STATUSES = ("queued", "running")
FOREGROUND_STATUSES = (*WORKER_RUN_STATUSES, "waiting_for_approval", "stopping")
ACTIVE_STATUSES = (*FOREGROUND_STATUSES, "waiting_for_information")
ALL_STATUSES = (*ACTIVE_STATUSES, "completed", "failed", "stopped")
RECENT_USER_MESSAGE_LIMIT = 3
RECENT_RUN_SCAN_LIMIT = 24
MAX_HISTORY_EVENT_SCAN = 256


class AgentRunRequest(Base):
    __tablename__ = "agent_run_requests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["thread_id", "case_id"], ["agent_thread_cases.thread_id", "agent_thread_cases.case_id"],
            ondelete="CASCADE", name="fk_agent_runs_linked_case",
        ),
        UniqueConstraint("thread_id", "client_message_id", name="uq_agent_runs_client_message"),
        CheckConstraint(f"status IN {ALL_STATUSES}", name="ck_agent_run_requests_status"),
        CheckConstraint(
            "(lease_token IS NULL) = (lease_expires_at IS NULL)", name="ck_agent_worker_lease_pair",
        ),
        Index(
            "ix_agent_worker_queue", "accepted_at", "id",
            postgresql_where=text(f"status IN {WORKER_RUN_STATUSES}"),
            sqlite_where=text(f"status IN {WORKER_RUN_STATUSES}"),
        ),
        Index(
            "uq_agent_runs_foreground_thread", "thread_id", unique=True,
            postgresql_where=text(f"status IN {FOREGROUND_STATUSES}"),
            sqlite_where=text(f"status IN {FOREGROUND_STATUSES}"),
        ),
        Index(
            "uq_agent_runs_active_thread_case", "thread_id", text("coalesce(case_id, '')"), unique=True,
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
    lease_token: Mapped[str | None] = mapped_column(String(36))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


@dataclass(frozen=True)
class RunAcceptance:
    outcome: Literal["accepted", "unavailable", "message_conflict", "stale_thread", "active_run"]
    run_id: UUID | None = None
    accepted_revision: int | None = None


class ConversationClarification(ContractModel):
    question_id: UUID
    question_text: ShortText
    disposition: ClarificationDisposition
    reply_text: ClarificationText | None


class ConversationApproval(ContractModel):
    """A proposal and its recorded decision; only an applied event proves a case write."""

    proposal_id: UUID
    field_id: Identifier
    proposed_value: FieldValue
    decision: Literal["accept", "correct", "reject", "cancel"] | None = None
    corrected_value: FieldValue | None = None
    applied_operation_id: UUID | None = None
    applied_case_revision: PositiveInt | None = None

    @model_validator(mode="after")
    def validate_receipt(self):
        if (self.applied_operation_id is None) != (self.applied_case_revision is None):
            raise ValueError("An applied operation requires its committed case revision")
        if self.applied_operation_id is not None and self.decision != "accept":
            raise ValueError("Only an accepted proposal may have a committed receipt")
        if self.corrected_value is not None and self.decision != "correct":
            raise ValueError("Only a correction decision carries the requested replacement value")
        return self


class ConversationTurn(ContractModel):
    run_id: UUID
    case_id: UUID | None
    status: RunStatus
    accepted_revision: PositiveInt
    user_message: str
    language: Language
    answer: AnswerResult | None = None
    clarifications: list[ConversationClarification] = Field(default_factory=list)
    approvals: list[ConversationApproval] = Field(default_factory=list)
    clarification_history_truncated: bool = False
    approval_history_truncated: bool = False
    terminal_event: RunFailed | RunStopped | None = None


class ConversationHistoryPage(ContractModel):
    thread_id: UUID
    items: list[ConversationTurn]
    next_before_revision: PositiveInt | None = None


@dataclass(frozen=True)
class RecentUserMessage:
    text: str
    language: Language
    origin: Literal["user_entered"] = field(default="user_entered", init=False)


@dataclass(frozen=True)
class StoredMessage:
    text: str
    language: Language
    case_id: UUID | None
    clarification_reply: QuestionAnswered | None = None
    recent_user_messages: tuple[RecentUserMessage, ...] = ()
    case_context: WorkerCaseContext | None = None
    clarification_question: ClarifyingQuestion | None = None
    approval_applied: ApprovalApplied | None = None
    destination_correction: DestinationCorrection | None = field(default=None, compare=False)
    accepted_revision: int | None = field(default=None, compare=False)
    origin: Literal["user_entered"] = field(default="user_entered", init=False)

    @property
    def corrects_destination(self) -> bool:
        return self.destination_correction is not None and self.destination_correction.revision == self.accepted_revision


def _associated_data(run: AgentRunRequest, subject: str) -> bytes:
    return json.dumps([
        "practicamia-agent-request/v1", subject, run.thread_id,
        run.id, run.client_message_id, run.case_id, run.accepted_revision,
    ], separators=(",", ":")).encode()


def _payload_cipher(key: bytes) -> AESGCM:
    if len(key) != 32:
        raise ValueError("Agent payloads require a 256-bit encryption key")
    return AESGCM(key)


def _decode(run: AgentRunRequest, principal: Principal, key: bytes) -> StoredMessage:
    nonce, payload = run.message_ciphertext[:12], run.message_ciphertext[12:]
    message, language, *metadata = json.loads(_payload_cipher(key).decrypt(
        nonce, payload, _associated_data(run, principal.subject),
    ))
    correction = None
    if metadata:
        revision, timestamp = metadata[0]
        correction = DestinationCorrection(revision, datetime.fromisoformat(timestamp))
    return StoredMessage(
        message, language, UUID(run.case_id) if run.case_id else None,
        destination_correction=correction, accepted_revision=run.accepted_revision,
    )


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


def lock_owned_thread(db: Session, thread_id: UUID, principal: Principal) -> AgentThread | None:
    """Serialize new runs and resumed replies in the same conversation."""
    return db.scalar(
        select(AgentThread)
        .where(AgentThread.id == str(thread_id), AgentThread.owner_subject == principal.subject)
        .execution_options(populate_existing=True)
        .with_for_update(key_share=True)
    )


def accept_message(
    db: Session, *, thread_id: UUID, principal: Principal, message: SendMessage, key: bytes,
) -> RunAcceptance:
    """Create an encrypted queued run within the caller's transaction."""
    thread = lock_owned_thread(db, thread_id, principal)
    if thread is None:
        return RunAcceptance("unavailable")
    case_id = str(message.case_id) if message.case_id else None
    case_link = None
    if case_id:
        case_link = db.execute(
            _owned_link(thread.id, case_id, principal).add_columns(CaseRecord.archived_at, CaseRecord.procedure)
            .with_for_update(read=True, of=(CaseRecord, AgentThreadCase))
        ).one_or_none()
        if case_link is None:
            return RunAcceptance("unavailable")

    prior = db.scalar(select(AgentRunRequest).where(
        AgentRunRequest.thread_id == thread.id,
        AgentRunRequest.client_message_id == str(message.client_message_id),
    ))
    if prior:
        if _decode(prior, principal, key) != StoredMessage(message.text, message.language, message.case_id):
            return RunAcceptance("message_conflict")
        return RunAcceptance("accepted", UUID(prior.id), prior.accepted_revision)
    if case_link is not None and case_link.archived_at is not None:
        return RunAcceptance("unavailable")
    if message.expected_thread_revision is not None and message.expected_thread_revision != thread.revision:
        return RunAcceptance("stale_thread")
    if db.scalar(select(AgentRunRequest.id).where(
        AgentRunRequest.thread_id == thread.id,
        AgentRunRequest.status.in_(ACTIVE_STATUSES),
        or_(
            case_id is None,
            AgentRunRequest.case_id == case_id,
            AgentRunRequest.status.in_(FOREGROUND_STATUSES),
        ),
    )) is not None:
        return RunAcceptance("active_run")

    run = AgentRunRequest(
        id=str(uuid4()), thread_id=thread.id, case_id=case_id,
        client_message_id=str(message.client_message_id), status="queued",
        accepted_revision=thread.revision + 1, accepted_at=datetime.now(timezone.utc),
    )
    payload_fields = [message.text, message.language]
    if case_link is not None and case_link.procedure == PROCEDURE:
        if destination_correction_name(message.text, message.language):
            correction = DestinationCorrection(run.accepted_revision, run.accepted_at)
        else:
            correction = latest_destination_correction(db, thread_id=thread.id, case_id=case_id, principal=principal, key=key)
        if correction is not None:
            payload_fields.append([correction.revision, correction.accepted_at.isoformat()])
    nonce = urandom(12)
    payload = json.dumps(payload_fields, ensure_ascii=False).encode()
    run.message_ciphertext = nonce + _payload_cipher(key).encrypt(
        nonce, payload, _associated_data(run, principal.subject),
    )
    thread.revision = run.accepted_revision
    db.add(run)
    db.flush()
    return RunAcceptance("accepted", UUID(run.id), run.accepted_revision)


def _owned_runs(principal: Principal):
    return (
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
            AgentThread.owner_subject == principal.subject,
            AgentRunRequest.case_id.is_(None) | CaseRecord.id.is_not(None),
        )
        .execution_options(populate_existing=True)
    )


def _owned_run(thread_id: UUID, run_id: UUID, principal: Principal):
    return _owned_runs(principal).where(
        AgentRunRequest.id == str(run_id), AgentRunRequest.thread_id == str(thread_id),
    )


def latest_destination_correction(
    db: Session, *, thread_id: str, case_id: str, principal: Principal, key: bytes,
) -> DestinationCorrection | None:
    """Read the propagated correction from the newest owned request for this linked case."""
    run = db.scalar(_owned_runs(principal).where(
        AgentRunRequest.thread_id == thread_id, AgentRunRequest.case_id == case_id,
    ).order_by(AgentRunRequest.accepted_revision.desc()).limit(1))
    return _decode(run, principal, key).destination_correction if run is not None else None


def _list_run_summaries(
    db: Session, *, principal: Principal, limit: int,
    before: ActiveRunCursor | None, active_only: bool,
) -> ActiveRunPage:
    if not 1 <= limit <= 50:
        raise ValueError("Invalid run page size")
    query = _owned_runs(principal).with_only_columns(
        AgentRunRequest.id, AgentRunRequest.thread_id, AgentRunRequest.case_id,
        AgentRunRequest.status, AgentRunRequest.accepted_at,
    )
    if active_only:
        query = query.where(AgentRunRequest.status.in_(ACTIVE_STATUSES))
    if before is not None:
        accepted_at = before.accepted_at
        query = query.where(
            (AgentRunRequest.accepted_at < accepted_at) | and_(
                AgentRunRequest.accepted_at == accepted_at, AgentRunRequest.id < str(before.run_id),
            ),
        )
    rows = db.execute(query.order_by(
        AgentRunRequest.accepted_at.desc(), AgentRunRequest.id.desc(),
    ).limit(limit + 1)).all()
    items = [
        ActiveRunSummary(
            run_id=row.id, thread_id=row.thread_id, case_id=row.case_id, status=row.status,
            accepted_at=row.accepted_at if row.accepted_at.tzinfo else row.accepted_at.replace(tzinfo=timezone.utc),
        )
        for row in rows[:limit]
    ]
    cursor = None
    if len(rows) > limit:
        last = items[-1]
        cursor = ActiveRunCursor(accepted_at=last.accepted_at, run_id=last.run_id)
    return ActiveRunPage(items=items, next_cursor=cursor)


def list_active_runs(
    db: Session, *, principal: Principal, limit: int = 20, before: ActiveRunCursor | None = None,
) -> ActiveRunPage:
    """Discover owned active runs without loading message or event payloads."""
    return _list_run_summaries(db, principal=principal, limit=limit, before=before, active_only=True)


def list_recent_runs(
    db: Session, *, principal: Principal, limit: int = 20, before: ActiveRunCursor | None = None,
) -> ActiveRunPage:
    """Discover owned active and terminal runs with the same safe metadata cursor."""
    return _list_run_summaries(db, principal=principal, limit=limit, before=before, active_only=False)


def list_thread_history(
    db: Session, *, thread_id: UUID, principal: Principal, key: bytes,
    limit: int = 20, before_revision: int | None = None,
) -> ConversationHistoryPage | None:
    """Project saved chat questions, approvals and terminal outcomes.

    An accepted proposal is not a saved case write without approval.applied.
    Failures and stops come from the exact terminal event, not a guessed
    status or a truncated scan. The encrypted journal remains authoritative.
    """
    if not 1 <= limit <= 30:
        raise ValueError("Invalid conversation history page size")
    if before_revision is not None and before_revision < 1:
        raise ValueError("Invalid thread revision cursor")
    if db.scalar(select(AgentThread.id).where(
        AgentThread.id == str(thread_id), AgentThread.owner_subject == principal.subject,
    )) is None:
        return None

    query = _owned_runs(principal).where(AgentRunRequest.thread_id == str(thread_id))
    if before_revision is not None:
        query = query.where(AgentRunRequest.accepted_revision < before_revision)
    rows = db.scalars(query.order_by(
        AgentRunRequest.accepted_revision.desc(),
    ).limit(limit + 1)).all()
    from app.agent.run_events import AgentRunEvent, _decode_event, _latest_event

    turns = []
    for run in rows[:limit]:
        message = _decode(run, principal, key)
        answer = None
        terminal_event = None
        if run.status in ("completed", "failed", "stopped"):
            final = _latest_event(db, run)
            event = _decode_event(final, run, principal, key) if final is not None else None
            if run.status == "completed" and isinstance(event, AnswerCompleted):
                answer = event.result
            elif run.status == "failed" and isinstance(event, RunFailed):
                terminal_event = event
            elif run.status == "stopped" and isinstance(event, RunStopped):
                terminal_event = event
            else:
                raise ValueError("Terminal run is missing its matching final event")

        stored_events = db.scalars(
            select(AgentRunEvent)
            .where(AgentRunEvent.run_id == run.id)
            .order_by(AgentRunEvent.event_seq)
            .limit(MAX_HISTORY_EVENT_SCAN + 1)
        ).all()
        truncated = len(stored_events) > MAX_HISTORY_EVENT_SCAN
        questions: dict[UUID, str] = {}
        clarifications: list[ConversationClarification] = []
        approvals: list[ConversationApproval] = []
        approval_indexes: dict[UUID, int] = {}
        for saved_event in stored_events[:MAX_HISTORY_EVENT_SCAN]:
            parsed_event = _decode_event(saved_event, run, principal, key)
            if isinstance(parsed_event, QuestionRequested):
                questions[parsed_event.question.question_id] = parsed_event.question.text
            elif isinstance(parsed_event, QuestionAnswered):
                question_text = questions.pop(parsed_event.question_id, None)
                if question_text is not None:
                    clarifications.append(ConversationClarification(
                        question_id=parsed_event.question_id,
                        question_text=question_text,
                        disposition=parsed_event.disposition,
                        reply_text=parsed_event.text,
                    ))
            elif isinstance(parsed_event, ApprovalRequested):
                proposal = parsed_event.proposal
                approval_indexes[proposal.proposal_id] = len(approvals)
                approvals.append(ConversationApproval(
                    proposal_id=proposal.proposal_id, field_id=proposal.field_id,
                    proposed_value=proposal.proposed_value,
                ))
            elif isinstance(parsed_event, ApprovalDecided):
                index = approval_indexes.get(parsed_event.proposal_id)
                if index is not None:
                    previous = approvals[index]
                    approvals[index] = ConversationApproval.model_validate({
                        **previous.model_dump(),
                        "decision": parsed_event.decision.decision,
                        "corrected_value": parsed_event.decision.corrected_value,
                    })
            elif isinstance(parsed_event, ApprovalApplied):
                index = approval_indexes.get(parsed_event.proposal_id)
                if index is not None:
                    previous = approvals[index]
                    approvals[index] = ConversationApproval.model_validate({
                        **previous.model_dump(),
                        "applied_operation_id": parsed_event.operation_id,
                        "applied_case_revision": parsed_event.case_revision,
                    })
        turns.append(ConversationTurn(
            run_id=UUID(run.id), case_id=UUID(run.case_id) if run.case_id else None,
            status=run.status, accepted_revision=run.accepted_revision,
            user_message=message.text, language=message.language, answer=answer,
            clarifications=clarifications, approvals=approvals,
            clarification_history_truncated=truncated, approval_history_truncated=truncated,
            terminal_event=terminal_event,
        ))
    next_cursor = turns[-1].accepted_revision if len(rows) > limit else None
    return ConversationHistoryPage(
        thread_id=thread_id, items=list(reversed(turns)), next_before_revision=next_cursor,
    )


def read_run_message(
    db: Session, *, thread_id: UUID, run_id: UUID, principal: Principal, key: bytes,
) -> StoredMessage | None:
    """Recover a saved request only while its thread and linked case are owned."""
    run = db.scalar(_owned_run(thread_id, run_id, principal))
    return _decode(run, principal, key) if run else None


def read_recent_user_messages(
    db: Session, *, run: AgentRunRequest, principal: Principal, key: bytes,
) -> tuple[RecentUserMessage, ...]:
    """Read same-case messages since the last explicit topic change."""
    from app.agent.run_events import _decode_event, _latest_event

    rows = db.scalars(
        _owned_runs(principal)
        .where(
            AgentRunRequest.thread_id == run.thread_id,
            AgentRunRequest.accepted_revision < run.accepted_revision,
            AgentRunRequest.status == "completed",
        )
        .order_by(AgentRunRequest.accepted_revision.desc())
        .limit(RECENT_RUN_SCAN_LIMIT)
    ).all()
    history = []
    for row in rows:
        terminal = _latest_event(db, row)
        try:
            event = _decode_event(terminal, row, principal, key) if terminal else None
        except (InvalidTag, ValidationError):
            # An unreadable result may mark a topic change.
            break
        if not isinstance(event, AnswerCompleted):
            break
        if event.result.next_action and event.result.next_action.operation == "start_new_topic":
            break
        if row.case_id != run.case_id:
            continue
        try:
            message = _decode(row, principal, key)
        except InvalidTag:
            # An unavailable historical message must never supply context.
            continue
        history.append(RecentUserMessage(text=message.text, language=message.language))
        if len(history) == RECENT_USER_MESSAGE_LIMIT:
            break
    return tuple(reversed(history))
