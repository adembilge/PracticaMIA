import os

import pytest
from fastapi.testclient import TestClient

from app.main import app, probe_db


def test_health_without_database(monkeypatch):
    monkeypatch.setattr("app.main.probe_db", lambda: "unconfigured")
    body = TestClient(app).get("/api/health").json()
    assert body == {"status": "ok", "db": "unconfigured"}


def test_health_marks_down(monkeypatch):
    monkeypatch.setattr("app.main.probe_db", lambda: "down")
    body = TestClient(app).get("/api/health").json()
    assert body == {"status": "degraded", "db": "down"}


def test_probe_unconfigured_when_keys_missing(monkeypatch):
    from app.config import Settings

    monkeypatch.setattr(
        "app.main.get_settings",
        lambda: Settings(supabase_url="", supabase_service_role_key=""),
    )
    assert probe_db() == "unconfigured"


@pytest.mark.integration
def test_probe_live():
    if not os.environ.get("SUPABASE_URL"):
        pytest.skip("supabase is not configured")
    assert probe_db() == "ok"