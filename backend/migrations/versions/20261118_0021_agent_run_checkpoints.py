"""Add encrypted checkpoints for resumable agent work."""

from alembic import op
import sqlalchemy as sa

revision = "20261118_0021"
down_revision = "20261118_0020"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_run_checkpoints",
        sa.Column(
            "run_id", sa.String(36), sa.ForeignKey("agent_run_requests.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("event_seq", sa.Integer(), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.CheckConstraint("revision > 0", name="ck_agent_checkpoint_revision"),
        sa.CheckConstraint("event_seq >= 0", name="ck_agent_checkpoint_event_seq"),
    )


def downgrade():
    op.drop_table("agent_run_checkpoints")
