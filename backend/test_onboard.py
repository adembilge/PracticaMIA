"""A supported story is saved. An excluded story writes nothing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import app
from auth import engine

S01 = (
    "I'm a Turkish citizen living in Milan. I was registered at Via Padova 10. "
    "Last week I moved to a new apartment at Via Torino 20, Milano. The lease is in my name. "
    "I have SPID, my passport, and a valid permesso di soggiorno. Help me update my registered address."
)
A01 = "I moved to Milan last month. I need residence."
U01 = (
    "I landed in Milan two weeks ago from Ankara. I have never been registered in Italy. "
    "I rented a room and need my first residence."
)
U03 = "Milano'da yeni bir daireye taşındım. İkamet adresimi güncellemem gerekiyor."
SECRET = "swordfish"


@pytest.fixture
def client():
    test_client = TestClient(app)
    yield test_client
    test_client.cookies.clear()


def _count(sql):
    with engine.connect() as conn:
        return conn.execute(text(sql)).scalar()


def test_s01_is_saved_not_ready(client):
    cases = _count('SELECT count(*) FROM "case"')
    messages = _count("SELECT count(*) FROM message")
    opened = client.post("/v1/onboarding", json={"messages": [S01]})
    assert opened.status_code == 200
    body = opened.json()
    assert body["case"]["stop"] == "not ready"
    assert body["case"]["language"] == "English"
    assert body["case"]["f02"] == "Yes"
    assert body["case"]["f03"] is None
    assert body["case"]["f04"] == "Via Torino 20, Milano"
    assert body["case"]["f05"] == "named tenant"
    assert S01 not in opened.text
    read = client.get("/v1/case/" + body["case"]["id"])
    assert read.status_code == 200
    assert read.json()["stop"] == "not ready"
    assert _count('SELECT count(*) FROM "case"') == cases + 1
    assert _count("SELECT count(*) FROM message") == messages


def test_s01_fields_without_f03_save_null(client):
    person_id = client.post("/v1/person").json()["id"]
    opened = client.post(
        "/v1/case",
        json={
            "person_id": person_id,
            "language": "English",
            "f02": "Yes",
            "f04": "Via Torino 20, Milano",
            "f05": "named tenant",
        },
    )
    assert opened.status_code == 200
    assert opened.json()["f03"] is None
    assert opened.json()["stop"] == "not ready"
    rejected = client.post(
        "/v1/case",
        json={
            "person_id": client.post("/v1/person").json()["id"],
            "language": "English",
            "f02": "Yes",
            "f03": "guest",
            "f04": "Via Torino 20, Milano",
            "f05": "named tenant",
        },
    )
    assert rejected.status_code == 400


def test_u01_and_u03_write_nothing(client):
    cases = _count('SELECT count(*) FROM "case"')
    people = _count("SELECT count(*) FROM person")
    abroad = client.post("/v1/onboarding", json={"messages": [U01]})
    assert abroad.status_code == 200
    assert abroad.json()["case"] is None
    assert abroad.json()["text"] == (
        "I will not open the address-change case. "
        "The door is the Comune di Milano service for foreigners arriving from abroad. "
        "I will not add the steps."
    )
    language = client.post("/v1/onboarding", json={"messages": [U03]})
    assert language.status_code == 200
    assert language.json() == {"case": None, "text": "Continue in English or Italian."}
    assert _count('SELECT count(*) FROM "case"') == cases
    assert _count("SELECT count(*) FROM person") == people


def test_a01_asks_once_and_writes_nothing(client):
    cases = _count('SELECT count(*) FROM "case"')
    asked = client.post("/v1/onboarding", json={"messages": [A01]})
    assert asked.status_code == 200
    assert asked.json() == {
        "case": None,
        "text": "Are you already registered as a resident of Milano?",
    }
    assert _count('SELECT count(*) FROM "case"') == cases


def test_a_secret_is_not_in_the_response(client):
    cases = _count('SELECT count(*) FROM "case"')
    refused = client.post("/v1/onboarding", json={"messages": ["my password is " + SECRET]})
    assert refused.status_code == 200
    assert refused.json() == {"case": None, "text": "I will not take your SPID password."}
    assert SECRET not in refused.text
    assert _count('SELECT count(*) FROM "case"') == cases
