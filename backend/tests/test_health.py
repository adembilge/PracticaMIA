from fastapi.testclient import TestClient
from app.main import app, probe_db

def test_health_without_database():
    client = TestClient(app)
    body = client.get("/api/health").json()
    assert body == {"status": "ok", "db": "unconfigured"}

def test_probe_db_is_unconfigured_until_phase_2():
    assert probe_db() == "unconfigured"
