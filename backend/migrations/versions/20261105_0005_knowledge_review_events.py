"""Append-only review decision and source change events.

Revision ID: 20261105_0005
Revises: 20261105_0004

Additive; no source approvals, source imports, or case mutations.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261105_0005"
down_revision = "20261105_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "knowledge_review_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_id", sa.String(length=96),
                  sa.ForeignKey("knowledge_sources.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("version_id", sa.String(length=36),
                  sa.ForeignKey("knowledge_source_versions.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("actor_subject", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("old_source_status", sa.String(length=24), nullable=False),
        sa.Column("new_source_status", sa.String(length=24), nullable=False),
        sa.Column("old_version_status", sa.String(length=24), nullable=False),
        sa.Column("new_version_status", sa.String(length=24), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "action IN ('approved', 'revoked', 'source_changed')",
            name="ck_knowledge_review_event_action",
        ),
    )
    op.create_index("ix_knowledge_review_events_source_id",
                    "knowledge_review_events", ["source_id"])
    op.create_index("ix_knowledge_review_events_version_id",
                    "knowledge_review_events", ["version_id"])


def downgrade():
    op.drop_index("ix_knowledge_review_events_version_id",
                  table_name="knowledge_review_events")
    op.drop_index("ix_knowledge_review_events_source_id",
                  table_name="knowledge_review_events")
    op.drop_table("knowledge_review_events")
