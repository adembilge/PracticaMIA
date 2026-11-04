"""Add authenticated ownership; prior anonymous demo cases remain inaccessible.

Revision ID: 20261104_0002
Revises: 20261104_0001
"""
from alembic import op
import sqlalchemy as sa

revision = "20261104_0002"
down_revision = "20261104_0001"
branch_labels = None
depends_on = None


def upgrade():
    # Do not assign legacy anonymous cases to an arbitrary user.
    op.add_column("cases", sa.Column("owner_subject", sa.String(length=255), nullable=True))
    op.create_index("ix_cases_owner_subject", "cases", ["owner_subject"])


def downgrade():
    op.drop_index("ix_cases_owner_subject", table_name="cases")
    op.drop_column("cases", "owner_subject")
