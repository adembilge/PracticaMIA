"""Add encrypted agent message requests and thread revisions."""

from alembic import op
import sqlalchemy as sa

revision = "20261118_0019"
down_revision = "20261118_0018"
branch_labels = None
depends_on = None

ACTIVE = ("queued", "running", "waiting_for_information", "waiting_for_approval", "stopping")
STATUSES = (*ACTIVE, "completed", "failed", "stopped")


def upgrade():
    op.add_column(
        "agent_threads",
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_table(
        "agent_run_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("thread_id", sa.String(36), sa.ForeignKey("agent_threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_id", sa.String(36)),
        sa.Column("client_message_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("accepted_revision", sa.Integer(), nullable=False),
        sa.Column("message_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["thread_id", "case_id"], ["agent_thread_cases.thread_id", "agent_thread_cases.case_id"],
            ondelete="CASCADE", name="fk_agent_runs_linked_case",
        ),
        sa.UniqueConstraint("thread_id", "client_message_id", name="uq_agent_runs_client_message"),
        sa.CheckConstraint(f"status IN {STATUSES}", name="ck_agent_run_requests_status"),
    )
    op.create_index(
        "uq_agent_runs_active_thread", "agent_run_requests", ["thread_id"], unique=True,
        postgresql_where=sa.text(f"status IN {ACTIVE}"),
        sqlite_where=sa.text(f"status IN {ACTIVE}"),
    )


def downgrade():
    op.drop_index("uq_agent_runs_active_thread", table_name="agent_run_requests")
    op.drop_table("agent_run_requests")
    op.drop_column("agent_threads", "revision")
