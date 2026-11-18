"""Persist and replay typed agent events for owned runs."""

import json
from os import urandom
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, LargeBinary, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.agent.contract import (
    AgentEvent, AnswerCompleted, ApprovalRequested, EventPage, RunSnapshot, RunStarted,
    agent_event_adapter,
)
from app.agent.run_requests import AgentRunRequest, _owned_run, _payload_cipher
from app.auth.tokens import Principal
from app.database import Base


class AgentRunEvent(Base):
    __tablename__ = "agent_run_events"
    __table_args__ = (
        CheckConstraint("event_seq > 0", name="ck_agent_run_events_sequence"),
    )

    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_run_requests.id", ondelete="CASCADE"), primary_key=True,
    )
    event_seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)


class EventConflict(ValueError):
    """The event cannot follow the stored sequence or run state."""


_WAITING = ("waiting_for_information", "waiting_for_approval")
_RUNNING_OR_WAITING = ("running", *_WAITING)
_TRANSITIONS = {
    "run.started": (("queued",), "running"),
    "progress.updated": (_RUNNING_OR_WAITING, None),
    "question.requested": (("running",), "waiting_for_information"),
    "approval.requested": (("running",), "waiting_for_approval"),
    "answer.completed": (("running",), "completed"),
    "run.failed": ((*_RUNNING_OR_WAITING, "stopping"), "failed"),
    "run.stopped": ((*_RUNNING_OR_WAITING, "stopping"), "stopped"),
}


def _event_aad(run: AgentRunRequest, seq: int, principal: Principal) -> bytes:
    return json.dumps([
        "practicamia-agent-event/v1", principal.subject, run.thread_id, run.id, run.case_id, seq,
    ], separators=(",", ":")).encode()


def _decode_event(
    row: AgentRunEvent, run: AgentRunRequest, principal: Principal, key: bytes,
) -> AgentEvent:
    nonce, payload = row.ciphertext[:12], row.ciphertext[12:]
    raw = _payload_cipher(key).decrypt(
        nonce, payload, _event_aad(run, row.event_seq, principal),
    )
    return agent_event_adapter.validate_json(raw)


def _latest_event(db: Session, run: AgentRunRequest) -> AgentRunEvent | None:
    return db.scalar(
        select(AgentRunEvent).where(AgentRunEvent.run_id == run.id)
        .order_by(AgentRunEvent.event_seq.desc()).limit(1)
    )


def append_run_event(
    db: Session, *, principal: Principal, event: AgentEvent, key: bytes,
) -> AgentEvent | None:
    """Append one worker-produced event and advance the run in the same transaction."""
    run = db.scalar(_owned_run(event.thread_id, event.run_id, principal).with_for_update(
        of=AgentRunRequest,
    ))
    if run is None:
        return None

    payload = event.model_dump_json().encode()
    event = agent_event_adapter.validate_json(payload)
    if previous := db.get(AgentRunEvent, (run.id, event.event_seq)):
        saved = _decode_event(previous, run, principal, key)
        if saved != event:
            raise EventConflict("Event sequence is already occupied")
        return saved

    latest = _latest_event(db, run)
    last_seq = latest.event_seq if latest else 0
    if event.event_seq != last_seq + 1 or (event.event_seq == 1) != (event.type == "run.started"):
        raise EventConflict("Expected the next event in the run sequence")
    allowed, status = _TRANSITIONS[event.type]
    if run.status not in allowed:
        raise EventConflict("Event is incompatible with the run state")
    if isinstance(event, RunStarted) and str(event.client_message_id) != run.client_message_id:
        raise EventConflict("Start event must identify the accepted message")
    if isinstance(event, ApprovalRequested) and str(event.proposal.case_id) != run.case_id:
        raise EventConflict("Proposal must belong to the run's case")

    nonce = urandom(12)
    ciphertext = nonce + _payload_cipher(key).encrypt(
        nonce, payload, _event_aad(run, event.event_seq, principal),
    )
    db.add(AgentRunEvent(run_id=run.id, event_seq=event.event_seq, ciphertext=ciphertext))
    if status is not None:
        run.status = status
    db.flush()
    return event


def read_run_snapshot(
    db: Session, *, thread_id: UUID, run_id: UUID, principal: Principal, key: bytes,
) -> RunSnapshot | None:
    """Recover status, event watermark and any recorded terminal answer."""
    run = db.scalar(_owned_run(thread_id, run_id, principal).with_for_update(
        read=True, of=AgentRunRequest,
    ))
    if run is None:
        return None

    latest = _latest_event(db, run)
    result = None
    if latest and run.status == "completed":
        terminal = _decode_event(latest, run, principal, key)
        if isinstance(terminal, AnswerCompleted):
            result = terminal.result

    last_seq = latest.event_seq if latest else 0
    return RunSnapshot(
        thread_id=thread_id, run_id=run_id, status=run.status, last_event_seq=last_seq,
        run_revision=last_seq + 1, result=result,
    )


def read_run_events(
    db: Session, *, thread_id: UUID, run_id: UUID, principal: Principal,
    after_seq: int, key: bytes, limit: int = 100,
) -> EventPage | None:
    """Replay a bounded page of events after an already observed sequence."""
    run = db.scalar(_owned_run(thread_id, run_id, principal).with_for_update(
        read=True, of=AgentRunRequest,
    ))
    if run is None:
        return None

    latest = _latest_event(db, run)
    if not 0 <= after_seq <= (latest.event_seq if latest else 0) or not 1 <= limit <= 100:
        raise ValueError("Invalid event cursor or page size")

    rows = db.scalars(
        select(AgentRunEvent).where(AgentRunEvent.run_id == run.id, AgentRunEvent.event_seq > after_seq)
        .order_by(AgentRunEvent.event_seq).limit(limit + 1)
    ).all()
    events = [_decode_event(row, run, principal, key) for row in rows[:limit]]
    return EventPage(
        thread_id=thread_id, run_id=run_id, after_seq=after_seq, events=events,
        last_event_seq=events[-1].event_seq if events else after_seq,
        has_more=len(rows) > limit,
    )
