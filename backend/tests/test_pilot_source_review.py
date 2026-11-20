"""Verify that pilot imports stay pending, scoped and reproducible."""

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import sqlite3

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.pilot_source_review import build_review_catalogue
from app.knowledge.pilot_sources import PILOT_CLAIM_PASSAGES, PILOT_SOURCES, POSTAL_APPOINTMENT_SOURCE_ID
from app.knowledge.snapshot_model import KnowledgeSnapshot
from app.knowledge.review_model import KnowledgeReviewEvent
from app.knowledge.search import resolve_approved_passage
from app.knowledge.snapshots import ingest_snapshot


@pytest.fixture
def originals(tmp_path, monkeypatch) -> Path:
    directory = tmp_path / "originals"
    directory.mkdir()
    for source_id, source in PILOT_SOURCES.items():
        if source_id == POSTAL_APPOINTMENT_SOURCE_ID:
            continue
        body = f"<h1>Test</h1><p>Fictional passage for {source_id}.</p>".encode()
        (directory / f"{source_id}.html").write_bytes(body)
        monkeypatch.setitem(PILOT_SOURCES, source_id, replace(source, content_sha256=sha256(body).hexdigest()))
    for claim_id, references in PILOT_CLAIM_PASSAGES.items():
        passages = []
        for source_id, _, _ in references:
            content = f"Fictional passage for {source_id}.".encode()
            passages.append((source_id, 0, sha256(content).hexdigest()))
        monkeypatch.setitem(PILOT_CLAIM_PASSAGES, claim_id, tuple(passages))
    return directory


def test_postal_original_adds_q3_without_revising_the_first_four(originals, tmp_path, monkeypatch):
    target = tmp_path / "review.sqlite3"
    baseline = build_review_catalogue(originals, target)
    source_id = POSTAL_APPOINTMENT_SOURCE_ID
    body = b"<nav><img src='logo.png'>Menu</nav><h2>Appointments</h2><p>Bring your letter.</p>"
    (originals / f"{source_id}.html").write_bytes(body)
    monkeypatch.setitem(PILOT_SOURCES, source_id, replace(
        PILOT_SOURCES[source_id], content_sha256=sha256(body).hexdigest(),
    ))
    digest = sha256(b"Bring your letter.").hexdigest()
    monkeypatch.setitem(PILOT_CLAIM_PASSAGES, "Q3", ((source_id, 0, digest),))

    extended = build_review_catalogue(originals, target)
    (originals / f"{source_id}.html").unlink()
    repeated = build_review_catalogue(originals, target)
    assert extended["claims_pending_acquisition"] == []
    assert repeated["claims_pending_review"] == extended["claims_pending_review"]
    assert all(extended["claims_pending_review"][key] == references
               for key, references in baseline["claims_pending_review"].items())
    [q3] = extended["claims_pending_review"]["Q3"]
    engine = create_engine(f"sqlite:///{target}")
    try:
        with Session(engine) as db:
            assert db.get(KnowledgeSnapshot, q3["source_version_id"]).extraction_version == "html-v2"
            assert resolve_approved_passage(
                db, citation_id=q3["passage_id"], jurisdiction="IT",
                procedure_id="residence_permit_renewal", language="it",
            ) is None
    finally:
        engine.dispose()


def test_isolated_sources_retain_ids_on_repeat_and_stay_out_of_approved_retrieval(originals, tmp_path):
    target = tmp_path / "review.sqlite3"
    first = build_review_catalogue(originals, target)
    second = build_review_catalogue(originals, target)
    assert {row["status"] for row in first["sources"]} == {"pending_review"}
    assert {row["status"] for row in second["sources"]} == {"unchanged"}
    assert first["claims_pending_review"] == second["claims_pending_review"]
    assert first["claims_pending_acquisition"] == ["Q3"]
    assert {row["version_id"] for row in first["sources"]} == {row["version_id"] for row in second["sources"]}

    engine = create_engine(f"sqlite:///{target}")
    try:
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(KnowledgeSourceVersion)) == 4
            assert db.scalar(select(func.count()).select_from(KnowledgeReviewEvent)) == 0
            for references in first["claims_pending_review"].values():
                for reference in references:
                    source = db.get(KnowledgeSource, reference["source_id"])
                    assert source.status == "candidate" and source.active_version_id is None
                    assert resolve_approved_passage(
                        db, citation_id=reference["passage_id"], jurisdiction=source.jurisdiction,
                        procedure_id=source.procedure_id, language="it",
                    ) is None

            source = db.get(KnowledgeSource, "torino-banns-office")
            original = (originals / "torino-banns-office.html").read_bytes()
            with pytest.raises(ValueError, match="approved official HTTPS host"):
                ingest_snapshot(db, source, original)
    finally:
        engine.dispose()


def test_wrong_original_is_rejected_before_creating_a_catalogue(originals, tmp_path):
    (originals / "torino-banns-office.html").write_bytes(b"<p>Access denied.</p>")
    target = tmp_path / "review.sqlite3"
    with pytest.raises(ValueError, match="Original differs from the recorded capture"):
        build_review_catalogue(originals, target)
    assert not target.exists()


def test_passage_mismatch_rolls_back_the_batch(originals, tmp_path, monkeypatch):
    monkeypatch.setitem(PILOT_CLAIM_PASSAGES, "T2", (("torino-banns-service", 0, "0" * 64),))
    target = tmp_path / "review.sqlite3"
    with pytest.raises(ValueError, match="Passage has changed"):
        build_review_catalogue(originals, target)
    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall() == []


def test_an_existing_non_pilot_sqlite_database_is_refused(originals, tmp_path):
    target = tmp_path / "application.sqlite3"
    with sqlite3.connect(target) as connection:
        connection.execute("CREATE TABLE original_table (id INTEGER PRIMARY KEY)")
    with pytest.raises(ValueError, match="existing Phase 4 review catalogue"):
        build_review_catalogue(originals, target)
    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall() == [
            ("original_table",),
        ]
