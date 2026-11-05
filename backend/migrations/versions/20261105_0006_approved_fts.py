"""Index approved-passage lexical retrieval using PostgreSQL full-text search.

Revision ID: 20261105_0006
Revises: 20261105_0005

Creates a PostgreSQL GIN expression index only. Source approval remains
controlled by existing human-reviewed active version metadata. No source
ingestion or automatic approval occurs during migration.
"""
from alembic import op

revision = "20261105_0006"
down_revision = "20261105_0005"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX ix_knowledge_passages_fts_simple "
            "ON knowledge_source_passages USING GIN "
            "(to_tsvector('simple'::regconfig, content))"
        )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP INDEX ix_knowledge_passages_fts_simple")
