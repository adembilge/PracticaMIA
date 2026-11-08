"""One complete synthetic agent MVP journey using authenticated API routes.

This is an OFFLINE integration test with a deterministic mock LLM and
fictional source/rules/documents. It is NOT a real-model, real-user, Auth0
browser, legal correctness, or government submission acceptance test.
"""
import base64
from datetime import datetime, timezone
from io import BytesIO
import re
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from reportlab.pdfgen import canvas
from sqlalchemy import select

from app.config import Settings
from app.database import Base
from app.knowledge.catalog import register_candidates
from app.knowledge.model import KnowledgeSource
from app.knowledge.review_service import approve_version
from app.knowledge.snapshots import ingest_snapshot
from app.main import create_app
from app.preparation import router as preparation_router
from app.preparation.intake import QUESTIONS
from app.preparation.models import CaseAgentTurn, CasePreparation
from conftest import ISSUER, AUDIENCE, JWKS_URL
from test_preparation_rules import synthetic_catalog


QUOTE = "Test sintetico: la parola residenza appare qui."
HTML = (
    b"<html><body><p>Test sintetico: la parola residenza appare qui. "
    b"Questa non e una istruzione governativa.</p></body></html>"
)
ADDRESS = "Synthetic Via 10 Milano"


@pytest.fixture
def agent_journey_client(tmp_path, monkeypatch):
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{tmp_path / 'agent-mvp-e2e.sqlite3'}",
        enable_demo_case_api=True,
        enable_knowledge_catalog_api=True,
        enable_knowledge_search_api=True,
        enable_preparation_api=True,
        enable_assistant_api=True,
        enable_agent_history_api=True,
        deployment_environment="preview",
        preparation_target="isolated_staging",
        preparation_document_key=base64.b64encode(bytes(range(32))).decode(),
        assistant_usage_hash_key="fictional-agent-e2e-usage-hmac-key-32-chars",
        assistant_daily_limit=30,
        auth_issuer=ISSUER, auth_audience=AUDIENCE, auth_jwks_url=JWKS_URL,
    )
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)
    # These two fakes are local-only, not the published Milan rules or a
    # reviewer approval. The signed production catalog stays untouched.
    monkeypatch.setattr(preparation_router, "current_catalog", synthetic_catalog)
    monkeypatch.setattr(
        preparation_router, "resolve_approved_passage",
        lambda *args, **kwargs: SimpleNamespace(
            title="Synthetic source for tests",
            official_url="https://example.test/synthetic",
            content="Synthetic fixture only. No administrative requirement.",
            reviewed_at=datetime(2026, 11, 6, tzinfo=timezone.utc),
        ),
    )

    with app.state.session_factory.begin() as db:
        register_candidates(db)
        source = db.get(KnowledgeSource, "milano-residence-change")
        version = ingest_snapshot(db, source, HTML)
    with app.state.session_factory.begin() as db:
        approve_version(
            db, version_id=version.version_id, expected_digest=version.sha256,
            actor_subject="synthetic-ci-reviewer",
            reason="Disposable test-only synthetic evidence; not a real approval.",
        )

    llm_calls = {"routing": 0, "quoting": 0}

    def offline_model(prompt):
        if isinstance(prompt, list):
            llm_calls["routing"] += 1
            question = prompt[-1].content.casefold()
            if "document" in question or "contratto" in question:
                return AIMessage(content="documents")
            if "status" in question or "stato" in question:
                return AIMessage(content="case_status")
            return AIMessage(content="next_step")
        llm_calls["quoting"] += 1
        text = prompt.to_messages()[-1].content
        citation = re.search(r"\[([0-9a-f-]{36}:[0-9]{4})\]", text)
        assert citation is not None
        return AIMessage(content=f'[{citation.group(1)}] "{QUOTE}"')

    app.state.assistant_model_factory = lambda: RunnableLambda(offline_model)
    with TestClient(app) as client:
        yield client, settings, llm_calls, version
    app.state.engine.dispose()


