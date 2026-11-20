"""Resume an owned approval interrupt, then apply it at a separate durable boundary."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.agent.approval_graph import resume_approval
from app.agent.checkpoints import CheckpointConflict, finish_checkpoint, load_checkpoint, save_checkpoint
from app.agent.contract import ApprovalApplied, ApprovalDecided, RunFailed, RunSnapshot
from app.agent.diagnostics import AgentFailureDiagnostic
from app.agent.run_events import _read_event_at, read_run_snapshot
from app.agent.run_requests import AgentRunRequest, _owned_run
from app.agent.tool_contract import ApplyApprovedUpdate
from app.agent.tool_execution import RecordedToolApproval, ToolExecutionDenied
from app.agent.tool_writes import (
    CaseWriter, lock_case_for_update, persist_approved_case_update, prepare_approved_case_update,
)
from app.agent.worker_leases import require_worker_lease
from app.auth.tokens import Principal


@dataclass(frozen=True)
class ApprovedCaseUpdates:
    """Trusted revision reader and writer for the explicitly configured case store."""

    read_revision: Callable[[Session, UUID], int | None]
    write_case: CaseWriter


def resume_approved_case_update(
    sessions: sessionmaker[Session], *, thread_id: UUID, run_id: UUID, principal: Principal, key: bytes,
    updates: ApprovedCaseUpdates, acceptance: ApprovalDecided,
) -> RunSnapshot | None:
    """Run a bounded approval step. Return None for runs outside its waiting state."""
    context = {"thread_id": thread_id, "run_id": run_id, "principal": principal, "key": key}
    diagnostic = None
    with sessions.begin() as db:
        owned_run = _owned_run(thread_id, run_id, principal)
        linked_case = db.scalar(owned_run.with_only_columns(AgentRunRequest.case_id).where(
            AgentRunRequest.status == "waiting_for_approval",
        ))
        if linked_case is None:
            return None

        case_id = UUID(linked_case)
        lock_case_for_update(db, case_id, principal)
        run = db.scalar(owned_run.with_for_update(of=AgentRunRequest))
        if run is None:
            return None
        if run.status != "waiting_for_approval":
            return read_run_snapshot(db, **context)
        require_worker_lease(db, run, None)
        checkpoint = load_checkpoint(db, **context)
        if checkpoint is None:
            raise CheckpointConflict("Waiting approval requires a checkpoint")
        accepted = _read_event_at(db, run, checkpoint.event_seq, principal, key)
        pause = checkpoint.state.approval_pause
        if (
            pause is None or accepted != acceptance or not isinstance(accepted, ApprovalDecided)
            or accepted.decision.decision != "accept"
        ):
            return read_run_snapshot(db, **context)
        if accepted.proposal_id != checkpoint.state.pending_proposal_id:
            raise CheckpointConflict("Acceptance must match the pending proposal")

        # The graph may replay its interrupt node. It performs no case writes.
        resume_approval(pause, accepted)
        call = ApplyApprovedUpdate(
            tool="apply_approved_update", case_id=case_id, proposal_id=accepted.proposal_id,
            expected_case_revision=accepted.decision.expected_case_revision,
            client_operation_id=accepted.proposal_id,
        )

        def read_approval(session: Session, requested_run_id: UUID, proposal_id: UUID) -> RecordedToolApproval | None:
            if (requested_run_id, proposal_id) != (run_id, accepted.proposal_id):
                return None
            revision = updates.read_revision(session, case_id)
            if revision is None:
                return None
            return RecordedToolApproval(
                actor_subject=principal.subject, thread_id=thread_id, run_id=run_id, case_id=case_id,
                proposal_event_seq=accepted.proposal_event_seq, proposal_id=proposal_id,
                decision=accepted.decision, current_case_revision=revision,
            )

        boundary = {"expected_revision": checkpoint.revision, "expected_event_seq": checkpoint.event_seq}
        envelope = {
            "schema_version": 1, "thread_id": thread_id, "run_id": run_id,
            "event_seq": checkpoint.event_seq + 1, "occurred_at": datetime.now(timezone.utc),
        }
        try:
            ready = prepare_approved_case_update(db, **context, call=call, read_approval=read_approval)
        except ToolExecutionDenied:
            freshness = checkpoint.state.proposal_freshness
            versions = tuple(sorted({
                UUID(passage.split(":")[0]) for passage in freshness.passage_ids
            })) if freshness is not None else ()
            diagnostic = AgentFailureDiagnostic(
                code="proposal_outdated", stage="resume_approval", intent=checkpoint.state.intent,
                tool=call.tool, source_version_ids=versions,
            )
            finish_checkpoint(
                db, principal=principal, key=key, **boundary,
                event=RunFailed(
                    **envelope, type="run.failed", code="proposal_outdated", retryable=False, recovery="review_proposal",
                ),
            )
        else:
            receipt = persist_approved_case_update(
                db, run_id=run_id, call=call, ready=ready, write_case=updates.write_case,
            )
            save_checkpoint(
                db, **context, **boundary,
                state=checkpoint.state.model_copy(update={
                    "pending_proposal_id": None, "proposal_freshness": None, "approval_pause": None,
                }),
                event=ApprovalApplied(
                    **envelope, type="approval.applied", proposal_id=receipt.proposal_id,
                    operation_id=receipt.operation_id, case_revision=receipt.case_revision,
                ),
            )
        snapshot = read_run_snapshot(db, **context)
    if diagnostic is not None:
        diagnostic.emit()
    return snapshot
