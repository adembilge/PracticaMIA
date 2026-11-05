"""Offline tests for the LangChain RAG context and ranked evidence fusion."""
from dataclasses import replace
from datetime import datetime, timezone

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.knowledge.rag_chain import answer_from_passages
from app.knowledge.search import EvidencePassage
from app.knowledge.vector_search import (
    EMBEDDING_DIMENSIONS, _encode_vector, _model_id, fuse_ranked_passages,
)


def passage(index: int = 1) -> EvidencePassage:
    now = datetime.now(timezone.utc)
    return EvidencePassage(
        citation_id=f"00000000-0000-0000-0000-000000000001:{index:04}",
        passage_id=f"00000000-0000-0000-0000-000000000001:{index:04}",
        source_id="milano-residence-change",
        source_version_id="00000000-0000-0000-0000-000000000001",
        source_revision=1, institution="Comune di Milano",
        title="Synthetic test source", official_url="https://www.comune.milano.it/test",
        jurisdiction="IT-MI-MILANO", procedure_id="milan_residence_change",
        language="it", section_path="Page 1",
        content="Test-only synthetic evidence, not official guidance.",
        passage_sha256="a" * 64, source_sha256="b" * 64,
        reviewed_at=now, retrieved_at=now,
    )


def test_langchain_abstains_without_evidence_and_never_calls_model():
    calls = []
    model = RunnableLambda(lambda prompt: calls.append(prompt) or AIMessage(content="UNSAFE"))
    result = answer_from_passages(question="Quali documenti?", passages=[], chat_model=model)
    assert result.status == "insufficient_evidence"
    assert result.answer is None and not result.citations and not result.sources
    assert calls == []


def test_langchain_uses_reviewed_evidence_with_exact_citation_metadata():
    calls = []
    def fake_response(prompt):
        calls.append(prompt.to_messages())
        return AIMessage(content=f"Synthetic only [{passage().citation_id}]")
    result = answer_from_passages(
        question="Quali documenti?", passages=[passage()],
        chat_model=RunnableLambda(fake_response),
    )
    assert result.status == "answer_generated"
    assert result.citations == (passage().citation_id,)
    assert result.sources[0].metadata["source_sha256"] == "b" * 64
    assert result.sources[0].metadata["official_url"].startswith("https://")
    assert len(calls) == 1
    assert passage().citation_id in calls[0][-1].content


def test_rag_context_length_and_question_limits_fail_closed():
    model = RunnableLambda(lambda _: AIMessage(content="unused"))
    with pytest.raises(ValueError):
        answer_from_passages(question="", passages=[passage()], chat_model=model)
    with pytest.raises(ValueError):
        answer_from_passages(
            question="a", passages=[replace(passage(), content="x" * 10001)],
            chat_model=model,
        )


def test_rank_fusion_deduplicates_and_rewards_both_modalities():
    a, b, c = passage(1), passage(2), passage(3)
    result = fuse_ranked_passages([a, b], [c, b, b], limit=3)
    assert len(result) == 3
    assert result[0].citation_id == b.citation_id
    assert len({x.citation_id for x in result}) == 3


def test_embedding_encoding_rejects_invalid_shape_numbers_and_model_ids():
    assert _encode_vector([1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 1)).startswith("[1,0,")
    for bad in ([0.0] * EMBEDDING_DIMENSIONS, [1.0, 2.0], [float("nan")] * EMBEDDING_DIMENSIONS):
        with pytest.raises(ValueError):
            _encode_vector(bad)
    for name in ("", "; DROP TABLE sources;", " "):
        with pytest.raises(ValueError):
            _model_id(name)


def test_end_to_end_two_step_rag_never_calls_model_without_review(client):
    from app.knowledge.catalog import register_candidates
    from app.knowledge.model import KnowledgeSource
    from app.knowledge.review_service import approve_version, revoke_version
    from app.knowledge.rag_service import answer_reviewed_question
    from app.knowledge.snapshots import ingest_snapshot

    calls = []
    def fake_model(prompt):
        calls.append(prompt)
        return AIMessage(content="Synthetic answer with citations")
    model = RunnableLambda(fake_model)
    scope = {
        "jurisdiction": "IT-MI-MILANO",
        "procedure_id": "milan_residence_change",
        "language": "it",
    }
    factory = client.app.state.session_factory
    with factory.begin() as db:
        register_candidates(db)
        src = db.get(KnowledgeSource, "milano-residence-change")
        doc = ingest_snapshot(
            db, src, b"<p>Procedura sintetica di prova non ufficiale.</p>",
        )

    with factory() as db:
        result = answer_reviewed_question(
            db, question="sintetica", chat_model=model, **scope,
        )
        assert result.status == "insufficient_evidence"
        assert calls == []

    with factory.begin() as db:
        approve_version(
            db, version_id=doc.version_id, expected_digest=doc.sha256,
            actor_subject="test-reviewer",
            reason="Synthetic evidence fixture in an isolated test.",
        )
    with factory() as db:
        result = answer_reviewed_question(
            db, question="sintetica", chat_model=model, **scope,
        )
        assert result.status == "answer_generated"
        assert len(result.citations) == 1
        assert len(calls) == 1

    with factory.begin() as db:
        revoke_version(
            db, version_id=doc.version_id, expected_digest=doc.sha256,
            actor_subject="test-reviewer",
            reason="Revoke synthetic fixture before final query.",
        )
    with factory() as db:
        result = answer_reviewed_question(
            db, question="sintetica", chat_model=model, **scope,
        )
        assert result.status == "insufficient_evidence"
        assert len(calls) == 1
