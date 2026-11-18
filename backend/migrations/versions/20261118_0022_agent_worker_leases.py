"""Add expiring worker reservations to agent runs."""

from alembic import op
import sqlalchemy as sa

revision = "20261118_0022"
down_revision = "20261118_0021"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("agent_run_requests", sa.Column("lease_token", sa.String(36)))
    op.add_column("agent_run_requests", sa.Column("lease_expires_at", sa.DateTime(timezone=True)))
    op.create_check_constraint(
        "ck_agent_worker_lease_pair", "agent_run_requests",
        "(lease_token IS NULL) = (lease_expires_at IS NULL)",
    )
    op.create_index(
        "ix_agent_worker_queue", "agent_run_requests", ["accepted_at", "id"],
        postgresql_where=sa.text("status IN ('queued', 'running')"),
        sqlite_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade():
    op.drop_index("ix_agent_worker_queue", table_name="agent_run_requests")
    op.drop_constraint("ck_agent_worker_lease_pair", "agent_run_requests", type_="check")
    op.drop_column("agent_run_requests", "lease_expires_at")
    op.drop_column("agent_run_requests", "lease_token")
