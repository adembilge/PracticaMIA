"""Red-team mutation tests: metadata drift must not preserve source trust.

Snapshots are created exclusively from synthetic browser text in a disposable
SQLite database. This does NOT determine whether any real legal rule is valid.
"""
from hashlib import sha256

import pytest
from sqlalchemy import select

from app.knowledge.catalog import register_candidates
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.provenance_digest import metadata_sha256
from app.knowledge.snapshot_model import KnowledgeSnapshot
from app.knowledge.snapshots import ingest_snapshot, verify_snapshot

SOURCE = "milano-residence-faq"
TITLE = "Come chiedere/cambiare residenza?"
OBSERVED = (
    "https://servizicrm.comune.milano.it/centro-supporto/KA-00330/"
    "Richiestacambio-residenza-come-procedere"
)
BODY = (
    "Synthetic municipal body for adversarial fixture testing."
    "\n\nThis is not genuine Italian administrative guidance."
).encode("utf-8")


def make_snapshot(client):
    with client.app.state.session_factory.begin() as db:
        register_candidates(db)
        src = db.get(KnowledgeSource, SOURCE)
        result = ingest_snapshot(
            db, src, BODY, media_type="text/plain",
            capture_method="browser_rendered_text",
            observed_url=OBS,
            observed_title=TITLE,
            observed_last_updated="23/07/2026",
        )
        return result


@pytest.mark.parametrize("field,new_value", [
    ("observed_last_updated", "24/07/2026"),
    ("observed_title", "Updated official article heading"),
    ("observed_url",
     "https://servizicrm.comune.milano.it/centro-supporto/KA-00330/"
     "Another-canonical-slug"),
    ("capture_method", "original_http"),
])
def test_metadata_changes_cannot_inherit_verification(client, field, new_value):
    result = make_snapshot(client)
    with client.app.state.session_factory.begin() as db:
        snap = db.get(KnowledgeSnapshot, result.version_id)
        assert snap.metadata_sha256
        assert verify_snapshot(
            db, db.get(KnowledgeSourceVersion, result.version_id)
        )
        setattr(snap, field, new_value)
    with client.app.state.session_factory() as db:
        version = db.get(KnowledgeSourceVersion, result.version_id)
        assert not verify_snapshot(db, version), field


def test_metadata_and_source_bytes_have_independent_digests(client):
    result = make_snapshot(client)
    with client.app.state.session_factory() as db:
        snap = db.get(KnowledgeSnapshot, result.version_id)
        assert result.sha256 == sha256(BODY).hexdigest()
        first = snap.metadata_sha256
        expected = metadata_sha256(
            fetched_url=snap.fetched_url, media_type=snap.media_type,
            capture_method=snap.capture_method,
            observed_url=snap.observed_url, observed_title=snap.observed_title,
            observed_last_updated=snap.observed_last_updated,
        )
        assert first == expected
    with client.app.state.session_factory.begin() as db:
        source = db.get(KnowledgeSource, SOURCE)
        new = ingest_snapshot(
            db, source, BODY, media_type="text/plain",
            capture_method="browser_rendered_text",
            observed_url=OBS, observed_title=TITLE,
            observed_last_updated="24/07/2026",
        )
        assert new.revision == result.revision + 1
        assert new.sha256 == result.sha256
    with client.app.state.session_factory() as db:
        original = db.get(KnowledgeSnapshot, result.version_id)
        updated = db.get(KnowledgeSnapshot, new.version_id)
        assert original.metadata_sha256 != updated.metadata_sha256
        assert verify_snapshot(db, db.get(KnowledgeSourceVersion, result.version_id))
        assert verify_snapshot(db, db.get(KnowledgeSourceVersion, new.version_id))


def test_metadata_digest_uses_unambiguous_length_prefix_and_unicode():
    base = dict(
        fetched_url="https://www.comune.milano.it/servizi/anagrafe/a",
        media_type="text/plain",
        capture_method="browser_rendered_text",
        observed_url="https://www.comune.milano.it/servizi/anagrafe/a",
        observed_title="Cittadinanza e residenza — Milano",
        observed_last_updated="23/07/2026",
    )
    digest = metadata_sha256(**base)
    assert len(digest) == 64
    assert metadata_sha256(**base) == digest
    assert metadata_sha256(**{**base, "observed_title": base["observed_title"] + " "}) != digest
    assert metadata_sha256(**{**base, "observed_last_updated": None}) != digest
    assert metadata_sha256(**{**base, "observed_last_updated": ""}) != digest
