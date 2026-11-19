"""Persist a case write and its retry receipt in the same transaction."""

from collections.abc import Callable
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, UniqueConstraint, and_, or_, select
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from app.agent.contract import ApprovalProposal
from app.agent.tool_access import ToolAccessDenied, authorize_tool_call
from app.agent.tool_contract import ApplyApprovedUpdate, ApplyApprovedUpdateResult
from app.agent.tool_execution import ApprovalReader, check_tool_execution
from app.auth.tokens import Principal
from app.cases.model import CaseRecord
from app.database import Base


class AgentCaseOperation(Base):
    __tablename__ = "agent_case_operations"
    __table_args__ = (
        UniqueConstraint("run_id", "client_operation_id", name="uq_agent_case_operation_client_id"),
        UniqueConstraint("run_id", "proposal_id", name="uq_agent_case_operation_proposal"),
        UniqueConstraint("case_id", "expected_case_revision", name="uq_agent_case_operation_revision"),
        CheckConstraint(
            "expected_case_revision > 0 AND case_revision = expected_case_revision + 1",
            name="ck_agent_case_operation_revision",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_run_requests.id", ondelete="CASCADE"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    client_operation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    proposal_id: Mapped[str] = mapped_column(String(36), nullable=False)
    expected_case_revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    case_revision: Mapped[int] = mapped_column(BigInteger, nullable=False)


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
    case_id, stored_run_id = str(call.case_id), str(run_id)
    client_operation_id, proposal_id = str(call.client_operation_id), str(call.proposal_id)
    with sessions.begin() as db:
        # Lock the case before its run, matching case deletion's cascade order.
        if db.scalar(select(CaseRecord.id).where(
            CaseRecord.id == case_id, CaseRecord.owner_subject == principal.subject,
        ).with_for_update()) is None:
            raise ToolAccessDenied("Tool scope unavailable")
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
        revision = write_case(db, proposal)
        if type(revision) is not int or revision != call.expected_case_revision + 1:
            raise CaseOperationConflict("Case writer did not advance the revision by one")
        receipt = AgentCaseOperation(
            id=str(uuid4()), run_id=stored_run_id, case_id=case_id, client_operation_id=client_operation_id,
            proposal_id=proposal_id, expected_case_revision=call.expected_case_revision, case_revision=revision,
        )
        db.add(receipt)
        db.flush()
        return _result(receipt)
