"""In-process health checks. No listening port."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_health_paths():
    for path in ("/health", "/v1/health"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_wrong_method():
    response = client.post("/health")
    assert response.status_code == 405
    assert response.json() == {"code": "method_not_allowed", "message": "Method not allowed."}


def test_missing_path():
    response = client.get("/missing")
    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "Not found."}


def test_openapi_lists_health():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/health" in response.json()["paths"]
