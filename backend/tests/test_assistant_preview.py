"""Authenticated assistant preview tests using only synthetic local evidence."""
import re

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.config import Settings
from app.database import Base
from app.knowledge.catalog import register_candidates
from app.knowledge.model import KnowledgeSource
from app.knowledge.review_service import approve_version, revoke_version
from app.knowledge.snapshots import ingest_snapshot
from app.main import create_app

ENDPOINT = "/api/v1/cases/{}/assistant/ask"
SYNTHETIC_HTML = (
    b"<html><body><p>Test sintetico: la parola residenza appare qui. "
    b"Questa non e una istruzione governativa.</p></body></html>"
)


@pytest.fixture
def assistant_client(tmp_path, token_factory):
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{tmp_path / 'assistant.sqlite3'}",
        enable_demo_case_api=True, enable_knowledge_catalog_api=True,
        enable_knowledge_search_api=True, enable_assistant_api=True,
        assistant_usage_hash_key="synthetic-test-daily-usage-hmac-key-32-chars",
        auth_issuer="https://identity.example.test/",
        auth_audience="https://api.practicamia.example.test",
        auth_jwks_url="https://identity.example.test/.well-known/jwks.json",
    )
    api = create_app(settings)
    Base.metadata.create_all(api.state.engine)
    with TestClient(api) as http:
        yield http
    api.state.engine.dispose()


def case_id(http, headers):
    response = http.post("/api/v1/cases", json={}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def index_synthetic(http):
    with http.app.state.session_factory.begin() as db:
        register_candidates(db)
        source = db.get(KnowledgeSource, "milano-residence-change")
        return ingest_snapshot(db, source, SYNTHETIC_HTML)


def post(http, case, headers, question="residenza", language="it"):
    return http.post(
        ENDPOINT.format(case), json={"question": question, "language": language},
        headers=headers,
    )


def test_preview_route_is_disabled_by_default_and_rejected_in_production():
    with TestClient(create_app(Settings())) as http:
        assert http.post(ENDPOINT.format("00000000-0000-0000-0000-000000000001")).status_code == 404
    with pytest.raises(ValueError, match="Assistant requires"):
        create_app(Settings(enable_assistant_api=True))
    with pytest.raises(ValueError, match="cannot be enabled in production"):
        create_app(Settings(enable_assistant_api=True, deployment_environment="production"))


def test_case_bound_auth_and_cross_user_isolation(assistant_client, auth_headers):
    owned = case_id(assistant_client, auth_headers("alice"))
    url = ENDPOINT.format(owned)
    assert assistant_client.post(url, json={"question": "residenza"}).status_code == 401
    assert post(assistant_client, owned, auth_headers("bob")).status_code == 404
    assert post(assistant_client, owned, auth_headers("alice")).status_code == 200
    assert post(assistant_client, owned, auth_headers("alice")).json() == {
        "status": "insufficient_evidence", "answer": None, "sources": [], "is_demo": True,
    }
    assert assistant_client.get(url, headers=auth_headers("alice")).status_code == 405
    assert post(assistant_client, owned, auth_headers("alice"), question="!!!").status_code == 422
    assert post(assistant_client, owned, auth_headers("alice"), question="x " * 13).status_code == 422
    assert assistant_client.post(
        url, json={"question": "residenza", "jurisdiction": "IT-RM-ROMA"},
        headers=auth_headers("alice"),
    ).status_code == 422


def test_pending_review_never_calls_model(assistant_client, auth_headers):
    owned = case_id(assistant_client, auth_headers())
    index_synthetic(assistant_client)
    calls = []
    assistant_client.app.state.assistant_model_factory = lambda: (
        calls.append("factory-called") or RunnableLambda(lambda _: AIMessage(content="bad"))
    )
    result = post(assistant_client, owned, auth_headers())
    assert result.status_code == 200
    assert result.json()["status"] == "insufficient_evidence"
    assert result.json()["sources"] == []
    assert calls == []


def test_model_not_configured_only_after_approval(assistant_client, auth_headers):
    owned = case_id(assistant_client, auth_headers())
    item = index_synthetic(assistant_client)
    with assistant_client.app.state.session_factory.begin() as db:
        approve_version(
            db, version_id=item.version_id, expected_digest=item.sha256,
            actor_subject="synthetic-ci-reviewer",
            reason="Synthetic fixture approved solely inside a disposable test database.",
        )
    response = post(assistant_client, owned, auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "model_not_configured"
    assert payload["answer"] is None
    assert len(payload["sources"]) == 1
    assert payload["sources"][0]["citation_id"].startswith(item.version_id + ":")
    assert "sintetico" in payload["sources"][0]["excerpt"].lower()


def test_generated_response_requires_exact_citations_then_revocation_abstains(
    assistant_client, auth_headers,
):
    owned = case_id(assistant_client, auth_headers())
    item = index_synthetic(assistant_client)
    with assistant_client.app.state.session_factory.begin() as db:
        approve_version(
            db, version_id=item.version_id, expected_digest=item.sha256,
            actor_subject="synthetic-ci-reviewer",
            reason="Approve only a synthetic, disposable test fixture.",
        )
    calls = []
    def fake_llm(prompt):
        calls.append(prompt)
        prompt_text = prompt.to_messages()[-1].content
        citation = re.search(r"\[([0-9a-f-]{36}:[0-9]{4})\]", prompt_text)
        assert citation is not None
        return AIMessage(
            content=citation.group(0)
            + ' "Test sintetico: la parola residenza appare qui."'
        )

    assistant_client.app.state.assistant_model_factory = lambda: RunnableLambda(fake_llm)
    response = post(assistant_client, owned, auth_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "answer_generated"
    assert payload["is_demo"] is True
    assert payload["sources"][0]["citation_id"] in payload["answer"]
    assert len(calls) == 1

    assistant_client.app.state.assistant_model_factory = lambda: RunnableLambda(
        lambda _: AIMessage(content="Uncited assertion")
    )
    assert post(assistant_client, owned, auth_headers()).json()["status"] == "unverified_answer"

    assistant_client.app.state.assistant_model_factory = lambda: RunnableLambda(
        lambda _: AIMessage(
            content="Fake citation [00000000-0000-0000-0000-000000000000:0000]"
        )
    )
    assert post(assistant_client, owned, auth_headers()).json()["status"] == "unverified_answer"

    with assistant_client.app.state.session_factory.begin() as db:
        revoke_version(
            db, version_id=item.version_id, expected_digest=item.sha256,
            actor_subject="synthetic-ci-reviewer",
            reason="Revocation test on a local synthetic source.",
        )
    called = []
    assistant_client.app.state.assistant_model_factory = lambda: (
        called.append(True) or RunnableLambda(fake_llm)
    )
    after = post(assistant_client, owned, auth_headers())
    assert after.status_code == 200
    assert after.json()["status"] == "insufficient_evidence"
    assert after.json()["sources"] == []
    assert called == []


def test_model_failure_is_sanitized(assistant_client, auth_headers):
    owned = case_id(assistant_client, auth_headers())
    item = index_synthetic(assistant_client)
    with assistant_client.app.state.session_factory.begin() as db:
        approve_version(
            db, version_id=item.version_id, expected_digest=item.sha256,
            actor_subject="synthetic-ci-reviewer",
            reason="Synthetic fixture, no official content.",
        )
    def broken(_):
        raise RuntimeError("Never expose model provider secrets")
    assistant_client.app.state.assistant_model_factory = lambda: RunnableLambda(broken)
    result = post(assistant_client, owned, auth_headers())
    assert result.json()["status"] == "generation_unavailable"
    assert "secrets" not in result.text
