"""Store immutable-intended source snapshots and provenance-preserving passages.

Revision ID: 20261105_0004
Revises: 20261104_0003

Only additive tables. No automatic import, approval, or change to case records.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261105_0004"
down_revision = "20261104_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "knowledge_source_snapshots",
        sa.Column("version_id", sa.String(36),
                  sa.ForeignKey("knowledge_source_versions.id", ondelete="RESTRICT"),
                  primary_key=True),
        sa.Column("fetched_url", sa.String(700), nullable=False),
        sa.Column("media_type", sa.String(60), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("extraction_version", sa.String(24), nullable=False),
        sa.Column("raw_body", sa.LargeBinary(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.CheckConstraint("size_bytes > 0", name="ck_snapshot_positive_size"),
    )
    op.create_table(
        "knowledge_source_passages",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("version_id", sa.String(36),
                  sa.ForeignKey("knowledge_source_versions.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("section_path", sa.String(300), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.UniqueConstraint("version_id", "ordinal",
                            name="uq_passage_version_ordinal"),
        sa.CheckConstraint("ordinal >= 0", name="ck_passage_ordinal_nonnegative"),
        sa.CheckConstraint("start_offset >= 0 AND end_offset > start_offset",
                           name="ck_passage_valid_span"),
    )
    op.create_index("ix_knowledge_source_passages_version_id",
                    "knowledge_source_passages", ["version_id"])


def downgrade():
    op.drop_index("ix_knowledge_source_passages_version_id",
                  table_name="knowledge_source_passages")
    op.drop_table("knowledge_source_passages")
    op.drop_table("knowledge_source_snapshots")
