"""The Vercel function entrypoint exposes the existing FastAPI application."""
from fastapi.testclient import TestClient


def test_vercel_entrypoint_has_health_endpoint(monkeypatch):
    monkeypatch.setenv("ENABLE_DEMO_CASE_API", "0")
    # index.app is the exact FastAPI object imported by Vercel.
    from index import app

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "service": "practicamia-backend",
        }
        assert client.post("/api/v1/cases", json={}).status_code == 404
