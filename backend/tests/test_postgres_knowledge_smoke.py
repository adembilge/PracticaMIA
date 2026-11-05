"""Migration smoke for official knowledge tables on disposable CI PostgreSQL."""
import os

import pytest
from sqlalchemy import create_engine, inspect

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_SMOKE") != "1",
    reason="requires migrated PostgreSQL test database",
)


def test_knowledge_schema_exists_after_migration():
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        inspector = inspect(engine)
        assert {"cases", "knowledge_sources", "knowledge_source_versions",
             "knowledge_source_snapshots", "knowledge_source_passages",
             "knowledge_review_events"}.issubset(
            set(inspector.get_table_names())
        )
        sources = {column["name"] for column in inspector.get_columns("knowledge_sources")}
        versions = {column["name"] for column in
                    inspector.get_columns("knowledge_source_versions")}
        assert {"id", "official_url", "status", "active_version_id",
                "jurisdiction", "procedure_id"}.issubset(sources)
        assert {"id", "source_id", "revision", "content_sha256", "status",
                "reviewed_at", "reviewed_by"}.issubset(versions)
        snapshot_cols = {c["name"] for c in inspector.get_columns("knowledge_source_snapshots")}
        passage_cols = {c["name"] for c in inspector.get_columns("knowledge_source_passages")}
        assert {"version_id", "raw_body", "normalized_text", "extraction_version"}.issubset(snapshot_cols)
        assert {"version_id", "ordinal", "section_path", "start_offset", "end_offset"}.issubset(passage_cols)
        audit_cols = {c["name"] for c in inspector.get_columns("knowledge_review_events")}
        assert {"id", "source_id", "version_id", "action", "actor_subject",
                "reason", "content_sha256", "occurred_at"}.issubset(audit_cols)
    finally:
        engine.dispose()
