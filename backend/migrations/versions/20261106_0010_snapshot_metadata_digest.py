"""Bind browser-rendered source metadata into a separate audit checksum.

Revision ID: 20261106_0010
Revises: 20261105_0009

Historical snapshots receive a deterministic one-time backfill. The hash
detects accidental or unauthorized single-field metadata edits; it is not
a signature issued by Comune di Milano.
"""
from hashlib import sha256

from alembic import op
import sqlalchemy as sa

revision = "20261106_0010"
down_revision = "20261105_0009"
branch_labels = None
depends_on = None


def _digest(row) -> str:
    pieces = (
        row["fetched_url"], row["media_type"], row["capture_method"],
        row["observed_url"], row["observed_title"],
        row["observed_last_updated"],
    )
    serialized = "".join(
        "-1:" if value is None else f"{len(value)}:{value}"
        for value in pieces
    ).encode("utf-8")
    return sha256(serialized).hexdigest()


def upgrade() -> None:
    op.add_column(
        "knowledge_source_snapshots",
        sa.Column("metadata_sha256", sa.String(64), nullable=True),
    )
    db = op.get_bind()
    rows = db.execute(sa.text("""
        SELECT version_id, fetched_url, media_type, capture_method,
               observed_url, observed_title, observed_last_updated
          FROM knowledge_source_snapshots
    """)).mappings().all()
    for row in rows:
        db.execute(sa.text("""
            UPDATE knowledge_source_snapshots
               SET metadata_sha256 = :digest WHERE version_id = :id
        """), {"digest": _digest(row), "id": row["version_id"]})
    op.alter_column(
        "knowledge_source_snapshots", "metadata_sha256",
        existing_type=sa.String(64), nullable=False,
    )


def downgrade() -> None:
    op.drop_column("knowledge_source_snapshots", "metadata_sha256")
