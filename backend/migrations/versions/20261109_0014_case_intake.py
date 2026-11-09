"""Additive private case-owned categorical intake.

Revision ID: 20261109_0014
Revises: 20261109_0013

No existing cases, documents, or source approvals are changed.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261109_0014"
down_revision = "20261109_0013"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "case_intakes",
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("owner_subject", sa.String(255), nullable=False),
        sa.Column("facts", sa.JSON(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_case_intakes_owner_subject", "case_intakes", ["owner_subject"])


def downgrade():
    # Never downgrade against active private case data without explicit backup.
    op.drop_index("ix_case_intakes_owner_subject", table_name="case_intakes")
    op.drop_table("case_intakes")
