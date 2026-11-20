"""Disposable PostgreSQL smoke test for manual original-file intake."""
import os
from dataclasses import replace
from hashlib import sha256

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.knowledge.batch_import import (
    ingest_prepared, prepare_directory, queue_records, require_staging_database,
)
from app.knowledge.catalog import candidate_sources, register_candidates
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.pilot_source_review import _prepare_originals, _store_originals
from app.knowledge.pilot_sources import PILOT_CLAIM_PASSAGES, PILOT_SOURCES
from app.knowledge.review_model import KnowledgeReviewEvent
from app.knowledge.search import resolve_approved_passage
from app.knowledge.staging_guard import require_pilot_preview_database

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
                    imported = db.get(
                        KnowledgeSourceVersion, results[0]["version_id"],
                    )
                    assert imported is not None
                    assert imported.source_id == "milano-residence-change"
                    assert imported.status == "pending_review"
                    queue = queue_records(candidate_sources(), db)
                    assert next(
                        row for row in queue
                        if row["source_id"] == "milano-residence-change"
                    )["stored_version_status"] == "pending_review"
                    assert conn.execute(text(
                        "SELECT count(*) FROM knowledge_passage_embeddings"
                    )).scalar_one() == 0
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def test_pilot_preview_import_preserves_pending_ids_and_rolls_back_on_passage_mismatch(tmp_path, monkeypatch):
    for source_id, source in PILOT_SOURCES.items():
        body = f"<p>Synthetic pilot text for {source_id}.</p>".encode()
        (tmp_path / f"{source_id}.html").write_bytes(body)
        monkeypatch.setitem(PILOT_SOURCES, source_id, replace(source, content_sha256=sha256(body).hexdigest()))
    for claim, refs in PILOT_CLAIM_PASSAGES.items():
        monkeypatch.setitem(PILOT_CLAIM_PASSAGES, claim, tuple(
            (source_id, 0, sha256(f"Synthetic pilot text for {source_id}.".encode()).hexdigest())
            for source_id, _, _ in refs
        ))

    engine = create_engine(os.environ["DATABASE_URL"])
    monkeypatch.setenv("PRACTICAMIA_KNOWLEDGE_TARGET", "staging")
    monkeypatch.setenv("PRACTICAMIA_PILOT_PREVIEW_HOST", engine.url.host)
    monkeypatch.setenv("PRACTICAMIA_PILOT_PREVIEW_DATABASE", engine.url.database)
    originals = _prepare_originals(tmp_path, include_postal=True)
    try:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                factory = sessionmaker(bind=conn, join_transaction_mode="create_savepoint")
                with monkeypatch.context() as transient:
                    transient.setitem(PILOT_CLAIM_PASSAGES, "Q3", (("poste-residence-permit-appointments", 0, "0" * 64),))
                    with pytest.raises(ValueError, match="Passage has changed"), factory.begin() as db:
                        _store_originals(db, originals)
                with factory.begin() as db:
                    assert db.scalars(select(KnowledgeSource.id).where(KnowledgeSource.id.in_(PILOT_SOURCES))).all() == []
                    require_pilot_preview_database(db)
                    first = _store_originals(db, originals)
                with factory.begin() as db:
                    repeat = _store_originals(db, originals)
                    assert {row["status"] for row in first["sources"]} == {"pending_review"}
                    assert {row["status"] for row in repeat["sources"]} == {"unchanged"}
                    assert first["claims_pending_review"] == repeat["claims_pending_review"]
                    assert len(first["claims_pending_review"]) == 6
                    assert not db.scalars(select(KnowledgeReviewEvent.id).where(
                        KnowledgeReviewEvent.source_id.in_(PILOT_SOURCES),
                    )).all()
                    for refs in first["claims_pending_review"].values():
                        for ref in refs:
                            source = db.get(KnowledgeSource, ref["source_id"])
                            assert source.active_version_id is None
                            assert resolve_approved_passage(
                                db, citation_id=ref["passage_id"], jurisdiction=source.jurisdiction,
                                procedure_id=source.procedure_id, language=source.language,
                            ) is None
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
