"""Encrypted worker checkpoints for the internal Phase 4 execution path."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from os import urandom
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator
from sqlalchemy import CheckConstraint, ForeignKey, Integer, LargeBinary, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.agent.approval_graph import ApprovalPause
from app.agent.case_operations import AgentCaseOperation
from app.agent.clarification_disposition import resolve_disposition
from app.agent.contract import (
    MAX_MESSAGE_GOALS, MAX_PROCEDURE_CANDIDATES,
    AgentEvent, AgentIntent, AnswerCompleted, ApprovalApplied, ApprovalRequested, ClarificationReply, ContractModel,
    GoalNumber, Identifier, MessageGoal, PassageId, PositiveInt, QuestionAnswered, QuestionRequested,
    RunFailed, RunSnapshot, RunStopped,
    TERMINAL_EVENTS,
)
from app.agent.proposal_freshness import ProposalFreshness
from app.agent.run_events import _latest_event, _read_event_at, append_run_event, read_run_snapshot
from app.agent.run_requests import ACTIVE_STATUSES, AgentRunRequest, _owned_run, _payload_cipher
from app.auth.tokens import Principal
from app.cases.intake_schemas import KnownCitizenship
from app.database import Base

RoutingField = Literal[
    "procedure", "destination", "activity_location", "move_in_date", "filing_date", "housing_basis",
    "citizenship_class",
]


class AgentRunCheckpoint(Base):
    __tablename__ = "agent_run_checkpoints"
    __table_args__ = (
        CheckConstraint("revision > 0", name="ck_agent_checkpoint_revision"),
        CheckConstraint("event_seq >= 0", name="ck_agent_checkpoint_event_seq"),
    )

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agent_run_requests.id", ondelete="CASCADE"), primary_key=True,
    )
    revision: Mapped[int] = mapped_column(Integer)
    event_seq: Mapped[int] = mapped_column(Integer)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)


class RoutingCorrections(ContractModel):
    """User-confirmed routing inputs for this run, stored with its encrypted state."""

    procedure: Identifier | None = None
    destination: Identifier | None = None
    activity_location: Identifier | None = None
    move_in_date: date | None = None
    filing_date: date | None = None
    housing_basis: Literal["registered_private_rental", "owner", "guest", "other"] | None = None
    citizenship_class: KnownCitizenship | None = None
    reply_event_seqs: dict[RoutingField, PositiveInt] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_reply_refs(self):
        if any(getattr(self, name) is None for name in self.reply_event_seqs):
            raise ValueError("A routing reply reference requires a recorded value")
        return self


class CheckpointState(ContractModel):
    schema_version: Literal[1] = 1
    next_node: Literal[
        "load_context", "identify_intent", "find_evidence", "choose_next_step", "verify_and_respond",
    ]
    intent: AgentIntent | None = None
    procedure_candidates: list[Identifier] = Field(default_factory=list, max_length=MAX_PROCEDURE_CANDIDATES)
    goals: list[MessageGoal] = Field(default_factory=list, max_length=MAX_MESSAGE_GOALS)
    preferred_goal: GoalNumber | None = None
    evidence_ids: list[PassageId] = Field(default_factory=list, max_length=10)
    routing_corrections: RoutingCorrections | None = None
    missing_fields: list[Identifier] = Field(default_factory=list, max_length=12)
    pending_question_id: UUID | None = None
    pending_proposal_id: UUID | None = None
    proposal_freshness: ProposalFreshness | None = None
    approval_pause: ApprovalPause | None = None

    @model_validator(mode="after")
    def validate_pending_work(self):
        if self.preferred_goal is not None and self.preferred_goal > len(self.goals):
            raise ValueError("The preferred goal must be one of this message's goals")
        if self.goals and (
            self.intent != "plan_multiple_tasks" or len(self.goals) < 2 or self.procedure_candidates
        ):
            raise ValueError("Multiple goals require an independent candidate set for each goal")
        if self.pending_question_id is not None and self.pending_proposal_id is not None:
            raise ValueError("A checkpoint can hold one pending interaction")
        if self.pending_proposal_id is None and (self.proposal_freshness is not None or self.approval_pause is not None):
            raise ValueError("Proposal metadata requires a pending proposal")
        return self


@dataclass(frozen=True)
class WorkerCheckpoint:
    revision: int
    event_seq: int
    state: CheckpointState


class CheckpointConflict(ValueError):
    """The worker must reload the run before saving or resuming."""


class RunRevisionConflict(ValueError):
    """The run advanced before the stop request was accepted."""


def _event_watermark(db: Session, run: AgentRunRequest) -> int:
    latest = _latest_event(db, run)
    return latest.event_seq if latest else 0


def _checkpoint_aad(
    run: AgentRunRequest, principal: Principal, *, revision: int, event_seq: int,
) -> bytes:
    return json.dumps([
        "practicamia-agent-checkpoint/v1", principal.subject, run.thread_id,
        run.id, run.case_id, revision, event_seq,
    ], separators=(",", ":")).encode()


def load_checkpoint(
    db: Session, *, thread_id: UUID, run_id: UUID, principal: Principal, key: bytes,
) -> WorkerCheckpoint | None:
    """Load owned worker state at the current persisted event boundary."""
    run = db.scalar(_owned_run(thread_id, run_id, principal).with_for_update(
        read=True, of=AgentRunRequest,
    ))
    if run is None or run.status not in ACTIVE_STATUSES:
        return None
    row = db.get(AgentRunCheckpoint, run.id, populate_existing=True)
    if row is None:
        return None
    if row.event_seq != _event_watermark(db, run):
        raise CheckpointConflict("Checkpoint and event journal require reconciliation")
    nonce, ciphertext = row.ciphertext[:12], row.ciphertext[12:]
    payload = _payload_cipher(key).decrypt(
        nonce, ciphertext,
        _checkpoint_aad(run, principal, revision=row.revision, event_seq=row.event_seq),
    )
    return WorkerCheckpoint(row.revision, row.event_seq, CheckpointState.model_validate_json(payload))


def _check_writable_checkpoint(
    db: Session, run: AgentRunRequest, *, expected_revision: int, expected_event_seq: int,
) -> tuple[AgentRunCheckpoint | None, int]:
    row = db.get(AgentRunCheckpoint, run.id, populate_existing=True)
    last_revision = row.revision if row else 0
    last_seq = _event_watermark(db, run)
    if run.status not in ACTIVE_STATUSES:
        raise CheckpointConflict("The run is already terminal")
    if expected_revision != last_revision or expected_event_seq != last_seq:
        raise CheckpointConflict("Checkpoint revision or event watermark changed")

    return row, last_seq


def save_checkpoint(
    db: Session, *, thread_id: UUID, run_id: UUID, principal: Principal, key: bytes,
    expected_revision: int, expected_event_seq: int, state: CheckpointState,
    event: AgentEvent | None = None,
) -> WorkerCheckpoint | None:
    """Save one worker boundary and an optional event in the caller's transaction."""
    run = db.scalar(_owned_run(thread_id, run_id, principal).with_for_update(of=AgentRunRequest))
    if run is None:
        return None
    row, last_seq = _check_writable_checkpoint(
        db, run, expected_revision=expected_revision, expected_event_seq=expected_event_seq,
    )
    payload = state.model_dump_json().encode()
    state = CheckpointState.model_validate_json(payload)
    if event is not None:
        if (
            event.thread_id != thread_id or event.run_id != run_id
            or event.event_seq != last_seq + 1 or event.type in TERMINAL_EVENTS
        ):
            raise CheckpointConflict("Checkpoint event must be the next nonterminal event for this run")
        if isinstance(event, QuestionRequested) and state.pending_question_id != event.question.question_id:
            raise CheckpointConflict("Checkpoint must reference the pending question")
        if isinstance(event, QuestionRequested) and event.question.goal_selection_language is not None and (
            len(event.question.options) != len(state.goals) or state.preferred_goal is not None
        ):
            raise CheckpointConflict("Task choices must match the pending goals")
        if isinstance(event, QuestionRequested) and event.question.case_goal is not None and (
            len(event.question.case_goal.options) != len(state.goals)
        ):
            raise CheckpointConflict("Saved-case selection must preserve the active goal")
        if isinstance(event, ApprovalRequested) and state.pending_proposal_id != event.proposal.proposal_id:
            raise CheckpointConflict("Checkpoint must reference the pending proposal")
        if isinstance(event, ApprovalApplied) and state.pending_proposal_id is not None:
            raise CheckpointConflict("Applied approval must clear the pending proposal")

    revision = expected_revision + 1
    event_seq = event.event_seq if event is not None else last_seq
    nonce = urandom(12)
    ciphertext = nonce + _payload_cipher(key).encrypt(
        nonce, payload, _checkpoint_aad(run, principal, revision=revision, event_seq=event_seq),
    )
    if event is not None:
        append_run_event(db, principal=principal, event=event, key=key)
    if row is None:
        row = AgentRunCheckpoint(run_id=run.id)
        db.add(row)
    row.revision = revision
    row.event_seq = event_seq
    row.ciphertext = ciphertext
    db.flush()
    return WorkerCheckpoint(revision, event_seq, state)


