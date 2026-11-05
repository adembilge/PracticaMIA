"""Disposable PostgreSQL smoke test for manual original-file intake."""
import os

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.knowledge.batch_import import (
    ingest_prepared, prepare_directory, queue_records, require_staging_database,
)
from app.knowledge.catalog import candidate_sources, register_candidates
from app.knowledge.model import KnowledgeSourceVersion

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_SMOKE") != "1",
    reason="requires migrated, disposable CI PostgreSQL",
)


def test_batch_original_intake_stays_pending_and_rolls_back(tmp_path):
    (tmp_path / "milano-residence-change.html").write_bytes(
        b"<html><body><main><p>Fictitious source from unit tests only. "
        b"Residenza procedura sintetica.</p></main></body></html>"
    )
    prepared = prepare_directory(tmp_path)
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                factory = sessionmaker(bind=conn, expire_on_commit=False)
                with factory.begin() as db:
                    require_staging_database(db)
                    register_candidates(db)
                    results = ingest_prepared(db, prepared)
                    assert results[0]["status"] == "pending_review"
                    assert results[0]["previous_approval_invalidated"] is False
                with factory() as db:
                    versions = db.scalars(select(KnowledgeSourceVersion)).all()
                    assert len(versions) == 1
                    assert versions[0].status == "pending_review"
                    queue = queue_records(candidate_sources(), db)
                    assert sum(x["stored_version_status"] == "pending_review"
                               for x in queue) == 1
                    assert conn.execute(text(
                        "SELECT count(*) FROM knowledge_passage_embeddings"
                    )).scalar_one() == 0
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
