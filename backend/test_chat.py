"""A chat turn is kept. It does not set the stop."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import app
from auth import engine

SECRET = "swordfish"
LEASE = "Please upload the lease."
ADDRESS = "New address"
SUPPORTED = {
    "language": "English",
    "f02": "Yes",
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


def _open(client):
    person_id = client.post("/v1/person").json()["id"]
    opened = client.post("/v1/case", json={"person_id": person_id, **SUPPORTED})
    case_id = opened.json()["id"]
    client.post("/v1/session", json={"person_id": person_id, "case_id": case_id})
    return case_id


def _case(client, case_id):
    return client.get("/v1/case/" + case_id).json()


def test_answer_is_kept_after_refresh(client):
    case_id = _open(client)
    with engine.begin() as conn:
        conn.execute(text('UPDATE "case" SET f04 = NULL WHERE id = :id'), {"id": case_id})
    listed = client.get("/v1/case/%s/messages" % case_id)
    assert listed.status_code == 200
    assert listed.json() == {"messages": [], "stop": "not ready", "question": ADDRESS}
    sent = client.post("/v1/case/%s/messages" % case_id, json={"text": "Via Roma 1, Milano"})
    assert sent.status_code == 200
    assert sent.json() == {
        "messages": ["Via Roma 1, Milano", LEASE],
        "stop": "not ready",
        "question": LEASE,
    }
    again = client.get("/v1/case/%s/messages" % case_id)
    assert again.json() == sent.json()
    saved = _case(client, case_id)
    assert saved["f04"] == "Via Roma 1, Milano"
    assert saved["stop"] == "not ready"


def test_invalid_answer_keeps_the_question(client):
    case_id = _open(client)
    with engine.begin() as conn:
        conn.execute(text('UPDATE "case" SET f04 = NULL WHERE id = :id'), {"id": case_id})
    sent = client.post("/v1/case/%s/messages" % case_id, json={"text": "nope"})
    assert sent.status_code == 200
    assert sent.json()["question"] == ADDRESS
    assert sent.json()["stop"] == "not ready"
    assert _case(client, case_id)["f04"] is None


def test_password_is_not_stored(client):
    case_id = _open(client)
    before = _count("SELECT count(*) FROM message")
    refused = client.post(
        "/v1/case/%s/messages" % case_id,
        json={"text": "my password is " + SECRET},
    )
    assert refused.status_code == 200
    assert refused.json()["text"] == "I will not take your SPID password."
    assert SECRET not in refused.text
    assert refused.json()["messages"] == []
    assert _count("SELECT count(*) FROM message") == before
    assert _case(client, case_id)["stop"] == "not ready"


def test_research_leaves_the_case(client):
    case_id = _open(client)
    before = _case(client, case_id)
    sent = client.post(
        "/v1/case/%s/messages" % case_id,
        json={"text": "What is the deadline?"},
    )
    assert sent.status_code == 200
    assert sent.json()["messages"] == [
        "What is the deadline?",
        "This release does not state that.",
    ]
    assert sent.json()["stop"] == "not ready"
    assert sent.json()["question"] == LEASE
    assert _case(client, case_id) == before


def test_owner_is_asked_for_the_ownership_paper(client):
    person_id = client.post("/v1/person").json()["id"]
    opened = client.post(
        "/v1/case",
        json={
            "person_id": person_id,
            "language": "English",
            "f02": "Yes",
            "f04": "Via Savona 12, Milano",
            "f05": "Owner",
        },
    )
    case_id = opened.json()["id"]
    client.post("/v1/session", json={"person_id": person_id, "case_id": case_id})
    listed = client.get("/v1/case/%s/messages" % case_id)
    assert listed.json()["question"] == "Please upload the ownership paper."
    assert listed.json()["stop"] == "not ready"
