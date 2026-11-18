"""Encrypted worker checkpoints for the internal Phase 4 execution path."""

from dataclasses import dataclass
import json
from os import urandom
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator
from sqlalchemy import CheckConstraint, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.agent.contract import (
    AgentEvent, ApprovalRequested, ContractModel, Identifier, PassageId,
    QuestionRequested, TERMINAL_EVENTS,
)
from app.agent.run_events import _latest_event, append_run_event
from app.agent.run_requests import ACTIVE_STATUSES, AgentRunRequest, _owned_run, _payload_cipher
from app.auth.tokens import Principal
from app.database import Base


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


class CheckpointState(ContractModel):
    schema_version: Literal[1] = 1
    next_node: Literal[
        "load_context", "identify_intent", "find_evidence", "choose_next_step", "verify_and_respond",
    ]
    procedure_candidates: list[Identifier] = Field(default_factory=list, max_length=10)
    evidence_ids: list[PassageId] = Field(default_factory=list, max_length=10)
    missing_fields: list[Identifier] = Field(default_factory=list, max_length=12)
    pending_question_id: UUID | None = None
    pending_proposal_id: UUID | None = None

    @model_validator(mode="after")
    def validate_pending_work(self):
        if self.pending_question_id is not None and self.pending_proposal_id is not None:
            raise ValueError("A checkpoint can hold one pending interaction")
        return self


@dataclass(frozen=True)
class WorkerCheckpoint:
    revision: int
    event_seq: int
    state: CheckpointState


class CheckpointConflict(ValueError):
    """The worker must reload the run before saving or resuming."""


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


def save_checkpoint(
    db: Session, *, thread_id: UUID, run_id: UUID, principal: Principal, key: bytes,
    expected_revision: int, expected_event_seq: int, state: CheckpointState,
    event: AgentEvent | None = None,
) -> WorkerCheckpoint | None:
    """Save one worker boundary and an optional event in the caller's transaction."""
    run = db.scalar(_owned_run(thread_id, run_id, principal).with_for_update(of=AgentRunRequest))
    if run is None:
        return None
    row = db.get(AgentRunCheckpoint, run.id, populate_existing=True)
    last_revision = row.revision if row else 0
    last_seq = _event_watermark(db, run)
    if run.status not in ACTIVE_STATUSES:
        raise CheckpointConflict("The run is already terminal")
    if expected_revision != last_revision or expected_event_seq != last_seq:
        raise CheckpointConflict("Checkpoint revision or event watermark changed")

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
        if isinstance(event, ApprovalRequested) and state.pending_proposal_id != event.proposal.proposal_id:
            raise CheckpointConflict("Checkpoint must reference the pending proposal")

    revision = last_revision + 1
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
