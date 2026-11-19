"""Bind an agent tool request to the server's acting principal and run."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.agent.run_requests import AgentRunRequest, _owned_run
from app.agent.tool_contract import ApplyApprovedUpdate, FindProcedure, ToolCall
from app.auth.tokens import Principal


class ToolAccessDenied(PermissionError):
    """The acting principal cannot access the requested tool scope."""


def authorize_tool_call(
    db: Session, *, principal: Principal, thread_id: UUID, run_id: UUID, call: ToolCall,
) -> str:
    """Check ownership in the caller's transaction before accessing case data.

    The principal comes from authentication or the persisted worker lease.
    A write still needs its own approval and revision checks in that transaction.
    """
    owned_run = _owned_run(thread_id, run_id, principal).with_only_columns(AgentRunRequest.status)
    if not isinstance(call, FindProcedure):
        owned_run = owned_run.where(AgentRunRequest.case_id == str(call.case_id))
    status = db.scalar(owned_run.with_for_update(
        read=not isinstance(call, ApplyApprovedUpdate), of=AgentRunRequest,
    ))
    if status is None:
        raise ToolAccessDenied("Tool scope unavailable")
    return status