def submit_clarification_reply(
    db: Session, *, thread_id: UUID, run_id: UUID, question_id: UUID,
    principal: Principal, key: bytes, reply: ClarificationReply,
) -> QuestionAnswered | None:
    """Record one answer at the question boundary and make its run runnable."""
    context = {"thread_id": thread_id, "run_id": run_id, "principal": principal, "key": key}
    run = db.scalar(_owned_run(thread_id, run_id, principal).with_for_update(of=AgentRunRequest))
    if run is None:
        return None

    reply = ClarificationReply.model_validate_json(reply.model_dump_json())
    # The revision shown with the question is the sequence its reply would occupy.
    reply_seq = reply.expected_run_revision
    saved = _read_event_at(db, run, reply_seq, principal, key)
    if isinstance(saved, QuestionAnswered):
        # Text can express a disposition, but its original request used the answer channel.
        submitted_as = "answer" if saved.text is not None else saved.disposition
        if (saved.question_id, saved.client_reply_id, saved.text, submitted_as) == (
            question_id, reply.client_reply_id, reply.text, reply.disposition,
        ):
            return saved
    if saved is not None or run.status != "waiting_for_information":
        raise CheckpointConflict("The question is no longer pending at this revision")

    checkpoint = load_checkpoint(db, **context)
    if (
        checkpoint is None or checkpoint.state.pending_question_id != question_id
        or checkpoint.event_seq + 1 != reply_seq
    ):
        raise CheckpointConflict("The question is no longer pending at this revision")
    pending = _read_event_at(db, run, checkpoint.event_seq, principal, key)
    if not isinstance(pending, QuestionRequested) or pending.question.question_id != question_id:
        raise CheckpointConflict("The question is no longer pending at this revision")

    question = pending.question
    disposition = resolve_disposition(reply, question)
    selected_goal = (
        question.options.index(reply.text) + 1
        if question.goal_selection_language is not None and disposition == "answer" and reply.text in question.options
        else None
    )
    selected_case_id = next((
        choice.case_id for choice in question.case_choices
        if disposition == "answer" and choice.label == reply.text
    ), None)
    answered = QuestionAnswered(
        schema_version=1, thread_id=thread_id, run_id=run_id, event_seq=reply_seq,
        occurred_at=datetime.now(timezone.utc), type="question.answered",
        question_id=question_id, client_reply_id=reply.client_reply_id, text=reply.text,
        disposition=disposition, selected_goal=selected_goal, selected_case_id=selected_case_id,
    )
    updated = save_checkpoint(
        db, **context, expected_revision=checkpoint.revision, expected_event_seq=checkpoint.event_seq,
        state=checkpoint.state.model_copy(update={"pending_question_id": None}), event=answered,
    )
    return answered if updated is not None else None


