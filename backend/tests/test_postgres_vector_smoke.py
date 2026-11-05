"""Disposable PostgreSQL pgvector integration tests; never touch live Neon.

All synthetic source creation, mock vector indexing, reviewer approvals and
revocations are rolled back by a wrapping transaction.
"""
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.knowledge.catalog import register_candidates
from app.knowledge.model import KnowledgeSource
from app.knowledge.review_service import approve_version, revoke_version
from app.knowledge.search import resolve_approved_passage
from app.knowledge.snapshots import ingest_snapshot
from app.knowledge.vector_search import (
    EMBEDDING_DIMENSIONS, index_approved_passage_vector,
    search_approved_semantic, search_approved_hybrid,
)

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_SMOKE") != "1",
    reason="requires migrated disposable pgvector PostgreSQL",
)
SCOPE = {
    "jurisdiction": "IT-MI-MILANO",
    "procedure_id": "milan_residence_change",
    "language": "it",
}
MODEL = "ci-synthetic-1536"


def vector(x=1.0, y=0.0):
    return [float(x), float(y)] + [0.0] * (EMBEDDING_DIMENSIONS - 2)


def test_pgvector_approved_only_semantic_hybrid_and_revocation():
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            assert conn.execute(text(
                "SELECT to_regclass('knowledge_passage_embeddings')"
            )).scalar() == "knowledge_passage_embeddings"
            assert conn.execute(text(
                "SELECT to_regclass('ix_knowledge_embedding_cosine')"
            )).scalar() == "ix_knowledge_embedding_cosine"
            factory = sessionmaker(bind=conn, expire_on_commit=False)
            try:
                with factory.begin() as db:
                    register_candidates(db)
                    src = db.get(KnowledgeSource, "milano-residence-minor-documents")
                    assert src is not None and src.status == "candidate"
                    doc = ingest_snapshot(
                        db, src,
                        b"<html><main><p>Test-only synthetic house evidence.</p></main></html>",
                    )
                    citation = f"{doc.version_id}:0000"

                with factory.begin() as db:
                    assert not index_approved_passage_vector(
                        db, citation_id=citation, model_id=MODEL,
                        embedding=vector(), **SCOPE,
                    )
                with factory() as db:
                    assert search_approved_semantic(
                        db, query_embedding=vector(), model_id=MODEL, **SCOPE,
                    ) == []

                with factory.begin() as db:
                    approve_version(
                        db, version_id=doc.version_id,
                        expected_digest=doc.sha256, actor_subject="synthetic-ci",
                        reason="Synthetic only: approve test fixture in rollback transaction.",
                    )
                    assert index_approved_passage_vector(
                        db, citation_id=citation, model_id=MODEL,
                        embedding=vector(), **SCOPE,
                    )

                with factory() as db:
                    semantic = search_approved_semantic(
                        db, query_embedding=vector(), model_id=MODEL, **SCOPE,
                    )
                    assert [e.citation_id for e in semantic] == [citation]
                    assert semantic[0].source_version_id == doc.version_id
                    assert resolve_approved_passage(db, citation_id=citation, **SCOPE) == semantic[0]
                    assert search_approved_semantic(
                        db, query_embedding=vector(), model_id=MODEL,
                        jurisdiction="IT-RM-ROMA",
                        procedure_id=SCOPE["procedure_id"], language="it",
                    ) == []
                    hybrid = search_approved_hybrid(
                        db, query="casa", query_embedding=vector(),
                        model_id=MODEL, **SCOPE,
                    )
                    assert [e.citation_id for e in hybrid] == [citation]

                with factory.begin() as db:
                    revoke_version(
                        db, version_id=doc.version_id,
                        expected_digest=doc.sha256, actor_subject="synthetic-ci",
                        reason="Synthetic only: revoke test evidence to enforce abstention.",
                    )
                with factory() as db:
                    assert search_approved_semantic(
                        db, query_embedding=vector(), model_id=MODEL, **SCOPE,
                    ) == []
                    assert search_approved_hybrid(
                        db, query="casa", query_embedding=vector(),
                        model_id=MODEL, **SCOPE,
                    ) == []
            finally:
                trans.rollback()
    finally:
        engine.dispose()
