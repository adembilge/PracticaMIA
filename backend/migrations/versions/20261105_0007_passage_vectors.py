"""PostgreSQL pgvector for approved, version-bound official passages.

Revision ID: 20261105_0007
Revises: 20261105_0006

Metadata-only migration: no automatic embeddings, approval, source changes,
external model calls, or public RAG endpoints. SQLite is unit-test only.
"""
from alembic import op

revision = "20261105_0007"
down_revision = "20261105_0006"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("""
        CREATE TABLE knowledge_passage_embeddings (
            passage_id VARCHAR(64) NOT NULL
                REFERENCES knowledge_source_passages(id) ON DELETE RESTRICT,
            model_id VARCHAR(96) NOT NULL,
            version_id VARCHAR(36) NOT NULL
                REFERENCES knowledge_source_versions(id) ON DELETE RESTRICT,
            passage_sha256 VARCHAR(64) NOT NULL,
            embedding vector(1536) NOT NULL,
            PRIMARY KEY (passage_id, model_id),
            CONSTRAINT ck_passage_embedding_hash
                CHECK (passage_sha256 ~ '^[0-9a-f]{64}$')
        )
    """)
    op.execute("""
        CREATE INDEX ix_knowledge_embedding_version_model
        ON knowledge_passage_embeddings (version_id, model_id)
    """)
    op.execute("""
        CREATE INDEX ix_knowledge_embedding_cosine
        ON knowledge_passage_embeddings
        USING hnsw (embedding vector_cosine_ops)
    """)


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP TABLE knowledge_passage_embeddings")
    # Never drop the shared vector extension: other schemas may depend on it.
