"""Server-side preconditions for phase 4 tool execution."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.agent.checkpoints import load_checkpoint
from app.agent.contract import ApprovalDecided, ApprovalProposal, ApprovalRequested, ProposalDecision
from app.agent.run_events import read_run_events
from app.agent.tool_access import ToolAccessDenied, authorize_tool_call
from app.agent.tool_contract import ApplyApprovedUpdate, ExtensionToolCall, ToolCall, UnavailableExtensionResult
from app.auth.tokens import Principal


class ToolExecutionDenied(ToolAccessDenied):
    """The owned run currently lacks the conditions for this tool."""


class ToolCapabilityUnavailable(ToolExecutionDenied):
    """The schema exists for a capability that has no enabled executor."""

    def __init__(self, result: UnavailableExtensionResult) -> None:
        super().__init__("Tool capability unavailable")
        self.result = result


@dataclass(frozen=True)
class RecordedToolApproval:
    """Server-held decision and current case revision read in the write transaction."""

    actor_subject: str
    thread_id: UUID
    run_id: UUID
    case_id: UUID
    proposal_event_seq: int
    proposal_id: UUID
    decision: ProposalDecision
    current_case_revision: int


ApprovalReader = Callable[[Session, UUID, UUID], RecordedToolApproval | None]


def check_tool_execution(
    db: Session, *, principal: Principal, thread_id: UUID, run_id: UUID, call: ToolCall,
    key: bytes | None = None, read_approval: ApprovalReader | None = None,
) -> ApprovalProposal | None:
    """Return the exact approved proposal for a write. Never perform the write.

    The optional reader looks up the run and proposal IDs in the server's approval
    store. It must load the authenticated decision and current locked case revision
    via this session. Without a reader, an update is unavailable.
    """
    status = authorize_tool_call(db, principal=principal, thread_id=thread_id, run_id=run_id, call=call)
    if not isinstance(call, ApplyApprovedUpdate):
        if status != "running":
            raise ToolExecutionDenied("Read and proposal tools require a running run")
        if isinstance(call, ExtensionToolCall):
            raise ToolCapabilityUnavailable(UnavailableExtensionResult(tool=call.tool))
        return None

    if status != "waiting_for_approval" or key is None or read_approval is None:
        raise ToolExecutionDenied("Current user approval is required")
    context = {"principal": principal, "thread_id": thread_id, "run_id": run_id, "key": key}
    checkpoint = load_checkpoint(db, **context)
    if checkpoint is None or not checkpoint.event_seq or checkpoint.state.pending_proposal_id != call.proposal_id:
        raise ToolExecutionDenied("Current user approval is required")
    page = read_run_events(db, **context, after_seq=checkpoint.event_seq - 1, limit=1)
    event = page.events[0] if page is not None and page.events else None
    recorded = event if isinstance(event, ApprovalDecided) else None
    if recorded is not None:
        if recorded.decision.decision != "accept" or recorded.proposal_id != call.proposal_id:
            raise ToolExecutionDenied("Current user approval is required")
        proposal_page = read_run_events(db, **context, after_seq=recorded.proposal_event_seq - 1, limit=1)
        event = proposal_page.events[0] if proposal_page is not None and proposal_page.events else None
    if not isinstance(event, ApprovalRequested) or (event.requires_recorded_decision and recorded is None):
        raise ToolExecutionDenied("Current user approval is required")

    proposal = event.proposal
    if (
        proposal.proposal_id != call.proposal_id or proposal.case_id != call.case_id
        or proposal.expected_case_revision != call.expected_case_revision
    ):
        raise ToolExecutionDenied("Current user approval is required")
    approval = read_approval(db, run_id, proposal.proposal_id)
    if (
        approval is None or approval.actor_subject != principal.subject
        or (approval.thread_id, approval.run_id, approval.case_id) != (thread_id, run_id, call.case_id)
        or (approval.proposal_event_seq, approval.proposal_id) != (event.event_seq, proposal.proposal_id)
        or approval.decision.decision != "accept" or approval.decision.corrected_value is not None
        or (recorded is not None and approval.decision != recorded.decision)
        or approval.decision.expected_case_revision != call.expected_case_revision
        or approval.current_case_revision != call.expected_case_revision
        or proposal.expires_at <= datetime.now(timezone.utc)
    ):
        raise ToolExecutionDenied("Current user approval is required")
    return proposal
