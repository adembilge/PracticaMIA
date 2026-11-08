"""Unified synthetic case guide: approved retrieval, verified quotes, and abstention.

No external LLM, human source review, or government submission is exercised.
All approval operations are confined to the disposable SQLite fixture.
"""
import base64
import re

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from sqlalchemy import select

from app.config import Settings
from app.database import Base
from app.knowledge.catalog import register_candidates
from app.knowledge.model import KnowledgeSource
from app.knowledge.review_service import approve_version, revoke_version
from app.knowledge.snapshots import ingest_snapshot
from app.main import create_app
from app.preparation.models import CaseAgentTurn
from conftest import ISSUER, AUDIENCE, JWKS_URL

HTML = (
    b"<html><body><p>Test sintetico: la parola residenza appare qui. "
    b"Questa non e una istruzione governativa.</p></body></html>"
)
QUOTE = "Test sintetico: la parola residenza appare qui."


@pytest.fixture
def rag_preparation_client(tmp_path):
    api = create_app(Settings(
        database_url=f"sqlite+pysqlite:///{tmp_path / 'agent-rag.sqlite3'}",
        enable_demo_case_api=True,
        enable_knowledge_catalog_api=True,
        enable_knowledge_search_api=True,
        enable_preparation_api=True,
        enable_assistant_api=True,
        enable_agent_history_api=True,
        deployment_environment="preview",
        preparation_target="isolated_staging",
        preparation_document_key=base64.b64encode(bytes(range(32))).decode(),
        assistant_usage_hash_key="synthetic-agent-rag-hmac-key-32-chars-long",
        assistant_daily_limit=10,
        auth_issuer=ISSUER, auth_audience=AUDIENCE, auth_jwks_url=JWKS_URL,
    ))
    Base.metadata.create_all(api.state.engine)
    with TestClient(api) as client:
        yield client
    api.state.engine.dispose()


def seed_passage(client, *, approve=False):
    with client.app.state.session_factory.begin() as db:
        register_candidates(db)
        source = db.get(KnowledgeSource, "milano-residence-change")
        imported = ingest_snapshot(db, source, HTML)
    if approve:
        with client.app.state.session_factory.begin() as db:
            approve_version(
                db, version_id=imported.version_id, expected_digest=imported.sha256,
                actor_subject="synthetic-ci-reviewer",
                reason="Disposable synthetic source for offline assistant integration only.",
            )
    return imported


def use_model(client, *, claim="valid"):
    calls = {"selector": 0, "rag": 0}

    def scripted(input_value):
        if isinstance(input_value, list):
            calls["selector"] += 1
            return AIMessage(content="evidence")
        calls["rag"] += 1
        if claim == "unverified":
            return AIMessage(content="Mandatory invented rental tax payable immediately.")
        if claim == "failure":
            raise RuntimeError("Provider secrets and private error text")
        prompt = input_value.to_messages()[-1].content
        match = re.search(r"\[([0-9a-f-]{36}:[0-9]{4})\]", prompt)
        assert match is not None
        return AIMessage(content=f'[{match.group(1)}] "{QUOTE}"')

    client.app.state.assistant_model_factory = lambda: RunnableLambda(scripted)
    return calls


def make_case(client, headers):
    case = client.post("/api/v1/cases", json={}, headers=headers)
    assert case.status_code == 201, case.text
    return case.json()["id"]


def ask(client, case_id, headers, *, language="it", question="residenza"):
    return client.post(
        f"/api/v1/cases/{case_id}/preparation/guide",
        json={"question": question, "language": language},
        headers=headers,
    )


def test_approved_source_quote_in_unified_agent_and_saved_history(
    rag_preparation_client, auth_headers,
):
    client = rag_preparation_client
    alice, bob = auth_headers("alice"), auth_headers("bob")
    case_id = make_case(client, alice)
    imported = seed_passage(client, approve=True)
    calls = use_model(client)
    assert ask(client, case_id, bob).status_code == 404
    response = ask(client, case_id, alice, language="en")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["action"] == "evidence"
    assert result["status"] == "answer_generated"
    assert result["answer_status"] == "answer_generated"
    assert result["mode"] == "guided_fallback"
    assert result["answer"] == f'[{imported.version_id}:0000] "{QUOTE}"'
    assert result["references"][0]["citation_id"] == imported.version_id + ":0000"
    assert result["references"][0]["official_url"].startswith("https://")
    assert result["is_legal_assessment"] is False
    assert result["government_submission_status"] == "not_submitted"
    assert result["history_saved"] is True
    assert calls == {"selector": 0, "rag": 1}

    old = client.get(
        f"/api/v1/cases/{case_id}/preparation/conversation", headers=alice,
    )
    assert old.status_code == 200
    assert old.json()["historical_only"] is True
    assert QUOTE in old.json()["turns"][0]["answer"]
    with client.app.state.session_factory() as db:
        stored = db.scalars(select(CaseAgentTurn)).one()
        assert QUOTE.encode() not in stored.content_ciphertext
    assert client.get(
        f"/api/v1/cases/{case_id}/preparation/conversation", headers=bob,
    ).status_code == 404


