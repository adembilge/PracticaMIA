"""Ingest checks, in subtask order. A passage stays unreviewed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import app
from auth import engine
from embeddings import embed
from ingest import chunk, collect, extract, passage_id, run

INVALID = {"code": "unauthorized", "message": "The session is not valid."}
REJECTED = {"code": "rejected", "message": "That field is not accepted."}
HTML = (
    "<h1>Alpha</h1><ul><li>One</li><li>Two</li></ul>"
    "<table><tr><th>Head</th><td>Cell</td></tr></table><h2>Beta</h2><p>Tail</p>"
)
PDF = b"%PDF-1.1\nBT (Alpha token) Tj ET\n"


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


def _trusted(client):
    person_id = _sign_in(client)
    source_id = "src-" + person_id
    created = client.post("/v1/source", json={"id": source_id})
    assert created.status_code == 200
    version = client.post("/v1/source/" + source_id + "/version")
    assert version.status_code == 200
    version_id = version.json()["id"]
    reviewed = client.post("/v1/source/" + source_id + "/version/" + version_id + "/review")
    assert reviewed.status_code == 200
    return source_id, version_id


def _url(source_id, version_id):
    return "/v1/source/%s/version/%s/passages" % (source_id, version_id)


def _count(version_id):
    with engine.connect() as conn:
        passages = conn.execute(
            text("SELECT count(*) FROM passage WHERE source_version_id = :id"),
            {"id": version_id},
        ).scalar()
        embeddings = conn.execute(
            text(
                """
                SELECT count(*) FROM embedding AS e
                JOIN passage AS p ON p.id = e.passage_id
                WHERE p.source_version_id = :id
                """
            ),
            {"id": version_id},
        ).scalar()
    return passages, embeddings


def _body(version_id):
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT body FROM passage WHERE source_version_id = :id"),
            {"id": version_id},
        ).scalar()


def test_45_1_collect(tmp_path):
    calls = []

    def post(*args):
        calls.append(args)
        return 200

    missing = tmp_path / "gone.html"
    assert run(missing, "doc", "ver", post) == 1
    assert calls == []
    empty = tmp_path / "empty.html"
    empty.write_bytes(b"")
    assert run(empty, "doc", "ver", post) == 1
    assert collect("http://example.test/a") is None
    assert collect("https://example.test/a") is None
    assert run("https://example.test/a", "doc", "ver", post) == 1
    assert calls == []
    page = tmp_path / "page.html"
    page.write_bytes(HTML.encode())
    assert collect(page) == HTML.encode()
    assert run(page, "doc", "ver", post) == 0
    assert len(calls) == 1
    assert calls[0][0] == "doc"
    assert calls[0][1] == "ver"


def test_45_2_extract():
    assert extract("page.html", HTML.encode()) == [
        ("Alpha", "One Two Head Cell"),
        ("Beta", "Tail"),
    ]
    assert extract("file.pdf", PDF) == [(None, "Alpha token")]


def test_45_3_chunk():
    parts = extract("page.html", HTML.encode())
    rows = chunk("doc-1", "ver-1", parts)
    assert len(rows) == 2
    assert rows[0]["source_id"] == "doc-1"
    assert rows[0]["source_version_id"] == "ver-1"
    assert rows[0]["section"] == "Alpha"
    assert rows[1]["section"] == "Beta"
    assert rows[0]["id"] == passage_id("ver-1", "Alpha", rows[0]["body"])
    assert rows[1]["id"] == passage_id("ver-1", "Beta", rows[1]["body"])


def test_45_4_embed(client):
    closed = client.post("/v1/source/src/version/ver/passages", json={"passages": []})
    assert closed.status_code == 401
    assert closed.json() == INVALID
    source_id, version_id = _trusted(client)
    rows = chunk(source_id, version_id, [("Alpha", "alpha token")])
    written = client.post(_url(source_id, version_id), json={"passages": rows})
    assert written.status_code == 200
    stored_id = written.json()["passages"][0]["id"]
    assert stored_id == passage_id(version_id, "Alpha", "alpha token")
    assert written.json()["passages"][0]["review_status"] == "unreviewed"
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT model_name, embedding_version, vector::text, p.review_status
                FROM embedding AS e
                JOIN passage AS p ON p.id = e.passage_id
                WHERE e.passage_id = :id
                """
            ),
            {"id": stored_id},
        ).one()
    assert row[0] == "local"
    assert row[1] == "1"
    assert row[3] == "unreviewed"
    parsed = [float(part) for part in row[2].strip("[]").split(",")]
    expected = embed("alpha token")
    assert all(abs(left - right) < 1e-5 for left, right in zip(parsed, expected))


def test_45_5_index(client):
    source_id, version_id = _trusted(client)
    rows = chunk(source_id, version_id, [("Alpha", "zincword token")])
    written = client.post(_url(source_id, version_id), json={"passages": rows})
    assert written.status_code == 200
    stored_id = written.json()["passages"][0]["id"]
    literal = "[" + ",".join(str(value) for value in embed("zincword token")) + "]"
    with engine.connect() as conn:
        found = conn.execute(
            text(
                """
                SELECT id FROM passage
                WHERE source_version_id = :version_id
                  AND body_tsv @@ plainto_tsquery('simple', 'zincword')
                """
            ),
            {"version_id": version_id},
        ).scalar()
        nearest = conn.execute(
            text(
                """
                SELECT e.passage_id
                FROM embedding AS e
                JOIN passage AS p ON p.id = e.passage_id
                WHERE p.source_version_id = :version_id
                ORDER BY e.vector <=> CAST(:vector AS vector)
                LIMIT 1
                """
            ),
            {"version_id": version_id, "vector": literal},
        ).scalar()
    assert found == stored_id
    assert nearest == stored_id


def test_45_6_sync(client):
    source_id, version_id = _trusted(client)
    rows = chunk(source_id, version_id, [("Alpha", "alpha token")])
    first = client.post(_url(source_id, version_id), json={"passages": rows})
    assert first.status_code == 200
    ids = [row["id"] for row in first.json()["passages"]]
    second = client.post(_url(source_id, version_id), json={"passages": rows})
    assert second.status_code == 200
    assert [row["id"] for row in second.json()["passages"]] == ids
    assert _count(version_id) == (1, 1)
    changed = chunk(source_id, version_id, [("Alpha", "other token")])
    rejected = client.post(_url(source_id, version_id), json={"passages": changed})
    assert rejected.status_code == 400
    assert rejected.json() == REJECTED
    assert _body(version_id) == "alpha token"
    assert _count(version_id) == (1, 1)
    other = client.post("/v1/source/" + source_id + "/version")
    assert other.status_code == 200
    other_id = other.json()["id"]
    blocked = client.post(
        _url(source_id, other_id),
        json={"passages": chunk(source_id, other_id, [("Alpha", "alpha token")])},
    )
    assert blocked.status_code == 400
    assert blocked.json() == REJECTED
    assert _count(other_id) == (0, 0)
    assert _count(version_id) == (1, 1)
    with engine.connect() as conn:
        status = conn.execute(
            text("SELECT review_status FROM source_document WHERE id = :id"),
            {"id": source_id},
        ).scalar()
    assert status == "unreviewed"
