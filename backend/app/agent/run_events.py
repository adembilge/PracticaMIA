"""Persist and replay typed agent events for owned runs."""

import json
from os import urandom
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, LargeBinary, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.agent.case_operations import AgentCaseOperation
from app.agent.contract import (
    AgentEvent, AnswerCompleted, ApprovalApplied, ApprovalDecided, ApprovalRequested, EventPage, GoalSelection,
    QuestionAnswered, QuestionRequested,
    RunSnapshot, RunStarted, agent_event_adapter, valid_event_position,
)
from app.agent.run_requests import ACTIVE_STATUSES, AgentRunRequest, _owned_run, _payload_cipher
from app.auth.tokens import Principal
from app.database import Base
from app.private_documents.intelligence import normalize_labeled_move_date


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


class InvalidEventCursor(ValueError):
    """The requested event page is outside the reconnect bounds."""


class InvalidClarificationReply(ValueError):
    """The reply does not match the saved question’s answer shape."""


_WAITING = ("waiting_for_information", "waiting_for_approval")
_RUNNING_OR_WAITING = ("running", *_WAITING)
_TRANSITIONS = {
    "run.started": (("queued",), "running"),
    "progress.updated": (_RUNNING_OR_WAITING, None),
    "question.requested": (("running",), "waiting_for_information"),
    "question.answered": (("waiting_for_information",), "running"),
    "approval.requested": (("running",), "waiting_for_approval"),
    "approval.decided": (("waiting_for_approval",), None),
    "approval.applied": (("waiting_for_approval",), "running"),
    "answer.completed": (("running",), "completed"),
    "run.failed": ((*_RUNNING_OR_WAITING, "stopping"), "failed"),
    "run.stopped": (ACTIVE_STATUSES, "stopped"),
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


def _read_event_at(
    db: Session, run: AgentRunRequest, seq: int, principal: Principal, key: bytes,
) -> AgentEvent | None:
    row = db.get(AgentRunEvent, (run.id, seq))
    return _decode_event(row, run, principal, key) if row else None


def _latest_event(db: Session, run: AgentRunRequest) -> AgentRunEvent | None:
    return db.scalar(
        select(AgentRunEvent).where(AgentRunEvent.run_id == run.id)
        .order_by(AgentRunEvent.event_seq.desc()).limit(1)
    )


def append_run_event(
    db: Session, *, principal: Principal, event: AgentEvent, key: bytes,
) -> AgentEvent | None:
    """Append one event and advance the run in the same transaction."""
    run = db.scalar(_owned_run(event.thread_id, event.run_id, principal).with_for_update(
        of=AgentRunRequest,
    ))
    if run is None:
        return None

    payload = event.model_dump_json().encode()
    event = agent_event_adapter.validate_json(payload)
    if saved := _read_event_at(db, run, event.event_seq, principal, key):
        if saved != event:
            raise EventConflict("Event sequence is already occupied")
        return saved

    latest = _latest_event(db, run)
    last_seq = latest.event_seq if latest else 0
    if event.event_seq != last_seq + 1 or not valid_event_position(event):
        raise EventConflict("Expected the next event in the run sequence")
    allowed, status = _TRANSITIONS[event.type]
    if run.status not in allowed or (event.event_seq == 1 and run.status != "queued"):
        raise EventConflict("Event is incompatible with the run state")
    if isinstance(event, RunStarted) and str(event.client_message_id) != run.client_message_id:
        raise EventConflict("Start event must identify the accepted message")
    if isinstance(event, ApprovalRequested) and str(event.proposal.case_id) != run.case_id:
        raise EventConflict("Proposal must belong to the run's case")
    if isinstance(event, ApprovalDecided):
        pending = _decode_event(latest, run, principal, key) if latest else None
        if (
            not isinstance(pending, ApprovalRequested)
            or (pending.event_seq, pending.proposal.proposal_id) != (event.proposal_event_seq, event.proposal_id)
            or pending.proposal.expected_case_revision != event.decision.expected_case_revision
            or str(pending.proposal.case_id) != run.case_id
        ):
            raise EventConflict("Decision must identify the pending proposal")
        if event.decision.decision == "correct":
            status = "running"
    if isinstance(event, ApprovalApplied):
        accepted = _decode_event(latest, run, principal, key) if latest else None
        receipt = db.get(AgentCaseOperation, str(event.operation_id))
        if (
            not isinstance(accepted, ApprovalDecided) or accepted.decision.decision != "accept"
            or accepted.proposal_id != event.proposal_id or receipt is None
            or receipt.expected_case_revision != accepted.decision.expected_case_revision
            or (receipt.run_id, receipt.case_id, receipt.proposal_id, receipt.case_revision)
            != (run.id, run.case_id, str(event.proposal_id), event.case_revision)
        ):
            raise EventConflict("Applied approval must follow its decision and saved case receipt")
    if isinstance(event, AnswerCompleted):
        result = event.result
        if result.verification_status == "verified" and not result.claims:
            raise EventConflict("A verified answer requires evidence-linked claims")
        if result.official_channel and not any(claim.kind == "channel" for claim in result.claims):
            raise EventConflict("An official channel requires an evidence-linked channel claim")
        if result.document_observations and run.case_id is None:
            raise EventConflict("Document observations require a linked case")

    if isinstance(event, QuestionAnswered):
        pending = _decode_event(latest, run, principal, key) if latest else None
        if not isinstance(pending, QuestionRequested) or pending.question.question_id != event.question_id:
            raise EventConflict("Reply must identify the pending question")
        question = pending.question
        if event.disposition == "answer":
            if question.answer_shape == "single_choice" and event.text not in question.options:
                raise InvalidClarificationReply(question.reply_hint or "Select one of the offered choices.")
            if question.answer_format == "calendar_date" and normalize_labeled_move_date(event.text) is None:
                raise InvalidClarificationReply(
                    question.reply_hint or "Enter a valid date between 1900 and 2100 in YYYY-MM-DD or DD/MM/YYYY format."
                )
        selected_goal = (
            question.options.index(event.text) + 1
            if question.goal_selection_language is not None and event.disposition == "answer"
            else None
        )
        if event.selected_goal != selected_goal:
            raise EventConflict("The selected task must match the recorded option")

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
    """Recover status and the proposal or answer at the current event boundary."""
    run = db.scalar(_owned_run(thread_id, run_id, principal).with_for_update(
        read=True, of=AgentRunRequest,
    ))
    if run is None:
        return None

    latest = _latest_event(db, run)
    result = None
    pending_proposal = None
    approval_recorded = False
    goal_selection = None
    if latest and run.status in ("completed", "waiting_for_approval", "running"):
        current = _decode_event(latest, run, principal, key)
        if isinstance(current, AnswerCompleted) and run.status == "completed":
            result = current.result
            goal_selection = result.goal_selection
        if isinstance(current, ApprovalRequested) and run.status == "waiting_for_approval":
            pending_proposal = current.proposal
        if isinstance(current, ApprovalDecided) and run.status == "waiting_for_approval":
            approval_recorded = current.decision.decision == "accept"
        if isinstance(current, QuestionAnswered) and current.selected_goal is not None:
            asked = _read_event_at(db, run, current.event_seq - 1, principal, key)
            if isinstance(asked, QuestionRequested) and asked.question.goal_selection_language is not None:
                goal_selection = GoalSelection(
                    language=asked.question.goal_selection_language, options=asked.question.options,
                    active_goal=current.selected_goal,
                )

    last_seq = latest.event_seq if latest else 0
    return RunSnapshot(
        thread_id=thread_id, run_id=run_id, status=run.status, last_event_seq=last_seq,
        run_revision=last_seq + 1, result=result, pending_proposal=pending_proposal,
        approval_recorded=approval_recorded, goal_selection=goal_selection,
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
        raise InvalidEventCursor("Invalid event cursor or page size")

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