def finish_checkpoint(
    db: Session, *, principal: Principal, key: bytes,
    expected_revision: int, expected_event_seq: int, event: AnswerCompleted | RunFailed,
) -> AnswerCompleted | RunFailed | None:
    """Finish the selected worker boundary and discard its resume state."""
    run = db.scalar(_owned_run(event.thread_id, event.run_id, principal).with_for_update(
        of=AgentRunRequest,
    ))
    if run is None:
        return None
    row, last_seq = _check_writable_checkpoint(
        db, run, expected_revision=expected_revision, expected_event_seq=expected_event_seq,
    )
    if row is None or row.event_seq != last_seq or event.event_seq != last_seq + 1:
        raise CheckpointConflict("Terminal event must follow the current checkpoint")
    appended = append_run_event(db, principal=principal, event=event, key=key)
    if not isinstance(appended, (AnswerCompleted, RunFailed)):
        raise CheckpointConflict("The run could not be finalized")
    db.delete(row)
    db.flush()
    return appended


def stop_run(
    db: Session, *, thread_id: UUID, run_id: UUID, principal: Principal, key: bytes,
    expected_run_revision: int,
) -> RunSnapshot | None:
    """Stop an owned run, retaining its committed operations and fencing its lease."""
    context = {"thread_id": thread_id, "run_id": run_id, "principal": principal, "key": key}
    run = db.scalar(_owned_run(thread_id, run_id, principal).with_for_update(of=AgentRunRequest))
    if run is None:
        return None
    if run.status not in ACTIVE_STATUSES:
        return read_run_snapshot(db, **context)

    next_event_seq = _event_watermark(db, run) + 1
    if expected_run_revision != next_event_seq:
        raise RunRevisionConflict("Run revision changed before stop")

    operation_ids = db.scalars(
        select(AgentCaseOperation.id).where(AgentCaseOperation.run_id == run.id)
        .order_by(AgentCaseOperation.case_revision.desc()).limit(20)
    ).all()
    stopped = append_run_event(
        db, principal=principal, key=key,
        event=RunStopped(
            schema_version=1, thread_id=thread_id, run_id=run_id, event_seq=next_event_seq,
            occurred_at=datetime.now(timezone.utc), type="run.stopped", committed_operation_ids=operation_ids,
        ),
    )
    if stopped is None:
        return None

    checkpoint = db.get(AgentRunCheckpoint, run.id)
    if checkpoint is not None:
        db.delete(checkpoint)
    run.lease_token = None
    run.lease_expires_at = None
    db.flush()
    return read_run_snapshot(db, **context)
