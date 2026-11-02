"""Source registry. A version row stays after it is invalidated."""
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
INVALID = {"code": "unauthorized", "message": "The session is not valid."}


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


def _stored(version_id):
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT review_status FROM source_version WHERE id = :id"),
            {"id": version_id},
        ).scalar()


def _by_id(body):
    return {row["id"]: row["review_status"] for row in body["versions"]}


def test_source_lifecycle(client):
    refused = client.get("/v1/source/src-closed")
    assert refused.status_code == 401
    assert refused.json() == INVALID
    person_id = _sign_in(client)
    source_id = "src-" + person_id
    rejected = client.post(
        "/v1/source",
        json={"id": source_id, "review_status": "trusted"},
    )
    assert rejected.status_code == 400
    assert rejected.json() == REJECTED
    registered = client.post("/v1/source", json={"id": source_id})
    assert registered.status_code == 200
    assert registered.json() == {"id": source_id, "review_status": "unreviewed"}
    duplicate = client.post("/v1/source", json={"id": source_id})
    assert duplicate.status_code == 400
    assert duplicate.json() == REJECTED
    missing = client.post("/v1/source/missing-" + person_id + "/version")
    assert missing.status_code == 404
    assert missing.json() == MISSING
    bodied = client.post("/v1/source/" + source_id + "/version", json={"note": "x"})
    assert bodied.status_code == 400
    assert bodied.json() == REJECTED
    first = client.post("/v1/source/" + source_id + "/version")
    assert first.status_code == 200
    first_id = first.json()["id"]
    assert first.json() == {"id": first_id, "review_status": "unreviewed"}
    unknown = client.post("/v1/source/" + source_id + "/version/missing/review")
    assert unknown.status_code == 404
    assert unknown.json() == MISSING
    reviewed = client.post("/v1/source/" + source_id + "/version/" + first_id + "/review")
    assert reviewed.status_code == 200
    assert reviewed.json() == {"id": first_id, "review_status": "trusted"}
    second = client.post("/v1/source/" + source_id + "/version")
    assert second.status_code == 200
    second_id = second.json()["id"]
    assert _stored(first_id) == "trusted"
    blocked = client.post("/v1/source/" + source_id + "/version/" + second_id + "/review")
    assert blocked.status_code == 400
    assert blocked.json() == REJECTED
    assert _stored(first_id) == "trusted"
    assert _stored(second_id) == "unreviewed"
    read = client.get("/v1/source/" + source_id)
    assert read.status_code == 200
    assert read.json()["id"] == source_id
    assert read.json()["review_status"] == "unreviewed"
    assert _by_id(read.json()) == {first_id: "trusted", second_id: "unreviewed"}
    invalidated = client.post(
        "/v1/source/" + source_id + "/version/" + first_id + "/invalidate"
    )
    assert invalidated.status_code == 200
    assert invalidated.json() == {"id": first_id, "review_status": "unreviewed"}
    assert _stored(first_id) == "unreviewed"
    kept = client.get("/v1/source/" + source_id)
    assert kept.json()["review_status"] == "unreviewed"
    assert _by_id(kept.json()) == {first_id: "unreviewed", second_id: "unreviewed"}
    with engine.connect() as conn:
        passages = conn.execute(
            text("SELECT count(*) FROM passage WHERE source_version_id IN (:a, :b)"),
            {"a": first_id, "b": second_id},
        ).scalar()
    assert passages == 0
    deleted = client.delete("/v1/person")
    assert deleted.status_code == 200
    _sign_in(client)
    still = client.get("/v1/source/" + source_id)
    assert still.status_code == 200
    assert still.json()["review_status"] == "unreviewed"
    assert _by_id(still.json()) == {first_id: "unreviewed", second_id: "unreviewed"}