def _sample_pdf():
    data = BytesIO()
    writer = canvas.Canvas(data)
    writer.drawString(25, 750, f"Property address: {ADDRESS}")
    writer.save()
    return data.getvalue()


def _next_step(client, base, headers):
    response = client.post(
        base + "/guide", headers=headers,
        json={"question": "What should I do next?", "language": "en"},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["action"] == "next_step"
    assert result["is_legal_assessment"] is False
    assert result["government_submission_status"] == "not_submitted"
    return result


def test_full_agent_path_intake_rag_document_review_resume_and_handoff(
    agent_journey_client, auth_headers,
):
    client, settings, counts, version = agent_journey_client
    owner, stranger = auth_headers("alice"), auth_headers("bob")
    created = client.post("/api/v1/cases", json={}, headers=owner)
    assert created.status_code == 201, created.text
    case_id = created.json()["id"]
    base = f"/api/v1/cases/{case_id}/preparation"

    # Agent asks only the first unanswered, server-defined scope question.
    assert client.get(base, headers=stranger).status_code == 404
    assert client.post(base + "/guide", headers=stranger,
                       json={"question": "What should I do next?"}).status_code == 404
    initial = _next_step(client, base, owner)
    assert initial["next_action"] == "answer_missing_facts"
    assert initial["next_question"]["field"] == "citizenship_class"
    assert initial["history_saved"] is True

    # The user, never the LLM, saves facts. Product scope alone does not
    # establish official eligibility or imply submission.
    facts = {item["field"]: item["expected"] for item in QUESTIONS}
    facts.update({
        "synthetic_eligibility": "yes",
        "housing_arrangement": "fictional_rental",
        "property_address": ADDRESS,
    })
    saved = client.put(base + "/facts", headers=owner,
                       json={"confirmed_facts": facts})
    assert saved.status_code == 200, saved.text
    assert client.get(base, headers=owner).json()["intake"]["status"] == "candidate_scope_complete"
    needed = _next_step(client, base, owner)
    assert needed["next_action"] == "provide_documents"
    assert client.get(base + "/package", headers=owner).json()["package"] is None

    # RAG is the same approved, citation-bound quotation service used by
    # the independent assistant endpoint.
    evidence = client.post(
        base + "/guide", headers=owner,
        json={"question": "residenza", "language": "it"},
    )
    assert evidence.status_code == 200, evidence.text
    cited = evidence.json()
    assert cited["action"] == "evidence"
    assert cited["status"] == "answer_generated"
    assert cited["answer"] == f'[{version.version_id}:0000] "{QUOTE}"'
    assert cited["references"][0]["citation_id"] == version.version_id + ":0000"
    assert cited["government_submission_status"] == "not_submitted"
    assert counts["quoting"] == 1

    # Document contents enter only the encrypted, synthetic-only upload
    # endpoint. Extraction and document confirmation are separate steps.
    assert client.post(
        base + "/documents", headers=owner,
        data={"document_type": "fictional_agreement"},
        files={"file": ("fictional.pdf", _sample_pdf(), "application/pdf")},
    ).status_code == 403
    uploaded = client.post(
        base + "/documents",
        headers={**owner, "X-PracticaMIA-Synthetic-Only": "YES"},
        data={"document_type": "fictional_agreement"},
        files={"file": ("fictional.pdf", _sample_pdf(), "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    doc_id = uploaded.json()["id"]
    path = base + f"/documents/{doc_id}"
    parsed = client.post(path + "/extract", headers=owner)
    assert parsed.status_code == 200, parsed.text
    candidate = parsed.json()["candidates"][0]
    assert candidate["field_name"] == "property_address"
    assert client.post(
        path + "/review", headers=owner,
        json={"confirm_document": True},
    ).status_code == 409
    assert client.post(
        path + "/confirm-fields", headers=owner,
        json={"field_name": candidate["field_name"],
              "raw_value": candidate["raw_value"], "page": candidate["page"],
              "confirmed_value": ADDRESS},
    ).status_code == 200
    assert client.post(
        path + "/review", headers=owner,
        json={"confirm_document": True},
    ).json()["status"] == "confirmed"

    # Agent directs user to review, rather than submitting itself.
    ready = _next_step(client, base, owner)
    assert ready["next_action"] == "review_package"
    result = client.get(base + "/package", headers=owner).json()
    assert result["status"] == "reviewable"
    package = result["package"]
    assert package["data"]["government_submission"] == "user_only_not_submitted"
    assert client.get(base + "/handoff", headers=owner).status_code == 409
    digest = package["review_digest"]
    assert client.post(
        base + "/package/approve", headers=stranger,
        json={"review_digest": digest},
    ).status_code == 404
    approved = client.post(
        base + "/package/approve", headers=owner,
        json={"review_digest": digest},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "submission_ready"
    handoff = client.get(base + "/handoff", headers=owner)
    assert handoff.status_code == 200, handoff.text
    assert handoff.json()["status"] == "user_handoff"
    assert handoff.json()["government_status"] == "not_submitted"

    # History persists across application instances, but never becomes a
    # source of current legal facts or a substitute for confirmed inputs.
    history = client.get(base + "/conversation", headers=owner)
    assert history.status_code == 200
    assert history.json()["historical_only"] is True
    assert len(history.json()["turns"]) == 4
    assert QUOTE in history.json()["turns"][2]["answer"]
    with client.app.state.session_factory() as db:
        turns = db.scalars(select(CaseAgentTurn)).all()
        assert len(turns) == 4
        assert all(QUOTE.encode() not in x.content_ciphertext for x in turns)
    reopened = create_app(settings)
    try:
        with TestClient(reopened) as new_session:
            assert len(new_session.get(
                base + "/conversation", headers=owner,
            ).json()["turns"]) == 4
    finally:
        reopened.state.engine.dispose()

    # Changing a confirmed fact invalidates the user's reviewed digest.
    changed = {**facts, "property_address": "Different Synthetic Via 20"}
    assert client.put(base + "/facts", headers=owner,
                      json={"confirmed_facts": changed}).status_code == 200
    assert client.get(base + "/handoff", headers=owner).status_code == 409
    assert client.post(
        base + "/package/approve", headers=owner,
        json={"review_digest": digest},
    ).status_code == 409
    assert client.get(base + "/package", headers=owner).json()["package"] is None

    assert client.delete(f"/api/v1/cases/{case_id}",
                         headers=owner).status_code == 204
    with client.app.state.session_factory() as db:
        assert db.scalars(select(CaseAgentTurn).where(
            CaseAgentTurn.case_id == case_id,
        )).all() == []
        assert db.get(CasePreparation, case_id) is None


@pytest.mark.parametrize("field,value", [
    ("destination_municipality", "other"),
    ("housing_basis", "guest"),
])
def test_agent_stops_out_of_scope_without_preparation_or_submission(
    agent_journey_client, auth_headers, field, value,
):
    client, _, _, _ = agent_journey_client
    owner = auth_headers("alice")
    case_id = client.post("/api/v1/cases", json={},
                          headers=owner).json()["id"]
    base = f"/api/v1/cases/{case_id}/preparation"
    facts = {item["field"]: item["expected"] for item in QUESTIONS}
    facts[field] = value
    saved = client.put(base + "/facts", headers=owner,
                       json={"confirmed_facts": facts})
    assert saved.status_code == 200, saved.text
    answer = _next_step(client, base, owner)
    assert answer["status"] == "outside_first_candidate"
    assert answer["next_action"] == "unsupported_scope"
    assert answer["is_legal_assessment"] is False
    assert client.get(base + "/handoff", headers=owner).status_code == 409
