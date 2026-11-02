"""The review shows the package. The client does not set the stop."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import app
from auth import engine
from prepare import LINK

SUPPORTED = {
    "language": "English",
    "f02": "Yes",
    "f04": "Via Torino 20, Milano",
    "f05": "named tenant",
}
READABLE = (
    b"%PDF-1.4\n"
    b"(Name: Ada Lovelace) Tj\n"
    b"(Via Torino 20, Milano) Tj\n"
    b"%%EOF"
)
CONFLICT = (
    b"%PDF-1.4\n"
    b"(Name: Ada Lovlace) Tj\n"
    b"(Via Padova 10, Milano) Tj\n"
    b"%%EOF"
)
REPLACED = (
    b"%PDF-1.4\n"
    b"(Name: Ada Lovelace) Tj\n"
    b"(Via Dante 1, Milano) Tj\n"
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


def _row(case_id):
    with engine.connect() as conn:
        return conn.execute(
            text('SELECT stop, named_name, named_address FROM "case" WHERE id = :id'),
            {"id": case_id},
        ).mappings().one()


def _post(client, case_id, payload):
    return client.post(
        "/v1/case/%s/upload" % case_id,
        data={"role": "title"},
        files={"file": ("paper.pdf", payload, "application/pdf")},
    )


def test_missing_title_has_no_link(client):
    case_id = _open(client)
    reviewed = client.get("/v1/case/%s/review" % case_id)
    assert reviewed.status_code == 200
    body = reviewed.json()
    assert body["stop"] == "not ready"
    assert body["missing"] == ["f07"]
    assert body["name"] is None
    assert body["address"] is None
    assert body["language"] == "English"
    assert "link" not in body
    assert "notice" not in body
    refused = client.post("/v1/case/%s/review" % case_id, json={"stop": "ready to hand over"})
    assert refused.status_code == 400
    assert _row(case_id)["stop"] == "not ready"


def test_a_conflict_lists_both_values_until_named(client):
    case_id = _open(client)
    _post(client, case_id, CONFLICT)
    reviewed = client.get("/v1/case/%s/review" % case_id).json()
    assert reviewed["stop"] == "not ready"
    assert "link" not in reviewed
    assert reviewed["warnings"]["address"]["values"] == [
        {"type": "lease", "value": "Via Padova 10, Milano"},
        {"type": "stated", "value": "Via Torino 20, Milano"},
    ]
    refused = client.post(
        "/v1/case/%s/review" % case_id,
        json={"name": "Ada Lovelace", "address": "Via Torino 20, Milano", "stop": "ready to hand over"},
    )
    assert refused.status_code == 400
    assert _row(case_id)["stop"] == "not ready"
    named = client.post(
        "/v1/case/%s/review" % case_id,
        json={"name": "Ada Lovelace", "address": "Via Torino 20, Milano"},
    )
    assert named.status_code == 200
    body = named.json()
    assert body["stop"] == "ready to hand over"
    assert body["name"] == "Ada Lovelace"
    assert body["address"] == "Via Torino 20, Milano"
    assert body["link"] == LINK
    stored = _row(case_id)
    assert stored["stop"] == "ready to hand over"
    assert stored["named_name"] == "Ada Lovelace"
    assert stored["named_address"] == "Via Torino 20, Milano"


def test_replacing_the_paper_drops_the_confirmation(client):
    case_id = _open(client)
    _post(client, case_id, CONFLICT)
    named = client.post(
        "/v1/case/%s/review" % case_id,
        json={"name": "Ada Lovelace", "address": "Via Torino 20, Milano"},
    )
    assert named.json()["link"] == LINK
    _post(client, case_id, REPLACED)
    reviewed = client.get("/v1/case/%s/review" % case_id).json()
    assert reviewed["stop"] == "not ready"
    assert "link" not in reviewed
    stored = _row(case_id)
    assert stored["named_name"] is None
    assert stored["named_address"] is None
    assert stored["stop"] == "not ready"


def test_a_matching_paper_carries_the_link(client):
    case_id = _open(client)
    _post(client, case_id, READABLE)
    reviewed = client.get("/v1/case/%s/review" % case_id)
    assert reviewed.status_code == 200
    body = reviewed.json()
    assert body["stop"] == "ready to hand over"
    assert body["name"] == "Ada Lovelace"
    assert body["address"] == "Via Torino 20, Milano"
    assert body["link"] == LINK
    assert body["language"] == "English"
    assert "SPID password" in body["notice"]
    assert "I will not file it." in body["notice"]
    assert "Opening that page is not acceptance by the Comune di Milano." in body["notice"]
    assert _row(case_id)["stop"] == "ready to hand over"
    refused = client.post(
        "/v1/case/%s/review" % case_id,
        json={"name": "Other Person", "address": "Via Dante 1, Milano"},
    )
    assert refused.status_code == 400
    assert _row(case_id)["named_name"] is None


def test_other_person_cannot_read_the_review(client):
    case_id = _open(client)
    client.cookies.clear()
    _open(client)
    rejected = client.get("/v1/case/%s/review" % case_id)
    assert rejected.status_code == 404
    assert _row(case_id)["stop"] == "not ready"
