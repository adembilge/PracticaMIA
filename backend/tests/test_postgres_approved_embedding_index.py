"""Disposable Postgres test of approved-only vector indexing and revocation.

No API key, no OpenAI request and no live Neon data. SQL changes are
rolled back by an enclosing transaction even when a test fails.
"""
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.knowledge.approved_embedding_index import (
    MODEL_ID, plan_approved_unindexed, prepare_vectors, save_vectors,
)
from app.knowledge.model import KnowledgeSource
from app.knowledge.review_service import approve_version, revoke_version
from app.knowledge.snapshots import ingest_snapshot
from app.knowledge.vector_search import search_approved_semantic

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_SMOKE") != "1",
    reason="requires disposable migrated pgvector PostgreSQL",
)

SCOPE = {
    "jurisdiction": "IT-MI-MILANO",
    "procedure_id": "milan_residence_change",
    "language": "it",
}


def synthetic_source(db, suffix):
    source_id = "ci-approved-vector-" + suffix
    source = KnowledgeSource(
        id=source_id, institution="Synthetic CI municipality fixture",
        jurisdiction=SCOPE["jurisdiction"], procedure_id=SCOPE["procedure_id"],
        language=SCOPE["language"],
        title="Synthetic document for approved-only indexing",
        official_url="https://www.comune.milano.it/servizi/anagrafe/" + source_id,
        document_type="service_page", status="candidate",
    )
    db.add(source)
    db.flush()
    return source


class FakeEmbeddingProvider:
    def __init__(self):
        self.calls = []
    def embed_documents(self, texts):
        self.calls.append(tuple(texts))
        return [[1.0, 0.0] + [0.0] * 1534 for _ in texts]


def test_approved_only_plan_vector_index_and_revocation():
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.connect() as conn:
            outer = conn.begin()
            sessions = sessionmaker(bind=conn, expire_on_commit=False)
            try:
                with sessions.begin() as db:
                    source = synthetic_source(db, "first")
                    fixture = ingest_snapshot(
                        db, source,
                        b"<main><p>Synthetic source: reviewed passage for vector lookup.</p></main>",
                        media_type="text/html",
                    )
                with sessions() as db:
                    assert plan_approved_unindexed(db) == []
                with sessions.begin() as db:
                    approve_version(
                        db, version_id=fixture.version_id,
                        expected_digest=fixture.sha256,
                        actor_subject="ci-synthetic-reviewer",
                        reason="Fictional approval used only in disposable integration test.",
                    )
                with sessions() as db:
                    tasks = plan_approved_unindexed(db)
                    assert len(tasks) == 1
                    assert tasks[0].source_id == "ci-approved-vector-first"
                    assert tasks[0].citation_id == fixture.version_id + ":0000"
                    with pytest.raises(ValueError, match="budget"):
                        plan_approved_unindexed(db, max_passages=0)
                provider = FakeEmbeddingProvider()
                vectors = prepare_vectors(provider, tasks)
                assert len(provider.calls) == 1
                assert provider.calls[0] == (tasks[0].content,)
                with sessions.begin() as db:
                    assert save_vectors(db, tasks, vectors) == 1
                with sessions() as db:
                    assert plan_approved_unindexed(db) == []
                    results = search_approved_semantic(
                        db, query_embedding=vectors[0],
                        model_id=MODEL_ID, **SCOPE,
                    )
                    assert [x.citation_id for x in results] == [
                        fixture.version_id + ":0000",
                    ]
                with sessions.begin() as db:
                    revoke_version(
                        db, version_id=fixture.version_id,
                        expected_digest=fixture.sha256,
                        actor_subject="ci-synthetic-reviewer",
                        reason="Revocation must immediately suppress vectors.",
                    )
                with sessions() as db:
                    assert plan_approved_unindexed(db) == []
                    assert search_approved_semantic(
                        db, query_embedding=vectors[0], model_id=MODEL_ID,
                        **SCOPE,
                    ) == []
                    assert conn.execute(text(
                        "SELECT COUNT(*) FROM knowledge_passage_embeddings "
                        "WHERE model_id = :model",
                    ), {"model": MODEL_ID}).scalar_one() == 1
                    # Row may remain for audit/reprocessing, but the approved
                    # search gate never returns it after revocation.
            finally:
                outer.rollback()
    finally:
        engine.dispose()


def test_provider_vectors_are_withheld_if_approval_is_revoked_during_call():
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.connect() as conn:
            outer = conn.begin()
            sessions = sessionmaker(bind=conn, expire_on_commit=False)
            try:
                with sessions.begin() as db:
                    source = synthetic_source(db, "second")
                    doc = ingest_snapshot(
                        db, source,
                        b"<main><p>Invented synthetic passage before revocation.</p></main>",
                    )
                with sessions.begin() as db:
                    approve_version(
                        db, version_id=doc.version_id,
                        expected_digest=doc.sha256,
                        actor_subject="ci-synthetic-reviewer",
                        reason="Synthetic approval to test concurrent revocation.",
                    )
                with sessions() as db:
                    tasks = plan_approved_unindexed(db)
                    assert len(tasks) == 1
                vectors = prepare_vectors(FakeEmbeddingProvider(), tasks)
                with sessions.begin() as db:
                    revoke_version(
                        db, version_id=doc.version_id,
                        expected_digest=doc.sha256,
                        actor_subject="ci-synthetic-reviewer",
                        reason="Revoke before embedding persistence to test safety.",
                    )
                with pytest.raises(ValueError, match="changed"):
                    with sessions.begin() as db:
                        save_vectors(db, tasks, vectors)
                with sessions() as db:
                    assert conn.execute(text(
                        "SELECT COUNT(*) FROM knowledge_passage_embeddings "
                        "WHERE model_id = :model",
                    ), {"model": MODEL_ID}).scalar_one() == 0
            finally:
                outer.rollback()
    finally:
        engine.dispose()
