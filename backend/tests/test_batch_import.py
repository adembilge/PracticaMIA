"""Offline, original-byte batch ingestion safety regression suite."""
from hashlib import sha256

import pytest
from sqlalchemy import select

from app.knowledge.batch_import import (
    ingest_prepared, prepare_directory, queue_records,
)
from app.knowledge.catalog import candidate_sources, register_candidates
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.snapshot_model import KnowledgePassage, KnowledgeSnapshot
from app.knowledge.snapshots import verify_snapshot

A = "milano-residence-change"
B = "milano-italian-residence-change"
ORIGINAL = (
    b"<html><head><title>Fixture</title></head><body>"
    b"<main><h1>Synthetic test content</h1>"
    b"<p>La documentazione di residenza sintetica serve solo per i test.</p>"
    b"</main></body></html>"
)


def _file(directory, source=A, content=ORIGINAL, suffix=".html"):
    p = directory / f"{source}{suffix}"
    p.write_bytes(content)
    return p


def test_queue_has_exact_registered_sources_and_explicit_unreviewed_status():
    queue = queue_records(candidate_sources())
    assert len(queue) == 17
    assert all(item["stored_version_status"] == "not_imported" for item in queue)
    assert all(item["action"] == "download_original_and_review" for item in queue)
    assert next(item for item in queue if item["source_id"] ==
                "milano-residence-non-eu-allegato-a")["expected_extension"] == ".pdf"


def test_prepare_offline_bytes_and_save_only_pending_review(tmp_path, client):
    originals_dir = tmp_path / "originals"
    originals_dir.mkdir()
    _file(originals_dir)
    _file(originals_dir, source=B, content=ORIGINAL.replace(b"residenza", b"indirizzo"))
    originals = prepare_directory(originals_dir)
    assert [o.source_id for o in originals] == [B, A]  # deterministic filename order
    assert all(o.media_type == "text/html" for o in originals)
    assert originals[1].sha256 == sha256(ORIGINAL).hexdigest()
    factory = client.app.state.session_factory
    with factory.begin() as db:
        register_candidates(db)
        results = ingest_prepared(db, originals)
        assert all(item["status"] == "pending_review" for item in results)
        assert all(item["previous_approval_invalidated"] is False for item in results)

    with factory() as db:
        assert len(db.scalars(select(KnowledgeSourceVersion)).all()) == 2
        assert len(db.scalars(select(KnowledgeSnapshot)).all()) == 2
        assert len(db.scalars(select(KnowledgePassage)).all()) >= 2
        for version in db.scalars(select(KnowledgeSourceVersion)).all():
            assert version.status == "pending_review"
            assert verify_snapshot(db, version)
        assert all(
            src.status == "candidate" and src.active_version_id is None
            for src in db.scalars(select(KnowledgeSource)).all()
        )
        queue = queue_records(candidate_sources(), db)
        assert sum(x["stored_version_status"] == "pending_review" for x in queue) == 2
        assert len(queue) == 17

    # Exact reimport is idempotent: no duplicate version and no auto-approval.
    with factory.begin() as db:
        repeated = ingest_prepared(db, originals)
        assert all(item["status"] == "unchanged" for item in repeated)
    with factory() as db:
        assert len(db.scalars(select(KnowledgeSourceVersion)).all()) == 2


def test_preparation_rejects_unknown_duplicates_symlinks_and_wrong_media(tmp_path):
    _file(tmp_path, source="invented-source")
    with pytest.raises(ValueError, match="not mapped"):
        prepare_directory(tmp_path)

    (tmp_path / "invented-source.html").unlink()
    _file(tmp_path, source=A)
    _file(tmp_path, source=A, suffix=".htm")
    with pytest.raises(ValueError, match="Duplicate"):
        prepare_directory(tmp_path)

    (tmp_path / f"{A}.htm").unlink()
    (tmp_path / f"{A}.html").unlink()
    _file(tmp_path, source="milano-residence-form-allegato-1")
    with pytest.raises(ValueError, match="type differs"):
        prepare_directory(tmp_path)

    (tmp_path / "milano-residence-form-allegato-1.html").unlink()
    _file(tmp_path, source="milano-residence-form-allegato-1",
          content=b"<html><body>Not a PDF</body></html>", suffix=".pdf")
    with pytest.raises(ValueError):
        prepare_directory(tmp_path)

    (tmp_path / "milano-residence-form-allegato-1.pdf").unlink()
    path = _file(tmp_path)
    (tmp_path / "linked.html").symlink_to(path)
    with pytest.raises(ValueError, match="linked"):
        prepare_directory(tmp_path)


def test_batch_rolls_back_when_a_source_id_is_missing(tmp_path, client):
    originals_dir = tmp_path / "originals"
    originals_dir.mkdir()
    _file(originals_dir)
    _file(originals_dir, source=B)
    originals = prepare_directory(originals_dir)
    factory = client.app.state.session_factory
    with factory.begin() as db:
        register_candidates(db)
        db.delete(db.get(KnowledgeSource, A))
    with pytest.raises(ValueError, match="missing"):
        with factory.begin() as db:
            ingest_prepared(db, originals)
    with factory() as db:
        assert not db.scalars(select(KnowledgeSourceVersion)).all()


def test_database_url_mismatch_rejects_entire_batch(tmp_path, client):
    originals_dir = tmp_path / "originals"
    originals_dir.mkdir()
    _file(originals_dir)
    originals = prepare_directory(originals_dir)
    factory = client.app.state.session_factory
    with factory.begin() as db:
        register_candidates(db)
        db.get(KnowledgeSource, A).official_url = (
            "https://www.comune.milano.it/some-other-official-route"
        )
    with pytest.raises(ValueError, match="URL changed"):
        with factory.begin() as db:
            ingest_prepared(db, originals)
    with factory() as db:
        assert not db.scalars(select(KnowledgeSourceVersion)).all()


def test_empty_directory_never_ingests(tmp_path, client):
    originals_dir = tmp_path / "originals"
    originals_dir.mkdir()
    assert prepare_directory(originals_dir) == ()
    with pytest.raises(ValueError, match="No original"):
        with client.app.state.session_factory.begin() as db:
            ingest_prepared(db, ())
