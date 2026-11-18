"""Add the encrypted, ordered agent run event journal."""

from alembic import op
import sqlalchemy as sa

revision = "20261118_0020"
down_revision = "20261118_0019"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_run_events",
        sa.Column(
            "run_id", sa.String(36), sa.ForeignKey("agent_run_requests.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("event_seq", sa.Integer(), primary_key=True),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.CheckConstraint("event_seq > 0", name="ck_agent_run_events_sequence"),
    )


def downgrade():
    op.drop_table("agent_run_events")
