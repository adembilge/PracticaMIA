"""Persist a case write and its retry receipt in the same transaction."""

from collections.abc import Callable
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.agent.case_operations import AgentCaseOperation
from app.agent.contract import ApprovalProposal
from app.agent.tool_access import ToolAccessDenied, authorize_tool_call
from app.agent.tool_contract import ApplyApprovedUpdate, ApplyApprovedUpdateResult
from app.agent.tool_execution import ApprovalReader, check_tool_execution
from app.auth.tokens import Principal
from app.cases.model import CaseRecord


class CaseOperationConflict(ValueError):
    """A committed operation already occupies the key, proposal, or case revision."""


CaseWriter = Callable[[Session, ApprovalProposal], int]


def _result(row: AgentCaseOperation) -> ApplyApprovedUpdateResult:
    return ApplyApprovedUpdateResult(
        tool="apply_approved_update", case_id=row.case_id, proposal_id=row.proposal_id,
        operation_id=row.id, case_revision=row.case_revision,
    )


def apply_approved_case_update(
    sessions: sessionmaker[Session], *, principal: Principal, thread_id: UUID, run_id: UUID,
    call: ApplyApprovedUpdate, key: bytes, read_approval: ApprovalReader, write_case: CaseWriter,
) -> ApplyApprovedUpdateResult:
    """Apply one approved proposal or replay its original receipt.

    The trusted writer uses this session to persist the approved change and
    advance the canonical case revision by one. It does not commit or perform
    external side effects. Approval is checked only when a new write is needed.
    """
    with sessions.begin() as db:
        ready = prepare_approved_case_update(
            db, principal=principal, thread_id=thread_id, run_id=run_id, call=call,
            key=key, read_approval=read_approval,
        )
        return persist_approved_case_update(db, run_id=run_id, call=call, ready=ready, write_case=write_case)


def lock_case_for_update(db: Session, case_id: UUID, principal: Principal) -> None:
    # Lock the case before its run, matching case deletion's cascade order.
    if db.scalar(select(CaseRecord.id).where(
        CaseRecord.id == str(case_id), CaseRecord.owner_subject == principal.subject,
    ).with_for_update()) is None:
        raise ToolAccessDenied("Tool scope unavailable")


def prepare_approved_case_update(
    db: Session, *, principal: Principal, thread_id: UUID, run_id: UUID,
    call: ApplyApprovedUpdate, key: bytes, read_approval: ApprovalReader,
) -> ApprovalProposal | ApplyApprovedUpdateResult:
    """Resolve the write or replay receipt while holding the case and run locks."""
    case_id, stored_run_id = str(call.case_id), str(run_id)
    client_operation_id, proposal_id = str(call.client_operation_id), str(call.proposal_id)
    lock_case_for_update(db, call.case_id, principal)
    context = {"principal": principal, "thread_id": thread_id, "run_id": run_id, "call": call}
    authorize_tool_call(db, **context)

    prior = db.scalar(select(AgentCaseOperation).where(
        AgentCaseOperation.run_id == stored_run_id,
        AgentCaseOperation.client_operation_id == client_operation_id,
    ))
    if prior is not None:
        if (prior.case_id, prior.proposal_id, prior.expected_case_revision) != (
            case_id, proposal_id, call.expected_case_revision,
        ):
            raise CaseOperationConflict("Operation key already used for a different update")
        return _result(prior)

    if db.scalar(select(AgentCaseOperation.id).where(or_(
        and_(AgentCaseOperation.run_id == stored_run_id, AgentCaseOperation.proposal_id == proposal_id),
        and_(AgentCaseOperation.case_id == case_id,
             AgentCaseOperation.expected_case_revision == call.expected_case_revision),
    )).limit(1)) is not None:
        raise CaseOperationConflict("Proposal or case revision already applied")

    proposal = check_tool_execution(db, **context, key=key, read_approval=read_approval)
    if proposal is None:
        raise TypeError("The case writer requires an approved update call")
    return proposal


def persist_approved_case_update(
    db: Session, *, run_id: UUID, call: ApplyApprovedUpdate,
    ready: ApprovalProposal | ApplyApprovedUpdateResult, write_case: CaseWriter,
) -> ApplyApprovedUpdateResult:
    """Use the result of preflight within the same locked transaction."""
    if isinstance(ready, ApplyApprovedUpdateResult):
        return ready
    revision = write_case(db, ready)
    if type(revision) is not int or revision != call.expected_case_revision + 1:
        raise CaseOperationConflict("Case writer did not advance the revision by one")
    receipt = AgentCaseOperation(
        id=str(uuid4()), run_id=str(run_id), case_id=str(call.case_id),
        client_operation_id=str(call.client_operation_id), proposal_id=str(call.proposal_id),
        expected_case_revision=call.expected_case_revision, case_revision=revision,
    )
    db.add(receipt)
    db.flush()
    return _result(receipt)
