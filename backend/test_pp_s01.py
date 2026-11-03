"""Scenario 01 against the session that exists. No email and no password are stored."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from sqlalchemy import text

from app import app
from auth import engine

STORY = (
    "I'm a Turkish citizen living in Milan. I was registered at Via Padova 10. "
    "Last week I moved to a new apartment at Via Torino 20, Milano. The lease is in my name. "
    "I have SPID, my passport, and a valid permesso di soggiorno. Help me update my registered address."
)


def _count(sql):
    with engine.connect() as conn:
        return conn.execute(text(sql)).scalar()


def test_pp_s01_session_and_refused_password():
    client = TestClient(app)
    before = _count("SELECT count(*) FROM person")
    rejected = client.post(
        "/v1/person",
        json={"email": "giulia01@example.test", "password": "x"},
    )
    assert rejected.status_code == 400
    assert _count("SELECT count(*) FROM person") == before

    opened = client.post("/v1/onboarding", json={"messages": [STORY]})
    assert opened.status_code == 200
    body = opened.json()
    assert body["case"]["stop"] == "not ready"
    assert opened.cookies.get("session")
    assert "password" not in opened.text
    case_id = body["case"]["id"]

    read = client.get("/v1/case/" + case_id)
    assert read.status_code == 200
    assert read.json()["stop"] == "not ready"

    client.cookies.clear()
    hidden = client.get("/v1/case/" + case_id)
    assert hidden.status_code == 401
    assert "Via Torino" not in hidden.text

    refused = client.post("/v1/onboarding", json={"messages": ["my password is secret"]})
    assert refused.status_code == 200
    assert refused.json()["case"] is None
    client.cookies.clear()
