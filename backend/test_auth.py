"""Session checks. The case row is inserted here because opening a case is not this task."""
import os
import sys
import tempfile
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
        conn.execute(text('DELETE FROM "case" WHERE id = :id'), {"id": case_id})
        conn.execute(
            text('INSERT INTO "case" (id, person_id, stop) VALUES (:id, :person_id, :stop)'),
            {"id": case_id, "person_id": person_id, "stop": "not ready"},
        )


def _temp_file():
    handle = tempfile.NamedTemporaryFile(delete=False)
    handle.close()
    return handle.name


def _insert_upload(case_id, upload_id, path):
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO upload (id, case_id, role, status, path) "
                "VALUES (:id, :case_id, 'title', 'failed', :path)"
            ),
            {"id": upload_id, "case_id": case_id, "path": path},
        )


def _insert_passage():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM passage WHERE id = 'pass-profile'"))
        conn.execute(text("DELETE FROM source_version WHERE id = 'ver-profile'"))
        conn.execute(text("DELETE FROM source_document WHERE id = 'doc-profile'"))
        conn.execute(text("INSERT INTO source_document (id) VALUES ('doc-profile')"))
        conn.execute(
            text(
                "INSERT INTO source_version (id, source_document_id) "
                "VALUES ('ver-profile', 'doc-profile')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO passage (id, source_version_id, source_id, body) "
                "VALUES ('pass-profile', 'ver-profile', 'src-profile', 'kept')"
            )
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


def test_other_person_cannot_read_case(client):
    owner = client.post("/v1/person").json()["id"]
    other = client.post("/v1/person").json()["id"]
    _insert_case(owner, "case-read-a")
    _insert_case(other, "case-read-b")
    opened = client.post("/v1/session", json={"person_id": owner, "case_id": "case-read-a"})
    owner_session = opened.cookies.get("session")
    client.cookies.clear()
    missing = client.get("/v1/case/case-read-a")
    assert missing.status_code == 401
    assert missing.json() == INVALID
    client.post("/v1/session", json={"person_id": other, "case_id": "case-read-b"})
    rejected = client.get("/v1/case/case-read-a")
    assert rejected.status_code == 404
    assert rejected.json() == MISSING
    with engine.connect() as conn:
        stop = conn.execute(
            text('SELECT stop FROM "case" WHERE id = :id'),
            {"id": "case-read-a"},
        ).scalar()
    assert stop == "not ready"
    client.cookies.clear()
    client.cookies.set("session", owner_session)
    own = client.get("/v1/case/case-read-a")
    assert own.status_code == 200
    assert own.json() == {
        "id": "case-read-a",
        "stop": "not ready",
        "language": None,
        "f02": None,
        "f03": None,
        "f04": None,
        "f05": None,
        "f06": None,
        "missing_field": None,
    }


def test_other_person_cannot_delete_session(client):
    owner = client.post("/v1/person").json()["id"]
    other = client.post("/v1/person").json()["id"]
    _insert_case(owner, "case-keep")
    _insert_case(other, "case-drop")
    opened = client.post("/v1/session", json={"person_id": owner, "case_id": "case-keep"})
    owner_session = opened.cookies.get("session")
    client.cookies.clear()
    opened = client.post("/v1/session", json={"person_id": other, "case_id": "case-drop"})
    other_session = opened.cookies.get("session")
    rejected = client.delete("/v1/session/" + owner_session)
    assert rejected.status_code == 404
    assert rejected.json() == MISSING
    with engine.connect() as conn:
        kept = conn.execute(
            text("SELECT id FROM session WHERE id = :id"),
            {"id": owner_session},
        ).first()
    assert kept is not None
    deleted = client.delete("/v1/session/" + other_session)
    assert deleted.status_code == 200
    with engine.connect() as conn:
        gone = conn.execute(
            text("SELECT id FROM session WHERE id = :id"),
            {"id": other_session},
        ).first()
        case = conn.execute(
            text('SELECT id FROM "case" WHERE id = :id'),
            {"id": "case-drop"},
        ).first()
    assert gone is None
    assert case is not None


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


def test_person_read_and_empty_update(client):
    missing = client.get("/v1/person")
    assert missing.status_code == 401
    assert missing.json() == INVALID
    rejected = client.patch("/v1/person")
    assert rejected.status_code == 401
    assert rejected.json() == INVALID
    person_id = client.post("/v1/person").json()["id"]
    _insert_case(person_id, "case-prof-read")
    client.post("/v1/session", json={"person_id": person_id, "case_id": "case-prof-read"})
    read = client.get("/v1/person")
    assert read.status_code == 200
    assert read.json() == {"id": person_id}
    updated = client.patch("/v1/person")
    assert updated.status_code == 200
    assert updated.json() == {"id": person_id}
    before = _count("SELECT count(*) FROM person")
    denied = client.patch("/v1/person", json={"email": "a@b.c"})
    assert denied.status_code == 400
    assert denied.json() == REJECTED
    assert _count("SELECT count(*) FROM person") == before


def test_delete_person_leaves_the_other(client):
    person_a = client.post("/v1/person").json()["id"]
    person_b = client.post("/v1/person").json()["id"]
    _insert_case(person_a, "case-prof-a")
    _insert_case(person_b, "case-prof-b")
    path_a = _temp_file()
    path_b = _temp_file()
    try:
        _insert_upload("case-prof-a", "up-prof-a", path_a)
        _insert_upload("case-prof-b", "up-prof-b", path_b)
        _insert_passage()
        client.post("/v1/session", json={"person_id": person_a, "case_id": "case-prof-a"})
        client.cookies.clear()
        client.post("/v1/session", json={"person_id": person_b, "case_id": "case-prof-b"})
        deleted = client.delete("/v1/person")
        assert deleted.status_code == 200
        assert deleted.json() == {"status": "ok"}
        assert client.get("/v1/session").status_code == 401
        assert not os.path.isfile(path_b)
        with engine.connect() as conn:
            assert conn.execute(text("SELECT id FROM person WHERE id = :id"), {"id": person_b}).first() is None
            assert conn.execute(text("SELECT id FROM person WHERE id = :id"), {"id": person_a}).first() is not None
            assert conn.execute(text('SELECT id FROM "case" WHERE id = :id'), {"id": "case-prof-b"}).first() is None
            assert conn.execute(text('SELECT id FROM "case" WHERE id = :id'), {"id": "case-prof-a"}).first() is not None
            assert conn.execute(text("SELECT id FROM session WHERE case_id = :id"), {"id": "case-prof-b"}).first() is None
            assert conn.execute(text("SELECT id FROM session WHERE case_id = :id"), {"id": "case-prof-a"}).first() is not None
            assert conn.execute(text("SELECT id FROM passage WHERE id = 'pass-profile'")).first() is not None
        assert os.path.isfile(path_a)
    finally:
        for path in (path_a, path_b):
            if os.path.isfile(path):
                os.remove(path)
