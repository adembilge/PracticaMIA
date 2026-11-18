"""Add owner-scoped agent threads and case links."""

from alembic import op
import sqlalchemy as sa

revision = "20261118_0018"
down_revision = "20261116_0017"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_threads",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_subject", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "agent_thread_cases",
        sa.Column(
            "thread_id", sa.String(36), sa.ForeignKey("agent_threads.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "case_id", sa.String(36), sa.ForeignKey("cases.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index("ix_agent_thread_cases_case_id", "agent_thread_cases", ["case_id"])


def downgrade():
    op.drop_index("ix_agent_thread_cases_case_id", table_name="agent_thread_cases")
    op.drop_table("agent_thread_cases")
    op.drop_table("agent_threads")
