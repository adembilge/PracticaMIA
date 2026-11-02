"""Case lifecycle. Opening a case does not set ready."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import app
from auth import engine

REJECTED = {"code": "rejected", "message": "That field is not accepted."}
MISSING = {"code": "not_found", "message": "Not found."}
SUPPORTED = {
    "language": "English",
    "f02": "Yes",
    "f03": "named tenant, alone",
    "f04": "Via Torino 20, Milano",
    "f05": "named tenant",
}


@pytest.fixture
def client():
    test_client = TestClient(app)
    yield test_client
    test_client.cookies.clear()


def _count(sql):
    with engine.connect() as conn:
        return conn.execute(text(sql)).scalar()


def _stop(case_id):
    with engine.connect() as conn:
        return conn.execute(
            text('SELECT stop FROM "case" WHERE id = :id'),
            {"id": case_id},
        ).scalar()


def _actions(case_id):
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT action FROM audit_event WHERE case_id = :id"),
            {"id": case_id},
        ).scalars().all()


def _open(client, person_id, **override):
    body = {"person_id": person_id, **SUPPORTED, **override}
    return client.post("/v1/case", json=body)


def test_supported_case_persists(client):
    person_id = client.post("/v1/person").json()["id"]
    opened = _open(client, person_id)
    assert opened.status_code == 200
    case_id = opened.json()["id"]
    assert opened.json()["stop"] == "not ready"
    client.post("/v1/session", json={"person_id": person_id, "case_id": case_id})
    read = client.get("/v1/case/" + case_id)
    assert read.status_code == 200
    assert read.json() == {
        "id": case_id,
        "stop": "not ready",
        "language": "English",
        "f02": "Yes",
        "f03": "named tenant, alone",
        "f04": "Via Torino 20, Milano",
        "f05": "named tenant",
        "f06": None,
        "missing_field": None,
    }
    patched = client.patch("/v1/case/" + case_id, json={"f04": "Via Savona 12, Milano"})
    assert patched.status_code == 200
    assert client.get("/v1/case/" + case_id).json()["f04"] == "Via Savona 12, Milano"
    assert set(_actions(case_id)) == {"opened", "answer saved"}


def test_excluded_and_second_case_insert_nothing(client):
    person_id = client.post("/v1/person").json()["id"]
    case_id = _open(client, person_id).json()["id"]
    before = _count('SELECT count(*) FROM "case"')
    variants = (
        {"language": "other"},
        {"f02": "never registered in Italy"},
        {"f04": "Via Torino 20"},
        {"f05": "guest"},
        {"f06": "No"},
    )
    for override in variants:
        other = client.post("/v1/person").json()["id"]
        rejected = _open(client, other, **override)
        assert rejected.status_code == 400
        assert rejected.json() == REJECTED
    again = _open(client, person_id)
    assert again.status_code == 400
    assert again.json() == REJECTED
    assert _count('SELECT count(*) FROM "case"') == before
    assert _stop(case_id) == "not ready"


def test_stop_write_is_refused(client):
    person_id = client.post("/v1/person").json()["id"]
    case_id = _open(client, person_id).json()["id"]
    client.post("/v1/session", json={"person_id": person_id, "case_id": case_id})
    for payload in ({"stop": "ready to hand over"}, {"stop": "accepted"}):
        rejected = client.patch("/v1/case/" + case_id, json=payload)
        assert rejected.status_code == 400
        assert rejected.json() == REJECTED
    assert _stop(case_id) == "not ready"
    assert "stop became ready" not in _actions(case_id)


def test_other_person_cannot_update_case(client):
    person_a = client.post("/v1/person").json()["id"]
    person_b = client.post("/v1/person").json()["id"]
    case_a = _open(client, person_a).json()["id"]
    case_b = _open(client, person_b).json()["id"]
    client.post("/v1/session", json={"person_id": person_b, "case_id": case_b})
    rejected = client.patch("/v1/case/" + case_a, json={"f04": "Via Savona 12, Milano"})
    assert rejected.status_code == 404
    assert rejected.json() == MISSING
    with engine.connect() as conn:
        address = conn.execute(
            text('SELECT f04 FROM "case" WHERE id = :id'),
            {"id": case_a},
        ).scalar()
    assert address == "Via Torino 20, Milano"
