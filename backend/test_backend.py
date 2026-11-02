"""One backend walk. A failed replace leaves the first file."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import upload
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
PDF = b"%PDF-1.4\nhello\n%%EOF"
REPLACEMENT = b"%PDF-1.4\nreplaced\n%%EOF"


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
    return person_id, case_id


def _post(client, case_id, payload):
    return client.post(
        "/v1/case/%s/upload" % case_id,
        data={"role": "title"},
        files={"file": ("lease-client-name.pdf", payload, "application/pdf")},
    )


def _stop(case_id):
    with engine.connect() as conn:
        return conn.execute(
            text('SELECT stop FROM "case" WHERE id = :id'),
            {"id": case_id},
        ).scalar()


def _one(sql, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).scalar()


def test_backend_sequence(client):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM passage WHERE id = 'pass-backend'"))
        conn.execute(text("DELETE FROM source_version WHERE id = 'ver-backend'"))
        conn.execute(text("DELETE FROM source_document WHERE id = 'doc-backend'"))
        conn.execute(text("INSERT INTO source_document (id) VALUES ('doc-backend')"))
        conn.execute(
            text(
                "INSERT INTO source_version (id, source_document_id) "
                "VALUES ('ver-backend', 'doc-backend')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO passage (id, source_version_id, source_id, body) "
                "VALUES ('pass-backend', 'ver-backend', 'src-backend', 'kept')"
            )
        )
    person_id, case_id = _open(client)
    created = _post(client, case_id, PDF)
    assert created.status_code == 200
    upload_id = created.json()["id"]
    stored = _one("SELECT path FROM upload WHERE id = :id", id=upload_id)
    assert client.get("/v1/upload/" + upload_id).content == PDF
    patched = client.patch("/v1/case/" + case_id, json={"f04": "Via Savona 12, Milano"})
    assert patched.status_code == 200
    assert client.get("/v1/case/" + case_id).json()["f04"] == "Via Savona 12, Milano"
    refused = client.patch("/v1/case/" + case_id, json={"stop": "accepted"})
    assert refused.status_code == 400
    assert refused.json() == REJECTED
    assert _stop(case_id) == "not ready"
    owner_session = client.cookies.get("session")
    client.cookies.clear()
    _open(client)
    fetched = client.get("/v1/upload/" + upload_id)
    assert fetched.status_code == 404
    assert fetched.json() == MISSING
    other = client.patch("/v1/case/" + case_id, json={"f04": "Via Roma 1, Milano"})
    assert other.status_code == 404
    assert other.json() == MISSING
    assert Path(stored).read_bytes() == PDF
    client.cookies.clear()
    client.cookies.set("session", owner_session)
    deleted = client.delete("/v1/person")
    assert deleted.status_code == 200
    assert not Path(stored).is_file()
    assert _one("SELECT id FROM person WHERE id = :id", id=person_id) is None
    assert _one('SELECT id FROM "case" WHERE id = :id', id=case_id) is None
    assert _one("SELECT id FROM upload WHERE id = :id", id=upload_id) is None
    assert _one("SELECT id FROM passage WHERE id = 'pass-backend'") == "pass-backend"


def test_interrupted_replace_keeps_the_first_file(client, monkeypatch):
    _person_id, case_id = _open(client)
    created = _post(client, case_id, PDF)
    upload_id = created.json()["id"]
    stored = _one("SELECT path FROM upload WHERE id = :id", id=upload_id)
    original = upload.engine.begin
    state = {"n": 0}

    def begin():
        state["n"] += 1
        # shortcut: the write is the third begin in create_upload
        if state["n"] == 3:
            raise RuntimeError("interrupted")
        return original()

    monkeypatch.setattr(upload.engine, "begin", begin)
    try:
        with pytest.raises(RuntimeError, match="interrupted"):
            _post(client, case_id, REPLACEMENT)
    finally:
        monkeypatch.setattr(upload.engine, "begin", original)
    assert state["n"] == 3
    assert Path(stored).is_file()
    assert _one(
        "SELECT count(*) FROM upload WHERE case_id = :id AND current",
        id=case_id,
    ) == 1
    assert client.get("/v1/upload/" + upload_id).content == PDF
    names = {path.name for path in Path(upload.upload_dir()).iterdir()}
    assert names == {Path(stored).name}
