"""Create provenance-safe official-source metadata registry.

Revision ID: 20261104_0003
Revises: 20261104_0002

No contents or approvals are seeded automatically. Existing case records are unchanged.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261104_0003"
down_revision = "20261104_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.String(length=96), primary_key=True),
        sa.Column("institution", sa.String(length=160), nullable=False),
        sa.Column("jurisdiction", sa.String(length=48), nullable=False),
        sa.Column("procedure_id", sa.String(length=96), nullable=False),
        sa.Column("language", sa.String(length=5), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("official_url", sa.String(length=700), nullable=False, unique=True),
        sa.Column("document_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False,
                  server_default="candidate"),
        sa.Column("active_version_id", sa.String(length=36), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('candidate', 'approved', 'revoked')",
            name="ck_knowledge_sources_status",
        ),
    )
    op.create_index("ix_knowledge_sources_jurisdiction", "knowledge_sources",
                    ["jurisdiction"])
    op.create_index("ix_knowledge_sources_procedure_id", "knowledge_sources",
                    ["procedure_id"])

    op.create_table(
        "knowledge_source_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_id", sa.String(length=96),
                  sa.ForeignKey("knowledge_sources.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False,
                  server_default="pending_review"),
        sa.UniqueConstraint("source_id", "revision",
                            name="uq_source_revision"),
        sa.CheckConstraint("revision > 0", name="ck_source_revision_positive"),
        sa.CheckConstraint(
            "status IN ('pending_review', 'approved', 'revoked', 'superseded')",
            name="ck_source_version_status",
        ),
    )
    op.create_index("ix_knowledge_source_versions_source_id",
                    "knowledge_source_versions", ["source_id"])


def downgrade():
    op.drop_index("ix_knowledge_source_versions_source_id",
                  table_name="knowledge_source_versions")
    op.drop_table("knowledge_source_versions")
    op.drop_index("ix_knowledge_sources_procedure_id",
                  table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_jurisdiction",
                  table_name="knowledge_sources")
    op.drop_table("knowledge_sources")
