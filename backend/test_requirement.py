"""Requirement citations. An unreviewed row stays out of the trusted set."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import app
from auth import engine
from ingest import chunk
from requirement import citation_id

REJECTED = {"code": "rejected", "message": "That field is not accepted."}
INVALID = {"code": "unauthorized", "message": "The session is not valid."}
FILE = "docs/research/DOCUMENTS.md"


@pytest.fixture
def client():
    test_client = TestClient(app)
    yield test_client
    test_client.cookies.clear()


def _sign_in(client):
    person_id = client.post("/v1/person").json()["id"]
    case_id = "case-" + person_id
    with engine.begin() as conn:
        conn.execute(
            text(
                'INSERT INTO "case" (id, person_id, stop) VALUES (:id, :person_id, :stop)'
            ),
            {"id": case_id, "person_id": person_id, "stop": "not ready"},
        )
    opened = client.post("/v1/session", json={"person_id": person_id, "case_id": case_id})
    assert opened.status_code == 200
    return person_id


def _passage(client):
    person_id = _sign_in(client)
    source_id = "src-" + person_id
    created = client.post("/v1/source", json={"id": source_id})
    assert created.status_code == 200
    version = client.post("/v1/source/" + source_id + "/version")
    assert version.status_code == 200
    version_id = version.json()["id"]
    reviewed = client.post("/v1/source/" + source_id + "/version/" + version_id + "/review")
    assert reviewed.status_code == 200
    rows = chunk(source_id, version_id, [("Alpha", "alpha token")])
    written = client.post(
        "/v1/source/%s/version/%s/passages" % (source_id, version_id),
        json={"passages": rows},
    )
    assert written.status_code == 200
    return source_id, version_id, written.json()["passages"][0]["id"]


def _count(requirement_id):
    with engine.connect() as conn:
        requirements = conn.execute(
            text("SELECT count(*) FROM requirement_row WHERE id = :id"),
            {"id": requirement_id},
        ).scalar()
        citations = conn.execute(
            text("SELECT count(*) FROM citation WHERE requirement_row_id = :id"),
            {"id": requirement_id},
        ).scalar()
    return requirements, citations


def test_requirement_cites_passage(client):
    closed = client.post("/v1/requirement", json={"id": "req", "file": FILE, "passages": ["x"]})
    assert closed.status_code == 401
    assert closed.json() == INVALID
    source_id, version_id, passage_id = _passage(client)
    requirement_id = "req-" + source_id
    promoted = client.post(
        "/v1/requirement",
        json={
            "id": requirement_id,
            "file": FILE,
            "passages": [passage_id],
            "review_status": "trusted",
        },
    )
    assert promoted.status_code == 400
    assert promoted.json() == REJECTED
    assert _count(requirement_id) == (0, 0)
    body = {"id": requirement_id, "file": FILE, "passages": [passage_id]}
    loaded = client.post("/v1/requirement", json=body)
    assert loaded.status_code == 200
    assert loaded.json()["id"] == requirement_id
    assert loaded.json()["file"] == FILE
    assert loaded.json()["review_status"] == "unreviewed"
    citation = loaded.json()["citations"][0]
    assert citation["id"] == citation_id(requirement_id, passage_id)
    assert citation["passage_id"] == passage_id
    assert citation["source_id"] == source_id
    assert citation["source_version_id"] == version_id
    assert citation["section"] == "Alpha"
    assert citation["review_status"] == "unreviewed"
    again = client.post("/v1/requirement", json=body)
    assert again.status_code == 200
    assert again.json()["citations"][0]["id"] == citation["id"]
    assert _count(requirement_id) == (1, 1)
    other_file = client.post(
        "/v1/requirement",
        json={"id": requirement_id, "file": "docs/research/DEADLINES.md", "passages": [passage_id]},
    )
    assert other_file.status_code == 400
    assert other_file.json() == REJECTED
    missing = client.post(
        "/v1/requirement",
        json={"id": requirement_id, "file": FILE, "passages": ["missing-passage"]},
    )
    assert missing.status_code == 400
    assert missing.json() == REJECTED
    assert _count(requirement_id) == (1, 1)
    invalidated = client.post(
        "/v1/source/%s/version/%s/invalidate" % (source_id, version_id)
    )
    assert invalidated.status_code == 200
    blocked_id = "req-blocked-" + source_id
    blocked = client.post(
        "/v1/requirement",
        json={"id": blocked_id, "file": FILE, "passages": [passage_id]},
    )
    assert blocked.status_code == 400
    assert blocked.json() == REJECTED
    assert _count(blocked_id) == (0, 0)
    read = client.get("/v1/requirement/" + requirement_id)
    assert read.status_code == 200
    assert read.json()["review_status"] == "unreviewed"
    kept = read.json()["citations"][0]
    assert kept["passage_id"] == passage_id
    assert kept["source_version_id"] == version_id
    assert kept["section"] == "Alpha"
    deleted = client.delete("/v1/person")
    assert deleted.status_code == 200
    _sign_in(client)
    still = client.get("/v1/requirement/" + requirement_id)
    assert still.status_code == 200
    assert still.json()["file"] == FILE
    assert still.json()["citations"][0]["passage_id"] == passage_id
