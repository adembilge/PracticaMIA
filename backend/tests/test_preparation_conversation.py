"""Synthetic-only agent conversation persistence, tenant isolation and resumption."""
import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings
from app.database import Base
from app.main import create_app
from app.preparation.models import CaseAgentTurn, CasePreparation
from conftest import ISSUER, AUDIENCE, JWKS_URL


@pytest.fixture
def history_client(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path / 'agent-history.sqlite3'}"
    settings = Settings(
        database_url=url,
        enable_demo_case_api=True,
        enable_knowledge_catalog_api=True,
        enable_preparation_api=True,
        enable_agent_history_api=True,
        deployment_environment="preview",
        preparation_target="isolated_staging",
        preparation_document_key=base64.b64encode(bytes(range(32))).decode(),
        auth_issuer=ISSUER, auth_audience=AUDIENCE, auth_jwks_url=JWKS_URL,
    )
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as client:
        yield client
    app.state.engine.dispose()


def test_history_requires_preparation_preview():
    with pytest.raises(ValueError, match="requires isolated preparation"):
        create_app(Settings(enable_agent_history_api=True))


def test_disabled_history_endpoint_fails_closed(tmp_path, auth_headers):
    settings = Settings(
        database_url=f"sqlite+pysqlite:///{tmp_path / 'no-history.sqlite3'}",
        enable_demo_case_api=True, enable_knowledge_catalog_api=True,
        enable_preparation_api=True, deployment_environment="preview",
        preparation_target="isolated_staging",
        preparation_document_key=base64.b64encode(bytes(range(32))).decode(),
        auth_issuer=ISSUER, auth_audience=AUDIENCE, auth_jwks_url=JWKS_URL,
    )
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as client:
        case = client.post("/api/v1/cases", json={}, headers=auth_headers()).json()
        response = client.get(f"/api/v1/cases/{case['id']}/preparation/conversation",
                              headers=auth_headers())
        assert response.status_code == 404
        guide = client.post(
            f"/api/v1/cases/{case['id']}/preparation/guide",
            json={"question": "What is next?"}, headers=auth_headers(),
        )
        assert guide.status_code == 200
        assert "history_saved" not in guide.json()
        with app.state.session_factory() as db:
            assert db.scalars(select(CaseAgentTurn)).all() == []
    app.state.engine.dispose()


def test_encrypted_case_owned_turns_survive_reopen_and_delete(
    history_client, auth_headers,
):
    http = history_client
    alice, bob = auth_headers("alice"), auth_headers("bob")
    created = http.post("/api/v1/cases", json={}, headers=alice)
    assert created.status_code == 201
    case_id = created.json()["id"]
    base = f"/api/v1/cases/{case_id}/preparation"
    history_url = base + "/conversation"
    guide_url = base + "/guide"

    assert http.get(history_url).status_code == 401
    assert http.get(history_url, headers=bob).status_code == 404
    assert http.post(guide_url, json={"question": "What next?"},
                     headers=bob).status_code == 404
    assert http.get(history_url, headers=alice).json()["turns"] == []

    first = http.post(
        guide_url, json={"question": "What should I do next?", "language": "en"},
        headers=alice,
    )
    assert first.status_code == 200, first.text
    assert first.json()["history_saved"] is True
    assert first.json()["next_action"] == "answer_missing_facts"
    assert first.json()["government_submission_status"] == "not_submitted"

    second = http.post(
        guide_url, json={"question": "What is my case status?", "language": "en"},
        headers=alice,
    )
    assert second.status_code == 200, second.text
    assert second.json()["history_saved"] is True

    turns = http.get(history_url, headers=alice).json()
    assert turns["historical_only"] is True
    assert turns["government_submission_status"] == "not_submitted"
    assert len(turns["turns"]) == 2
    assert turns["turns"][0]["question"] == "What should I do next?"
    assert turns["turns"][0]["action"] == "next_step"
    assert turns["turns"][1]["action"] == "case_status"
    assert "references" not in str(turns)

    with http.app.state.session_factory() as db:
        records = db.scalars(select(CaseAgentTurn)).all()
        assert len(records) == 2
        assert all(b"What should I do next?" not in x.content_ciphertext for x in records)
        assert db.get(CasePreparation, case_id) is None  # history is not case facts

    # A fresh server instance loads history from the existing encrypted database.
    reopened = create_app(http.app.state.settings)
    try:
        with TestClient(reopened) as second_session:
            resumed = second_session.get(history_url, headers=alice)
            assert resumed.status_code == 200
            assert len(resumed.json()["turns"]) == 2
    finally:
        reopened.state.engine.dispose()

    assert http.delete(f"/api/v1/cases/{case_id}", headers=bob).status_code == 404
    assert http.delete(f"/api/v1/cases/{case_id}", headers=alice).status_code == 204
    with http.app.state.session_factory() as db:
        assert db.scalars(select(CaseAgentTurn).where(
            CaseAgentTurn.case_id == case_id,
        )).all() == []


def test_history_is_bounded_and_does_not_confirm_case_facts(
    history_client, auth_headers,
):
    http, headers = history_client, auth_headers()
    case_id = http.post("/api/v1/cases", json={}, headers=headers).json()["id"]
    base = f"/api/v1/cases/{case_id}/preparation"
    for i in range(25):
        answer = http.post(
            base + "/guide", json={"question": f"What is next step {i}?"},
            headers=headers,
        )
        assert answer.status_code == 200, answer.text
    turns = http.get(base + "/conversation", headers=headers).json()["turns"]
    assert len(turns) == 20
    assert turns[0]["question"] == "What is next step 5?"
    assert turns[-1]["question"] == "What is next step 24?"
    preparation = http.get(base, headers=headers).json()
    assert preparation["confirmed_facts"] == {}
    assert preparation["intake"]["next_question"]["field"] == "citizenship_class"
