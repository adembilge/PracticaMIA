"""Preview transport and case-free worker on the migrated disposable CI PostgreSQL database.

The test verifies durable encrypted queueing, independent JWT ownership,
idempotent first messages, one no-case LangGraph run, and deletion cleanup.
It does not use real Auth0 or authorize production.
"""
import base64
from hashlib import sha256
import os
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.agent.chat_graph import build_chat_executor
from app.agent.worker import run_worker_step
from app.knowledge.entity_matching import CatalogueName
from app.rules.engine import JURISDICTION, PROCEDURE
from app.auth.tokens import Principal
from app.agent.run_requests import AgentRunRequest
from app.agent.threads import AgentThread
from app.config import Settings
from app.main import create_app
from conftest import ISSUER, AUDIENCE, JWKS_URL

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_SMOKE") != "1",
    reason="requires disposable CI PostgreSQL with agent migrations",
)


def test_gated_preview_mount_accepts_encrypted_first_message_and_rejects_foreign_owner(auth_headers, monkeypatch):
    database = os.environ["DATABASE_URL"]
    settings = Settings(
        database_url=database,
        enable_task_api=True,
        enable_knowledge_catalog_api=True,
        enable_preparation_api=True,
        enable_agent_history_api=True,
        enable_agent_preview_api=True,
        deployment_environment="preview",
        deployment_git_branch="preview/auth-review-isolated",
        preparation_target="isolated_staging",
        preparation_database_fingerprint=sha256(database.encode()).hexdigest(),
        preparation_document_key=base64.b64encode(bytes(range(32))).decode(),
        agent_preview_journal_key=base64.b64encode(bytes(range(32, 64))).decode(),
        auth_issuer=ISSUER, auth_audience=AUDIENCE, auth_jwks_url=JWKS_URL,
    )
    app = create_app(settings)
    owner = auth_headers("phase4-preview-transport-owner")
    foreign = auth_headers("phase4-preview-transport-other")
    message = {
        "client_message_id": str(uuid4()), "text": "How can I change my address in Milan?",
        "language": "en",
    }
    thread_id = None
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/agent/conversations", headers=owner, json=message)
            assert response.status_code == 202, response.text
            saved = response.json()
            thread_id, run_id = saved["thread_id"], saved["run_id"]
            assert client.post("/api/v1/agent/conversations", headers=owner, json=message).json() == saved

            history_url = f"/api/v1/agent/threads/{thread_id}/history"
            run_url = f"/api/v1/agent/threads/{thread_id}/runs/{run_id}"
            mine = client.get(history_url, headers=owner)
            assert mine.status_code == 200, mine.text
            assert mine.json()["items"][0]["user_message"] == message["text"]
            assert mine.headers["Cache-Control"] == "private, no-store"
            snapshot = client.get(run_url, headers=owner)
            assert snapshot.status_code == 200
            assert snapshot.json()["status"] == "queued"
            # There is intentionally no fake answer or auto-started worker.
            assert snapshot.json()["result"] is None

            recent = client.get("/api/v1/agent/conversations/recent", headers=owner)
            assert recent.status_code == 200
            assert any(item["thread_id"] == thread_id for item in recent.json()["items"])
            foreign_recent = client.get("/api/v1/agent/conversations/recent", headers=foreign)
            assert foreign_recent.status_code == 200
            assert all(item["thread_id"] != thread_id for item in foreign_recent.json()["items"])
            for path in (history_url, run_url, run_url + "/events"):
                assert client.get(path, headers=foreign).status_code == 404
                assert client.get(path).status_code == 401

            # The new BFF will never forward this legacy internal picker route.
            assert client.get(f"/api/v1/agent/threads/{thread_id}/cases", headers=foreign).status_code == 404
            with app.state.session_factory() as db:
                row = db.get(AgentRunRequest, run_id)
                assert row is not None
                assert message["text"].encode() not in row.message_ciphertext
            # The chat graph is real; keep this PostgreSQL transport smoke
            # deterministic by returning no approved passages from its read-only search.
            import app.agent.chat_graph as chat_graph
            monkeypatch.setattr(chat_graph, "search_approved_passages", lambda *args, **kwargs: [])
            names = (
                CatalogueName(
                    catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
                    name="change my address", kind="search_variant", evidence_ref="synthetic-alias",
                    approved_for_search=True,
                ),
                CatalogueName(
                    catalogue_id=JURISDICTION, entity_type="municipality", display_name="Milano",
                    name="Milan", kind="search_variant", evidence_ref="synthetic-alias",
                    approved_for_search=True,
                ),
            )
            execute = build_chat_executor(app.state.session_factory, catalogue_names=names)
            updated = run_worker_step(
                app.state.session_factory, thread_id=UUID(thread_id), run_id=UUID(run_id),
                principal=Principal("phase4-preview-transport-owner"),
                key=bytes(range(32, 64)), execute=execute,
            )
            assert updated.status == "completed"
            finished = client.get(run_url, headers=owner)
            assert finished.status_code == 200
            assert finished.json()["status"] == "completed"
            answer = finished.json()["result"]
            assert answer["verification_status"] == "insufficient_evidence"
            assert answer["citations"] == [] and answer["official_channel"] is None
            assert client.get(run_url, headers=foreign).status_code == 404
            final_history = client.get(history_url, headers=owner).json()["items"][0]
            assert final_history["answer"]["verification_status"] == "insufficient_evidence"
    finally:
        if thread_id:
            with app.state.session_factory.begin() as db:
                if row := db.get(AgentThread, thread_id):
                    db.delete(row)
        app.state.engine.dispose()
