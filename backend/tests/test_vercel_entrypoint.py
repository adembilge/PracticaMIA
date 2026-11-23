"""The Vercel function entrypoint exposes the existing FastAPI application."""
from fastapi.testclient import TestClient

from app.config import Settings


def test_task_api_flag_prefers_canonical_and_supports_legacy(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_CASE_API", "1")
    monkeypatch.setenv("ENABLE_TASK_API", "0")
    assert Settings.from_env().enable_task_api is False

    monkeypatch.delenv("ENABLE_TASK_API")
    assert Settings.from_env().enable_task_api is True


def test_vercel_entrypoint_has_health_endpoint(monkeypatch):
    monkeypatch.setenv("ENABLE_TASK_API", "0")
    # index.app is the exact FastAPI object imported by Vercel.
    from index import app

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "service": "practicamia-backend",
        }
        assert client.post("/api/v1/conversations/tasks", json={}).status_code == 404
