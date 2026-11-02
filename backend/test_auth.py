"""Session checks. The case row is inserted here because opening a case is not this task."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import app
from auth import engine

REJECTED = {"code": "rejected", "message": "That field is not accepted."}
MISSING = {"code": "not_found", "message": "Not found."}
INVALID = {"code": "unauthorized", "message": "The session is not valid."}


@pytest.fixture
def client():
    test_client = TestClient(app)
    yield test_client
    test_client.cookies.clear()


def _count(sql):
    with engine.connect() as conn:
        return conn.execute(text(sql)).scalar()


def _insert_case(person_id, case_id):
    with engine.begin() as conn:
        conn.execute(
            text('INSERT INTO "case" (id, person_id, stop) VALUES (:id, :person_id, :stop)'),
            {"id": case_id, "person_id": person_id, "stop": "not ready"},
        )


def test_empty_body_issues_id_and_password_writes_nothing(client):
    created = client.post("/v1/person")
    assert created.status_code == 200
    assert created.json()["id"]
    before = _count("SELECT count(*) FROM person")
    rejected = client.post("/v1/person", json={"password": "x"})
    assert rejected.status_code == 400
    assert rejected.json() == REJECTED
    assert _count("SELECT count(*) FROM person") == before


def test_session_cookie_reads_back(client):
    person_id = client.post("/v1/person").json()["id"]
    _insert_case(person_id, "case-own")
    opened = client.post("/v1/session", json={"person_id": person_id, "case_id": "case-own"})
    assert opened.status_code == 200
    assert opened.cookies.get("session")
    read = client.get("/v1/session")
    assert read.status_code == 200
    assert read.json() == {"person_id": person_id, "case_id": "case-own"}


def test_other_persons_case_writes_no_session(client):
    owner = client.post("/v1/person").json()["id"]
    other = client.post("/v1/person").json()["id"]
    _insert_case(owner, "case-owner")
    before = _count("SELECT count(*) FROM session")
    rejected = client.post("/v1/session", json={"person_id": other, "case_id": "case-owner"})
    assert rejected.status_code == 404
    assert rejected.json() == MISSING
    assert _count("SELECT count(*) FROM session") == before


def test_delete_removes_session_and_keeps_case(client):
    person_id = client.post("/v1/person").json()["id"]
    _insert_case(person_id, "case-del")
    client.post("/v1/session", json={"person_id": person_id, "case_id": "case-del"})
    deleted = client.delete("/v1/session")
    assert deleted.status_code == 200
    assert client.get("/v1/session").status_code == 401
    with engine.connect() as conn:
        case = conn.execute(text('SELECT id FROM "case" WHERE id = :id'), {"id": "case-del"}).first()
        session = conn.execute(
            text("SELECT id FROM session WHERE case_id = :id"),
            {"id": "case-del"},
        ).first()
    assert case is not None
    assert session is None


def test_expired_session_is_dropped_and_case_remains(client):
    person_id = client.post("/v1/person").json()["id"]
    _insert_case(person_id, "case-old")
    opened = client.post("/v1/session", json={"person_id": person_id, "case_id": "case-old"})
    session_id = opened.cookies.get("session")
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE session SET expires_at = :at WHERE id = :id"),
            {"at": datetime.now(timezone.utc) - timedelta(hours=1), "id": session_id},
        )
    rejected = client.get("/v1/session")
    assert rejected.status_code == 401
    assert rejected.json() == INVALID
    with engine.connect() as conn:
        session = conn.execute(text("SELECT id FROM session WHERE id = :id"), {"id": session_id}).first()
        case = conn.execute(text('SELECT id FROM "case" WHERE id = :id'), {"id": "case-old"}).first()
    assert session is None
    assert case is not None
