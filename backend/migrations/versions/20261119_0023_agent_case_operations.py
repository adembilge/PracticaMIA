"""Store retry receipts for approved agent case updates."""

from alembic import op
import sqlalchemy as sa

revision = "20261119_0023"
down_revision = "20261118_0022"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_case_operations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("agent_run_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_operation_id", sa.String(36), nullable=False),
        sa.Column("proposal_id", sa.String(36), nullable=False),
        sa.Column("expected_case_revision", sa.BigInteger(), nullable=False),
        sa.Column("case_revision", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("run_id", "client_operation_id", name="uq_agent_case_operation_client_id"),
        sa.UniqueConstraint("run_id", "proposal_id", name="uq_agent_case_operation_proposal"),
        sa.UniqueConstraint("case_id", "expected_case_revision", name="uq_agent_case_operation_revision"),
        sa.CheckConstraint(
            "expected_case_revision > 0 AND case_revision = expected_case_revision + 1",
            name="ck_agent_case_operation_revision",
        ),
    )


def downgrade():
    op.drop_table("agent_case_operations")
