"""Private synthetic-only preparation and encrypted document fixture tables.

Revision ID: 20261106_0011
Revises: 20261106_0010
This additive migration must be applied only to an explicitly authorized
isolated staging database; merging code does not run migrations.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261106_0011"
down_revision = "20261106_0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "case_preparations",
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("owner_subject", sa.String(255), nullable=False),
        sa.Column("facts_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("review_digest", sa.String(64), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_case_preparations_owner_subject", "case_preparations", ["owner_subject"])
    op.create_table(
        "case_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_subject", sa.String(255), nullable=False),
        sa.Column("document_type", sa.String(64), nullable=False),
        sa.Column("media_type", sa.String(40), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("review_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_case_documents_case_id", "case_documents", ["case_id"])
    op.create_index("ix_case_documents_owner_subject", "case_documents", ["owner_subject"])


def downgrade():
    op.drop_index("ix_case_documents_owner_subject", table_name="case_documents")
    op.drop_index("ix_case_documents_case_id", table_name="case_documents")
    op.drop_table("case_documents")
    op.drop_index("ix_case_preparations_owner_subject", table_name="case_preparations")
    op.drop_table("case_preparations")
