"""Browser-rendered publisher content is provenance-labeled and untrusted until approval."""
import json
from hashlib import sha256

import pytest
from sqlalchemy import select

from app.knowledge.browser_capture_import import prepare_captures
from app.knowledge.catalog import register_candidates
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.review_service import approve_version
from app.knowledge.search import search_approved_passages
from app.knowledge.snapshot_model import KnowledgeSnapshot, KnowledgePassage
from app.knowledge.snapshots import ingest_snapshot, verify_snapshot

SOURCE = "milano-residence-faq"
REG = "https://servizicrm.comune.milano.it/centro-supporto/KA-00330/"
OBS = REG + "Richiestacambio-residenza-come-procedere"
BODY = (
    "Il Comune descrive un testo sintetico creato per testare i controlli."
    "\n\nLa seconda frase verifica la provenienza del contenuto."
)
SCOPE = {
    "jurisdiction": "IT-MI-MILANO",
    "procedure_id": "milan_residence_change",
    "language": "it",
}


def capture(db):
    source = db.get(KnowledgeSource, SOURCE)
    return ingest_snapshot(
        db, source, BODY.encode(), media_type="text/plain",
        capture_method="browser_rendered_text",
        observed_url=OBS, observed_title="Come chiedere/cambiare residenza?",
        observed_last_updated="23/07/2026",
    )


def test_browser_capture_is_pending_and_never_searchable_without_review(client):
    factory = client.app.state.session_factory
    with factory.begin() as db:
        register_candidates(db)
        result = capture(db)
        assert result.status == "pending_review"
    with factory() as db:
        version = db.get(KnowledgeSourceVersion, result.version_id)
        snapshot = db.get(KnowledgeSnapshot, result.version_id)
        assert verify_snapshot(db, version)
        assert snapshot.raw_body == BODY.encode()
        assert snapshot.capture_method == "browser_rendered_text"
        assert snapshot.media_type == "text/plain"
        assert snapshot.observed_url == OBS
        assert snapshot.observed_last_updated == "23/07/2026"
        assert snapshot.extraction_version == "browser-text-v1"
        assert len(db.scalars(
            select(KnowledgePassage).where(
                KnowledgePassage.version_id == version.id
            )
        ).all()) == 2
        assert search_approved_passages(db, query="Comune", **SCOPE) == []
    with factory.begin() as db:
        approved = approve_version(
            db, version_id=result.version_id,
            expected_digest=sha256(BODY.encode()).hexdigest(),
            actor_subject="synthetic-test-reviewer",
            reason="Approved synthetic fixture to exercise existing review control.",
        )
        assert approved.version_status == "approved"
    with factory() as db:
        found = search_approved_passages(db, query="Comune", **SCOPE)
        assert len(found) == 1
        assert found[0].source_id == SOURCE


def test_cannot_launder_browser_capture_as_original_bytes(client):
    factory = client.app.state.session_factory
    with factory.begin() as db:
        register_candidates(db)
        source = db.get(KnowledgeSource, SOURCE)
        with pytest.raises(ValueError, match="Original server bytes"):
            ingest_snapshot(db, source, BODY.encode(), media_type="text/plain")
        with pytest.raises(ValueError, match="Browser captures require"):
            ingest_snapshot(
                db, source, BODY.encode(), media_type="text/html",
                capture_method="browser_rendered_text", observed_url=OBS,
                observed_title="Official page title",
                observed_last_updated="23/07/2026",
            )


@pytest.mark.parametrize("observed_url", [
    "http://servizicrm.comune.milano.it/centro-supporto/KA-00330/",
    "https://evil.example/centro-supporto/KA-00330/",
    "https://servizicrm.comune.milano.it/centro-supporto/KA-00491/",
    "https://servizicrm.comune.milano.it/centro-supporto/KA-00330/?utm_source=x",
])
def test_observed_url_identity_and_host_are_restricted(client, observed_url):
    factory = client.app.state.session_factory
    with factory.begin() as db:
        register_candidates(db)
        source = db.get(KnowledgeSource, SOURCE)
        with pytest.raises(ValueError):
            ingest_snapshot(
                db, source, BODY.encode(), media_type="text/plain",
                capture_method="browser_rendered_text", observed_url=observed_url,
                observed_title="Come chiedere/cambiare residenza?",
                observed_last_updated="23/07/2026",
            )


def test_tampering_with_browser_metadata_invalidates_trust(client):
    factory = client.app.state.session_factory
    with factory.begin() as db:
        register_candidates(db)
        result = capture(db)
    with factory.begin() as db:
        snapshot = db.get(KnowledgeSnapshot, result.version_id)
        snapshot.observed_url = "https://servizicrm.comune.milano.it/centro-supporto/KA-00491/"
    with factory() as db:
        assert not verify_snapshot(db, db.get(KnowledgeSourceVersion, result.version_id))


def test_importer_validates_source_mapping_and_provenance(tmp_path):
    path = tmp_path / (SOURCE + ".json")
    record = {
        "source_id": SOURCE, "capture_method": "browser_rendered_text",
        "captured_url": OBS, "page_title": "Come chiedere/cambiare residenza?",
        "last_updated": "23/07/2026", "article_text": BODY,
    }
    path.write_text(json.dumps(record), encoding="utf-8")
    result = prepare_captures(tmp_path)
    assert len(result) == 1
    assert result[0].digest == sha256(BODY.encode()).hexdigest()
    assert result[0].passages == 2
    record["captured_url"] = "https://evil.example/page"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError):
        prepare_captures(tmp_path)


def test_original_html_still_has_original_http_provenance(client):
    factory = client.app.state.session_factory
    with factory.begin() as db:
        register_candidates(db)
        source = db.get(KnowledgeSource, SOURCE)
        result = ingest_snapshot(
            db, source, b"<main><p>Synthetic approved HTML source.</p></main>",
            media_type="text/html",
        )
    with factory() as db:
        version = db.get(KnowledgeSourceVersion, result.version_id)
        snap = db.get(KnowledgeSnapshot, version.id)
        assert snap.capture_method == "original_http"
        assert snap.observed_url is None
        assert verify_snapshot(db, version)
