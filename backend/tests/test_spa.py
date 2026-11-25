from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import register_spa, STATIC_DIR


def test_spa_serves_index_and_keeps_api(monkeypatch, tmp_path: Path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html>PracticaMIA shell</html>", encoding="utf-8")
    monkeypatch.setattr("app.main.STATIC_DIR", static)
    application = FastAPI()

    @application.get("/api/health")
    def health():
        return {"status": "ok", "db": "unconfigured"}

    register_spa(application)
    client = TestClient(application)
    assert client.get("/api/health").json()["db"] == "unconfigured"
    assert "PracticaMIA shell" in client.get("/").text
    assert "PracticaMIA shell" in client.get("/kayit").text
