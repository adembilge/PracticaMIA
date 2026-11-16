"""Add reversible saved-case archiving."""

from alembic import op
import sqlalchemy as sa

revision = "20261116_0017"
down_revision = "20261109_0016"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cases", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("cases", "archived_at")
