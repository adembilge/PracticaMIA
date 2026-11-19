"""Owned, transactional receipts for approved case operations."""

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

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
