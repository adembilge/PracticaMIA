"""Encrypted, case-owned synthetic Preview agent turns.

Revision ID: 20261108_0012
Revises: 20261106_0011

Additive schema only. Do not migrate production or existing Preview databases
without an explicit environment-specific migration review.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261108_0012"
down_revision = "20261106_0011"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "case_agent_turns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36),
                  sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_subject", sa.String(255), nullable=False),
        sa.Column("content_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_case_agent_turns_case_id", "case_agent_turns", ["case_id"])
    op.create_index("ix_case_agent_turns_owner_subject", "case_agent_turns", ["owner_subject"])


def downgrade():
    op.drop_index("ix_case_agent_turns_owner_subject", table_name="case_agent_turns")
    op.drop_index("ix_case_agent_turns_case_id", table_name="case_agent_turns")
    op.drop_table("case_agent_turns")
