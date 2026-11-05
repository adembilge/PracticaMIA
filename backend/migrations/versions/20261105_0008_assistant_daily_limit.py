"""Shared pseudonymous assistant model-call quota.

Revision ID: 20261105_0008
Revises: 20261105_0007

No source approvals, embeddings, model credentials or production feature
activation. Apply on isolated staging first.
"""
from alembic import op

revision = "20261105_0008"
down_revision = "20261105_0007"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE assistant_daily_usage (
            subject_digest VARCHAR(64) NOT NULL,
            usage_day DATE NOT NULL,
            request_count INTEGER NOT NULL,
            PRIMARY KEY (subject_digest, usage_day),
            CONSTRAINT ck_assistant_daily_usage_positive
                CHECK (request_count > 0)
        )
    """)


def downgrade():
    op.execute("DROP TABLE assistant_daily_usage")
