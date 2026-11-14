"""Add encrypted, expiring review metadata to private-document vault.

Revision ID: 20261109_0015
Revises: 20261109_0014

Additive and nullable: no change to existing cases, files or source versions.
Metadata shares the existing document row's deletion and seven-day expiry.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261109_0015"
down_revision = "20261109_0014"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("private_case_documents",
                  sa.Column("review_ciphertext", sa.LargeBinary(), nullable=True))


def downgrade():
    # Do not downgrade while users have saved document reviews.
    op.drop_column("private_case_documents", "review_ciphertext")
