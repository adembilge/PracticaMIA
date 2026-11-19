"""Allow separate case questions in one agent thread."""

from alembic import op
import sqlalchemy as sa

revision = "20261119_0024"
down_revision = "20261119_0023"
branch_labels = None
depends_on = None

TABLE = "agent_run_requests"
FOREGROUND = ("queued", "running", "waiting_for_approval", "stopping")
ACTIVE = (*FOREGROUND, "waiting_for_information")


def _index(name, columns, statuses):
    predicate = sa.text(f"status IN {statuses}")
    op.create_index(name, TABLE, columns, unique=True, postgresql_where=predicate, sqlite_where=predicate)


def upgrade():
    _index("uq_agent_runs_foreground_thread", ["thread_id"], FOREGROUND)
    _index("uq_agent_runs_active_thread_case", ["thread_id", sa.text("coalesce(case_id, '')")], ACTIVE)
    op.drop_index("uq_agent_runs_active_thread", table_name=TABLE)


def downgrade():
    # The old invariant must hold before removing the current protections.
    _index("uq_agent_runs_active_thread", ["thread_id"], ACTIVE)
    op.drop_index("uq_agent_runs_active_thread_case", table_name=TABLE)
    op.drop_index("uq_agent_runs_foreground_thread", table_name=TABLE)
