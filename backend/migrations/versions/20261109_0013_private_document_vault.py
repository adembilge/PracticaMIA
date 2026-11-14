"""Add isolated, owner-scoped vault for consented, scanned, expiring documents.

Revision ID: 20261109_0013
Revises: 20261108_0012

Additive only. Does not import, decrypt, or mutate existing case/document rows.
No real document endpoint is enabled by this migration.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261109_0013"
down_revision = "20261108_0012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "private_case_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_subject", sa.String(255), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("media_type", sa.String(40), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("consent_version", sa.String(48), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_private_case_documents_case_id", "private_case_documents", ["case_id"])
    op.create_index("ix_private_case_documents_owner_subject", "private_case_documents", ["owner_subject"])
    op.create_index("ix_private_document_expiry", "private_case_documents", ["expires_at"])


def downgrade():
    # Never run this downgrade against real applicant documents.
    op.drop_index("ix_private_document_expiry", table_name="private_case_documents")
    op.drop_index("ix_private_case_documents_owner_subject", table_name="private_case_documents")
    op.drop_index("ix_private_case_documents_case_id", table_name="private_case_documents")
    op.drop_table("private_case_documents")
