"""Retrieval checks, in subtask order. A passage stays unreviewed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import app
from auth import engine
from ingest import chunk
from requirement import citation_id
from retrieval import search

FILE = "docs/research/DOCUMENTS.md"


@pytest.fixture
def client():
    test_client = TestClient(app)
    yield test_client
    test_client.cookies.clear()


def _clear():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM citation"))
        conn.execute(text("DELETE FROM embedding"))
        conn.execute(text("DELETE FROM passage"))


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
    return person_id, case_id


def _trusted(client, parts):
    person_id, case_id = _sign_in(client)
    source_id = "src-" + person_id
    assert client.post("/v1/source", json={"id": source_id}).status_code == 200
    version = client.post("/v1/source/" + source_id + "/version")
    assert version.status_code == 200
    version_id = version.json()["id"]
    reviewed = client.post("/v1/source/" + source_id + "/version/" + version_id + "/review")
    assert reviewed.status_code == 200
    rows = chunk(source_id, version_id, parts)
    written = client.post(
        "/v1/source/%s/version/%s/passages" % (source_id, version_id),
        json={"passages": rows},
    )
    assert written.status_code == 200
    return {
        "person_id": person_id,
        "case_id": case_id,
        "source_id": source_id,
        "version_id": version_id,
        "passages": written.json()["passages"],
    }


def _label(passage_id, procedure="address change", jurisdiction="Milano", language="English"):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE passage
                SET procedure = :procedure,
                    jurisdiction = :jurisdiction,
                    language = :language
                WHERE id = :id
                """
            ),
            {
                "id": passage_id,
                "procedure": procedure,
                "jurisdiction": jurisdiction,
                "language": language,
            },
        )


def _status(passage_id, version_id):
    with engine.connect() as conn:
        passage = conn.execute(
            text("SELECT review_status FROM passage WHERE id = :id"),
            {"id": passage_id},
        ).scalar()
        version = conn.execute(
            text("SELECT review_status FROM source_version WHERE id = :id"),
            {"id": version_id},
        ).scalar()
    return passage, version


def test_50_1_hybrid_rank(client):
    _clear()
    stored = _trusted(client, [("Alpha", "alpha residence"), ("Other", "quartz pebble")])
    for row in stored["passages"]:
        _label(row["id"])
    result = search("alpha", "address change", "Milano", "English")
    assert [row["body"] for row in result["passages"]] == ["alpha residence", "quartz pebble"]
    assert result["passages"][0]["review_status"] == "unreviewed"
    assert result["passages"][0]["provenance"]["source_version_id"] == stored["version_id"]


def test_50_2_metadata_filter(client):
    _clear()
    stored = _trusted(
        client,
        [
            ("Good", "alpha residence"),
            ("Roma", "alpha residence"),
            ("Turkish", "alpha residence"),
            ("Tari", "alpha residence"),
        ],
    )
    good, roma, turkish, tari = stored["passages"]
    _label(good["id"])
    _label(roma["id"], jurisdiction="Roma")
    _label(turkish["id"], language="Turkish")
    _label(tari["id"], procedure="TARI")
    other = _trusted(client, [("Held", "alpha residence")])
    _label(other["passages"][0]["id"])
    invalidated = client.post(
        "/v1/source/%s/version/%s/invalidate" % (other["source_id"], other["version_id"])
    )
    assert invalidated.status_code == 200
    result = search("alpha", "address change", "Milano", "English")
    assert [row["id"] for row in result["passages"]] == [good["id"]]


def test_50_3_more_query_words_rank_first(client):
    _clear()
    stored = _trusted(client, [("Many", "alpha alpha alpha"), ("One", "alpha quartz")])
    for row in stored["passages"]:
        _label(row["id"])
    import retrieval

    assert "rerank" not in Path(retrieval.__file__).read_text()
    result = search("alpha", "address change", "Milano", "English")
    assert result["passages"][0]["body"] == "alpha alpha alpha"


def test_50_4_citation_stays_unreviewed(client):
    _clear()
    stored = _trusted(client, [("Alpha", "alpha residence")])
    passage_id = stored["passages"][0]["id"]
    _label(passage_id)
    requirement_id = "req-" + stored["source_id"]
    loaded = client.post(
        "/v1/requirement",
        json={"id": requirement_id, "file": FILE, "passages": [passage_id]},
    )
    assert loaded.status_code == 200
    result = search("alpha", "address change", "Milano", "English")
    assert result["passages"][0]["review_status"] == "unreviewed"
    assert result["passages"][0]["citations"] == [
        {"id": citation_id(requirement_id, passage_id), "review_status": "unreviewed"}
    ]


def test_50_5_outcomes_and_no_route(client):
    _clear()
    assert search("", "address change", "Milano", "English") == {
        "outcome": "no evidence",
        "passages": [],
    }
    assert search("alpha", "TARI", "Milano", "English")["outcome"] == "no evidence"
    one = _trusted(client, [("Alpha", "alpha residence")])
    _label(one["passages"][0]["id"])
    single = search("alpha", "address change", "Milano", "English")
    assert single["outcome"] == "insufficient evidence"
    assert len(single["passages"]) == 1
    _clear()
    two = _trusted(client, [("Alpha", "alpha residence"), ("Beta", "beta residence")])
    for row in two["passages"]:
        _label(row["id"])
    conflict = search("residence", "address change", "Milano", "English")
    assert conflict["outcome"] == "conflicting evidence"
    assert {row["body"] for row in conflict["passages"]} == {"alpha residence", "beta residence"}
    paths = [getattr(route, "path", "") for route in app.routes]
    assert not any("search" in path for path in paths)


def test_50_6_invalidated_version_and_upload_are_absent(client):
    _clear()
    stored = _trusted(client, [("Alpha", "alpha residence")])
    passage_id = stored["passages"][0]["id"]
    _label(passage_id)
    upload_id = "upload-" + stored["person_id"]
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO upload (id, case_id, role, status, path, extracted_name)
                VALUES (:id, :case_id, 'title', 'read', :path, :name)
                """
            ),
            {
                "id": upload_id,
                "case_id": stored["case_id"],
                "path": "unused",
                "name": "alpha residence",
            },
        )
    before = _status(passage_id, stored["version_id"])
    found = search("alpha", "address change", "Milano", "English")
    assert [row["id"] for row in found["passages"]] == [passage_id]
    assert upload_id not in [row["id"] for row in found["passages"]]
    assert _status(passage_id, stored["version_id"]) == before
    invalidated = client.post(
        "/v1/source/%s/version/%s/invalidate" % (stored["source_id"], stored["version_id"])
    )
    assert invalidated.status_code == 200
    assert search("alpha", "address change", "Milano", "English") == {
        "outcome": "no evidence",
        "passages": [],
    }
    assert _status(passage_id, stored["version_id"]) == ("unreviewed", "unreviewed")
