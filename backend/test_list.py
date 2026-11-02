"""The checklist follows the stored papers. It does not set the stop."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

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


def _stop(case_id):
    with engine.connect() as conn:
        return conn.execute(
            text('SELECT stop FROM "case" WHERE id = :id'),
            {"id": case_id},
        ).scalar()


def _post(client, case_id, payload):
    return client.post(
        "/v1/case/%s/upload" % case_id,
        data={"role": "title"},
        files={"file": ("paper.pdf", payload, "application/pdf")},
    )


def test_missing_title_is_the_only_gap(client):
    case_id = _open(client)
    listed = client.get("/v1/case/%s/checklist" % case_id)
    assert listed.status_code == 200
    assert listed.json() == {
        "stop": "not ready",
        "missing": "f07",
        "items": [
            {"id": "f07", "state": "missing"},
            {"id": "f09", "state": "waiting"},
        ],
    }
    assert "link" not in listed.json()
    refused = client.post("/v1/case/%s/checklist" % case_id, json={"missing": None})
    assert refused.status_code == 405
    assert _stop(case_id) == "not ready"


def test_a_read_paper_updates_only_that_row(client):
    case_id = _open(client)
    _post(client, case_id, UNREADABLE)
    blocked = client.get("/v1/case/%s/checklist" % case_id).json()
    assert blocked["items"][0] == {"id": "f07", "state": "blocked"}
    assert blocked["missing"] == "f07"
    assert blocked["stop"] == "not ready"
    _post(client, case_id, READABLE)
    read = client.get("/v1/case/%s/checklist" % case_id).json()
    assert read["items"][0] == {"id": "f07", "state": "done"}
    assert read["items"][1] == {"id": "f09", "state": "done"}
    assert read["missing"] is None
    assert _stop(case_id) == "ready to hand over"


def test_other_person_cannot_read_the_list(client):
    case_id = _open(client)
    client.cookies.clear()
    _open(client)
    rejected = client.get("/v1/case/%s/checklist" % case_id)
    assert rejected.status_code == 404
    assert _stop(case_id) == "not ready"
