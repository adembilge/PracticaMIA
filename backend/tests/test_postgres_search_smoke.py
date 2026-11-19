"""Real PostgreSQL full-text integration test on disposable CI database.

This smoke test never touches production Neon or live municipal websites.
"""
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.agent.answer_evidence import AnswerEvidenceScope, revalidate_answer_evidence
from app.agent.catalogue_evidence import catalogue_passage
from app.agent.contract import AnswerResult
from app.knowledge.catalog import register_candidates
from app.knowledge.model import KnowledgeSource
from app.knowledge.review_service import approve_version, revoke_version
from app.knowledge.search import resolve_approved_passage, search_approved_passages
from app.knowledge.service_areas import CaseLocation
from app.knowledge.snapshots import ingest_snapshot
from test_service_areas import area

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_SMOKE") != "1",
    reason="requires migrated disposable PostgreSQL database",
)

HTML = (
    b"<html><body><h1>Trasloco a Milano</h1>"
    b"<p>Il cambio di residenza richiede una procedura sintetica."
    b" Questo testo serve esclusivamente al test di ricerca PostgreSQL.</p>"
    b"</body></html>"
)
SCOPE = {
    "jurisdiction": "IT-MI-MILANO",
    "procedure_id": "milan_residence_change",
    "language": "it",
}


def test_postgres_gin_search_and_citation_revocation():
    engine = create_engine(os.environ["DATABASE_URL"])
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with engine.connect() as connection:
            index_name = connection.execute(
                text("SELECT to_regclass('ix_knowledge_passages_fts_simple')")
            ).scalar()
            assert index_name == "ix_knowledge_passages_fts_simple"

        with factory.begin() as db:
            register_candidates(db)
            source = db.get(KnowledgeSource, "milano-residence-change")
            ingested = ingest_snapshot(db, source, HTML)

        with factory() as db:
            assert search_approved_passages(
                db, query="residenza", limit=5, **SCOPE
            ) == []

        with factory.begin() as db:
            approve_version(
                db, version_id=ingested.version_id,
                expected_digest=ingested.sha256,
                actor_subject="ci-reviewer",
                reason="Reviewed an isolated synthetic source in disposable PostgreSQL.",
            )

        with factory() as db:
            results = search_approved_passages(
                db, query="residenza", limit=5, **SCOPE
            )
            assert results
            evidence = results[0]
            assert evidence.source_id == "milano-residence-change"
            assert evidence.source_version_id == ingested.version_id
            assert evidence.citation_id == evidence.passage_id
            assert "residenza" in evidence.content.lower()
            assert resolve_approved_passage(
                db, citation_id=evidence.citation_id, **SCOPE
            ) == evidence
            assert search_approved_passages(
                db, query="residenza", jurisdiction="IT-RM-ROMA",
                procedure_id="milan_residence_change", language="it", limit=5,
            ) == []
            assert search_approved_passages(
                db, query="nonexistentword", limit=5, **SCOPE
            ) == []

        citation = catalogue_passage(evidence).citation
        answer = AnswerResult(
            explanation="Synthetic source text.",
            verification_status="insufficient_evidence", citations=[citation],
        )
        scope = AnswerEvidenceScope(
            procedure_id=citation.procedure_id,
            case_locations={"destination": CaseLocation(municipality_id=citation.location_id, confirmed=True)},
            confirmed_dates={}, confirmed_circumstances={},
            assignments=(area(
                procedure_id=citation.procedure_id, evidence_ref=citation.passage_id,
                unit_ids=(citation.location_id,),
            ),),
        )
        with factory.begin() as db:
            assert revalidate_answer_evidence(db, answer, scope=scope, language="it") == answer
            with pytest.raises(OperationalError) as blocked, factory.begin() as reviewer:
                reviewer.execute(text("SET LOCAL lock_timeout = '500ms'"))
                revoke_version(
                    reviewer, version_id=ingested.version_id, expected_digest=ingested.sha256,
                    actor_subject="ci-reviewer", reason="Synthetic concurrent withdrawal.",
                )
            assert blocked.value.orig.sqlstate == "55P03"

        with factory.begin() as db:
            revoke_version(
                db, version_id=ingested.version_id,
                expected_digest=ingested.sha256,
                actor_subject="ci-reviewer",
                reason="Revoke a synthetic source after full-text search test.",
            )

        with factory() as db:
            assert search_approved_passages(
                db, query="residenza", limit=5, **SCOPE
            ) == []
            assert resolve_approved_passage(
                db, citation_id=evidence.citation_id, **SCOPE
            ) is None
            assert revalidate_answer_evidence(db, answer, scope=scope, language="it").citations == []
    finally:
        engine.dispose()
