"""Source-grounded lexical benchmark on the disposable CI PostgreSQL database.

The fixture contains invented HTML, not municipal text or legal rules. Every
review step is synthetic, transaction-scoped and rolled back after the test.
"""
import json
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.knowledge.catalog import register_candidates
from app.knowledge.model import KnowledgeSource
from app.knowledge.retrieval_eval import score_query, summarize
from app.knowledge.review_service import approve_version
from app.knowledge.search import resolve_approved_passage, search_approved_passages
from app.knowledge.snapshots import ingest_snapshot


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_SMOKE") != "1",
    reason="requires migrated disposable PostgreSQL database",
)
FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "evals" / "fixtures" / "knowledge_retrieval_synthetic.json"
)


def test_postgres_ranked_relevance_and_abstention():
    dataset = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert "synthetic" in dataset["dataset"].lower()
    assert len(dataset["cases"]) >= 4
    assert any(item["expected"] for item in dataset["cases"])
    assert any(not item["expected"] for item in dataset["cases"])
    scope = dataset["scope"]

    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.connect() as connection:
            # This outer transaction is never committed, including on assertion
            # failure. It must not alter the CI DB for the other smoke tests.
            transaction = connection.begin()
            sessions = sessionmaker(bind=connection, expire_on_commit=False)
            try:
                ingested = {}
                with sessions.begin() as db:
                    register_candidates(db)
                    for source_fixture in dataset["corpus"]:
                        source = db.get(KnowledgeSource, source_fixture["source_id"])
                        assert source is not None
                        result = ingest_snapshot(
                            db, source, source_fixture["html"].encode("utf-8"),
                        )
                        assert result.status == "pending_review"
                        ingested[source.id] = result

                with sessions() as db:
                    assert search_approved_passages(
                        db, query="residenza", limit=5, **scope
                    ) == []

                with sessions.begin() as db:
                    for result in ingested.values():
                        approve_version(
                            db, version_id=result.version_id,
                            expected_digest=result.sha256,
                            actor_subject="ci-synthetic-reviewer",
                            reason="Synthetic benchmark fixture reviewed for test use only.",
                        )

                scores = []
                with sessions() as db:
                    for case in dataset["cases"]:
                        found = search_approved_passages(
                            db, query=case["query"],
                            limit=case["k"], **scope,
                        )
                        citations = [passage.citation_id for passage in found]
                        expected = {
                            f"{ingested[item['source_id']].version_id}:{item['ordinal']:04d}"
                            for item in case["expected"]
                        }
                        # Every ranked result must resolve to the same exact
                        # hash-bound passage, not simply to a matching title.
                        for passage in found:
                            assert passage.source_version_id == ingested[
                                passage.source_id
                            ].version_id
                            assert resolve_approved_passage(
                                db, citation_id=passage.citation_id, **scope
                            ) == passage
                            assert passage.jurisdiction == scope["jurisdiction"]
                            assert passage.procedure_id == scope["procedure_id"]
                            assert passage.language == scope["language"]

                        scores.append(score_query(
                            case_id=case["id"],
                            expected_citations=expected,
                            returned_citations=citations,
                            k=case["k"],
                        ))

                    assert search_approved_passages(
                        db, query="residenza", limit=5,
                        jurisdiction="IT-RM-ROMA",
                        procedure_id=scope["procedure_id"],
                        language=scope["language"],
                    ) == []

                report = summarize(scores)
                assert report.positive_cases == 3
                assert report.negative_cases == 1
                # Baseline only for this simple lexical synthetic corpus.
                # These are NOT real-world RAG acceptance thresholds.
                assert report.recall_at_k == 1.0, report
                assert report.mrr_at_k == 1.0, report
                assert report.negative_abstention_rate == 1.0, report
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