def test_unapproved_and_revoked_sources_never_generate_quotes(
    rag_preparation_client, auth_headers,
):
    client = rag_preparation_client
    alice = auth_headers("alice")
    case_id = make_case(client, alice)
    imported = seed_passage(client, approve=False)
    calls = use_model(client)
    blocked = ask(client, case_id, alice)
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "insufficient_evidence"
    assert blocked.json()["answer"] is None
    assert blocked.json()["references"] == []
    assert calls["rag"] == 0

    with client.app.state.session_factory.begin() as db:
        approve_version(
            db, version_id=imported.version_id, expected_digest=imported.sha256,
            actor_subject="synthetic-ci-reviewer",
            reason="Synthetic evidence only, in isolated test database.",
        )
    assert ask(client, case_id, alice).json()["status"] == "answer_generated"
    with client.app.state.session_factory.begin() as db:
        revoke_version(
            db, version_id=imported.version_id, expected_digest=imported.sha256,
            actor_subject="synthetic-ci-reviewer",
            reason="Revoke this synthetic fixture to test denial.",
        )
    prior_calls = calls["rag"]
    revoked = ask(client, case_id, alice)
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "insufficient_evidence"
    assert revoked.json()["answer"] is None
    assert revoked.json()["references"] == []
    assert calls["rag"] == prior_calls


@pytest.mark.parametrize("behavior, expected", [
    ("unverified", "unverified_answer"),
    ("failure", "generation_unavailable"),
])
def test_hallucination_or_provider_failure_never_reaches_user(
    rag_preparation_client, auth_headers, behavior, expected,
):
    client = rag_preparation_client
    alice = auth_headers()
    case_id = make_case(client, alice)
    seed_passage(client, approve=True)
    use_model(client, claim=behavior)
    response = ask(client, case_id, alice)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == expected
    assert result["answer"] is None
    assert "invented rental tax" not in response.text
    assert "Provider secrets" not in response.text
    assert result["references"]  # verified evidence still available
    assert result["government_submission_status"] == "not_submitted"


def test_without_model_sources_appear_but_no_generated_answer(
    rag_preparation_client, auth_headers,
):
    client = rag_preparation_client
    case_id = make_case(client, auth_headers())
    seed_passage(client, approve=True)
    response = ask(client, case_id, auth_headers())
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["action"] == "evidence"
    assert result["status"] == "model_not_configured"
    assert result["answer"] is None
    assert len(result["references"]) == 1


def test_multi_sentence_search_abstains_instead_of_inventing_answer(
    rag_preparation_client, auth_headers,
):
    client = rag_preparation_client
    case_id = make_case(client, auth_headers())
    seed_passage(client, approve=True)
    use_model(client)
    query = "Official requirements for applying to change my residence in Milan when I moved to a new home with a private rental"
    result = ask(client, case_id, auth_headers(), question=query)
    assert result.status_code == 200, result.text
    assert result.json()["answer"] is None
    assert result.json()["status"] == "insufficient_evidence"


def test_english_residence_question_uses_reviewed_italian_lexical_alias(
    rag_preparation_client, auth_headers,
):
    client = rag_preparation_client
    headers = auth_headers()
    case_id = make_case(client, headers)
    imported = seed_passage(client, approve=True)
    calls = use_model(client)
    reply = ask(
        client, case_id, headers, language="en",
        question="What official sources explain residence?",
    )
    assert reply.status_code == 200, reply.text
    result = reply.json()
    assert result["action"] == "evidence"
    assert result["status"] == "answer_generated"
    assert result["answer"] == f'[{imported.version_id}:0000] "{QUOTE}"'
    assert result["government_submission_status"] == "not_submitted"
    assert calls == {"selector": 0, "rag": 1}


def test_english_alias_does_not_escape_source_approval_gate(
    rag_preparation_client, auth_headers,
):
    client = rag_preparation_client
    headers = auth_headers()
    case_id = make_case(client, headers)
    seed_passage(client, approve=False)
    calls = use_model(client)
    response = ask(
        client, case_id, headers, language="en",
        question="What official sources explain residence?",
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["references"] == []
    assert response.json()["answer"] is None
    assert calls == {"selector": 0, "rag": 0}
