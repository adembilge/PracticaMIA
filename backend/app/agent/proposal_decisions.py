"""Record an owner's decision at the encrypted proposal boundary."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.agent.approval_graph import pause_for_approval
from app.agent.checkpoints import CheckpointConflict, load_checkpoint, save_checkpoint, stop_run
from app.agent.contract import (
    ApprovalDecided, ApprovalProposal, ApprovalRequested, FieldValue, ProposalDecision, SubmitProposalDecision,
)
from app.agent.run_events import _read_event_at, append_run_event
from app.agent.run_requests import AgentRunRequest, _owned_run, read_run_message
from app.auth.tokens import Principal
from app.cases.intake_schemas import IntakeFacts


class ProposalDecisionConflict(ValueError):
    """The decision no longer refers to the current review boundary."""


class InvalidProposalValue(ValueError):
    """The proposed value cannot be accepted for this field."""


def _validate_proposed_value(proposal: ApprovalProposal, value: FieldValue) -> None:
    if proposal.field_id in IntakeFacts.model_fields:
        try:
            IntakeFacts.model_validate({proposal.field_id: value})
        except ValidationError:
            raise InvalidProposalValue() from None
    # The other supported case-update shape is a checklist review flag.
    elif type(proposal.proposed_value) is not bool or type(value) is not bool:
        raise InvalidProposalValue()


def submit_proposal_decision(
    db: Session, *, thread_id: UUID, run_id: UUID, proposal_id: UUID, principal: Principal,
    key: bytes, payload: SubmitProposalDecision,
) -> ApprovalDecided | None:
    """Persist review only. The separate case writer consumes a valid acceptance."""
    context = {"thread_id": thread_id, "run_id": run_id, "principal": principal, "key": key}
    run = db.scalar(_owned_run(thread_id, run_id, principal).with_for_update(of=AgentRunRequest))
    if run is None:
        return None

    seq = payload.expected_run_revision
    decision = ProposalDecision.model_validate(payload.model_dump(exclude={"expected_run_revision"}))
    saved = _read_event_at(db, run, seq, principal, key)
    if isinstance(saved, ApprovalDecided) and (saved.proposal_id, saved.decision) == (proposal_id, decision):
        return saved
    if saved is not None or run.status != "waiting_for_approval":
        raise ProposalDecisionConflict()
    try:
        checkpoint = load_checkpoint(db, **context)
    except CheckpointConflict:
        raise ProposalDecisionConflict() from None
    if checkpoint is None or checkpoint.event_seq + 1 != seq or checkpoint.state.pending_proposal_id != proposal_id:
        raise ProposalDecisionConflict()
    pending = _read_event_at(db, run, checkpoint.event_seq, principal, key)
    if (
        not isinstance(pending, ApprovalRequested)
        or pending.proposal.proposal_id != proposal_id
        or str(pending.proposal.case_id) != run.case_id
        or pending.proposal.expected_case_revision != decision.expected_case_revision
    ):
        raise ProposalDecisionConflict()

    now = datetime.now(timezone.utc)
    proposal = pending.proposal
    replacement = None
    if decision.decision in ("accept", "correct"):
        if proposal.expires_at <= now:
            raise ProposalDecisionConflict()
        value = proposal.proposed_value if decision.corrected_value is None else decision.corrected_value
        _validate_proposed_value(proposal, value)
        if decision.decision == "correct":
            message = read_run_message(db, **context)
            if message is None:
                return None
            rationale = (
                "Review the value corrected by the user."
                if message.language == "en" else "Esamina il valore corretto dall’utente."
            )
            replacement = proposal.model_copy(update={
                "proposal_id": uuid4(), "proposed_value": value, "rationale": rationale,
            })

    envelope = {"schema_version": 1, "thread_id": thread_id, "run_id": run_id, "occurred_at": now}
    event = ApprovalDecided(
        **envelope, event_seq=seq, type="approval.decided", proposal_id=proposal_id,
        proposal_event_seq=checkpoint.event_seq, decision=decision,
    )
    if decision.decision in ("reject", "cancel"):
        if append_run_event(db, principal=principal, key=key, event=event) is None:
            raise ProposalDecisionConflict()
        if stop_run(db, **context, expected_run_revision=seq + 1) is None:
            raise ProposalDecisionConflict()
        return event

    saved_checkpoint = save_checkpoint(
        db, **context, expected_revision=checkpoint.revision, expected_event_seq=checkpoint.event_seq,
        state=checkpoint.state, event=event,
    )
    if saved_checkpoint is None:
        raise ProposalDecisionConflict()
    if replacement is not None:
        approval_pause = (
            pause_for_approval(thread_id, run_id, replacement.proposal_id)
            if checkpoint.state.approval_pause is not None else None
        )
        save_checkpoint(
            db, **context, expected_revision=saved_checkpoint.revision, expected_event_seq=seq,
            state=checkpoint.state.model_copy(update={
                "pending_proposal_id": replacement.proposal_id, "approval_pause": approval_pause,
            }),
            event=ApprovalRequested(
                **envelope, event_seq=seq + 1, type="approval.requested", proposal=replacement,
                requires_recorded_decision=True,
            ),
        )
    return event
