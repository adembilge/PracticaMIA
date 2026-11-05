"""Distinguish approved-origin server bytes from browser-rendered captures.

Revision ID: 20261105_0009
Revises: 20261105_0008
"""
from alembic import op

revision = "20261105_0009"
down_revision = "20261105_0008"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE knowledge_source_snapshots
        ADD COLUMN capture_method VARCHAR(32) NOT NULL DEFAULT 'original_http'
    """)
    op.execute("""
        ALTER TABLE knowledge_source_snapshots
        ADD COLUMN observed_url VARCHAR(700)
    """)
    op.execute("""
        ALTER TABLE knowledge_source_snapshots
        ADD COLUMN observed_title VARCHAR(300)
    """)
    op.execute("""
        ALTER TABLE knowledge_source_snapshots
        ADD COLUMN observed_last_updated VARCHAR(10)
    """)
    op.execute("""
        ALTER TABLE knowledge_source_snapshots
        ADD CONSTRAINT ck_snapshot_capture_method
        CHECK (capture_method IN ('original_http','browser_rendered_text'))
    """)


def downgrade():
    op.execute("ALTER TABLE knowledge_source_snapshots DROP CONSTRAINT ck_snapshot_capture_method")
    op.execute("ALTER TABLE knowledge_source_snapshots DROP COLUMN observed_last_updated")
    op.execute("ALTER TABLE knowledge_source_snapshots DROP COLUMN observed_title")
    op.execute("ALTER TABLE knowledge_source_snapshots DROP COLUMN observed_url")
    op.execute("ALTER TABLE knowledge_source_snapshots DROP COLUMN capture_method")
