"""Bind user-only checklist review marks to currently verified case evidence.

Revision ID: 20261109_0016
Revises: 20261109_0015

Additive, owner-scoped and nullable-safe; no existing cases or files changed.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261109_0016"
down_revision = "20261109_0015"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("case_intakes", sa.Column(
        "checklist_progress", sa.JSON(), nullable=False, server_default="{}"
    ))
    op.add_column("case_intakes", sa.Column(
        "progress_fingerprint", sa.String(64), nullable=True
    ))
    op.alter_column("case_intakes", "checklist_progress", server_default=None)


def downgrade():
    # Downgrades would remove saved review marks; require a recovery snapshot.
    op.drop_column("case_intakes", "progress_fingerprint")
    op.drop_column("case_intakes", "checklist_progress")
