"""Upload storage. A kept file is not a read."""
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
NAME = "lease-client-name.pdf"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PAPERPILOT_UPLOAD_DIR", str(tmp_path))
    test_client = TestClient(app)
    yield test_client
    test_client.cookies.clear()


def _stop(case_id):
    with engine.connect() as conn:
        return conn.execute(
            text('SELECT stop FROM "case" WHERE id = :id'),
            {"id": case_id},
        ).scalar()


def _count_uploads(case_id):
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT count(*) FROM upload WHERE case_id = :id AND role = 'title' AND current"),
            {"id": case_id},
        ).scalar()


def _path(upload_id):
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT path FROM upload WHERE id = :id"),
            {"id": upload_id},
        ).scalar()


def _actions(case_id):
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT action FROM audit_event WHERE case_id = :id"),
            {"id": case_id},
        ).scalars().all()


def _open(client):
    person_id = client.post("/v1/person").json()["id"]
    opened = client.post("/v1/case", json={"person_id": person_id, **SUPPORTED})
    case_id = opened.json()["id"]
    client.post("/v1/session", json={"person_id": person_id, "case_id": case_id})
    return person_id, case_id


def _post(client, case_id, payload, name=NAME):
    return client.post(
        "/v1/case/%s/upload" % case_id,
        data={"role": "title"},
        files={"file": (name, payload, "application/pdf")},
    )


def test_owner_replaces_title_file(client):
    _person_id, case_id = _open(client)
    created = _post(client, case_id, PDF)
    assert created.status_code == 200
    assert created.json() == {"id": created.json()["id"], "role": "title"}
    upload_id = created.json()["id"]
    stored = _path(upload_id)
    assert NAME not in stored
    assert _stop(case_id) == "not ready"
    assert "upload replaced" not in _actions(case_id)
    fetched = client.get("/v1/upload/" + upload_id)
    assert fetched.status_code == 200
    assert fetched.content == PDF
    replaced = _post(client, case_id, REPLACEMENT)
    assert replaced.status_code == 200
    assert not Path(stored).is_file()
    assert _count_uploads(case_id) == 1
    assert client.get("/v1/upload/" + replaced.json()["id"]).content == REPLACEMENT
    assert _actions(case_id).count("upload replaced") == 1
    assert _stop(case_id) == "not ready"


def test_invalid_uploads_are_not_kept(client, monkeypatch):
    _person_id, case_id = _open(client)
    before = _count_uploads(case_id)
    empty = client.post("/v1/case/%s/upload" % case_id, content=b"")
    assert empty.status_code == 400
    assert empty.json() == REJECTED
    plain = _post(client, case_id, b"plain text")
    assert plain.status_code == 400
    assert plain.json() == REJECTED
    assert upload.LIMIT == 10 * 1024 * 1024
    monkeypatch.setattr(upload, "LIMIT", 8)
    oversized = _post(client, case_id, PDF)
    assert oversized.status_code == 400
    assert oversized.json() == REJECTED
    assert _count_uploads(case_id) == before
    assert _stop(case_id) == "not ready"
    assert list(Path(upload.upload_dir()).iterdir()) == []


def test_other_person_cannot_use_the_file(client):
    _person_a, case_a = _open(client)
    created = _post(client, case_a, PDF)
    upload_id = created.json()["id"]
    stored = _path(upload_id)
    client.cookies.clear()
    _open(client)
    rejected = _post(client, case_a, REPLACEMENT)
    assert rejected.status_code == 404
    assert rejected.json() == MISSING
    fetched = client.get("/v1/upload/" + upload_id)
    assert fetched.status_code == 404
    assert fetched.json() == MISSING
    assert Path(stored).is_file()
    assert _path(upload_id) == stored


def _png(width, height):
    data = width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"
    return b"\x89PNG\r\n\x1a\n" + len(data).to_bytes(4, "big") + b"IHDR" + data + b"\x00\x00\x00\x00"


def _jpeg(height, width):
    return (
        b"\xff\xd8\xff\xc0\x00\x0b\x08"
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + b"\x01\x01\x11\x00"
    )


def test_bad_bytes_are_not_written(client):
    _person_id, case_id = _open(client)
    before = _count_uploads(case_id)
    samples = (
        b"%PDF-1.4\nhello",
        b"%PDF-1.4\n/JavaScript\n%%EOF",
        _png(100000, 100000),
        b"\xff\xd8\xff\xd9",
    )
    for payload in samples:
        rejected = _post(client, case_id, payload)
        assert rejected.status_code == 400
        assert rejected.json() == REJECTED
    assert _count_uploads(case_id) == before
    assert list(Path(upload.upload_dir()).iterdir()) == []
    assert _stop(case_id) == "not ready"


def test_small_images_keep_the_signature_suffix(client):
    _person_id, case_id = _open(client)
    png = _post(client, case_id, _png(1, 1), name="photo.pdf")
    assert png.status_code == 200
    assert _path(png.json()["id"]).endswith(".png")
    jpeg = _post(client, case_id, _jpeg(1, 1), name="photo.pdf")
    assert jpeg.status_code == 200
    assert _path(jpeg.json()["id"]).endswith(".jpg")
    assert _stop(case_id) == "not ready"


def test_client_filename_is_not_stored(client):
    _person_id, case_id = _open(client)
    created = _post(client, case_id, PDF, name="../../secret.pdf")
    assert created.status_code == 200
    stored = _path(created.json()["id"])
    assert "secret" not in stored
    assert ".." not in stored
    assert stored.endswith(".pdf")
