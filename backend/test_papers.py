"""A paper can be replaced. The stop follows the check."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import upload
from app import app
from auth import engine

SUPPORTED = {
    "language": "English",
    "f02": "Yes",
    "f04": "Via Torino 20, Milano",
    "f05": "named tenant",
}
UNREADABLE = b"%PDF-1.4\n%%EOF"
READABLE = (
    b"%PDF-1.4\n"
    b"(Name: Ada Lovelace) Tj\n"
    b"(Via Torino 20, Milano) Tj\n"
    b"%%EOF"
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PAPERPILOT_UPLOAD_DIR", str(tmp_path))
    test_client = TestClient(app)
    yield test_client
    test_client.cookies.clear()


def _open(client):
    person_id = client.post("/v1/person").json()["id"]
    opened = client.post("/v1/case", json={"person_id": person_id, **SUPPORTED})
    case_id = opened.json()["id"]
    client.post("/v1/session", json={"person_id": person_id, "case_id": case_id})
    return case_id


def _post(client, case_id, payload, role="title"):
    return client.post(
        "/v1/case/%s/upload" % case_id,
        data={"role": role},
        files={"file": ("paper.pdf", payload, "application/pdf")},
    )


def _stop(case_id):
    with engine.connect() as conn:
        return conn.execute(
            text('SELECT stop FROM "case" WHERE id = :id'),
            {"id": case_id},
        ).scalar()


def test_unreadable_then_a_readable_replacement(client):
    case_id = _open(client)
    listed = client.get("/v1/case/%s/uploads" % case_id)
    assert listed.status_code == 200
    assert listed.json() == {"stop": "not ready", "uploads": []}
    failed = client.post("/v1/case/%s/upload" % case_id, content=b"")
    assert failed.status_code == 400
    assert client.get("/v1/case/%s/uploads" % case_id).json()["uploads"] == []
    created = _post(client, case_id, UNREADABLE)
    assert created.status_code == 200
    unread = client.get("/v1/case/%s/uploads" % case_id).json()
    assert unread["stop"] == "not ready"
    assert unread["uploads"] == [{"id": created.json()["id"], "role": "title", "status": "unreadable"}]
    assert "path" not in unread
    replaced = _post(client, case_id, READABLE)
    assert replaced.status_code == 200
    read = client.get("/v1/case/%s/uploads" % case_id).json()
    assert read["uploads"] == [{"id": replaced.json()["id"], "role": "title", "status": "read"}]
    assert _stop(case_id) == "ready to hand over"
    assert upload.LIMIT == 10 * 1024 * 1024


def test_other_person_cannot_list_papers(client):
    case_id = _open(client)
    _post(client, case_id, READABLE)
    client.cookies.clear()
    _open(client)
    rejected = client.get("/v1/case/%s/uploads" % case_id)
    assert rejected.status_code == 404
    assert _stop(case_id) == "ready to hand over"
