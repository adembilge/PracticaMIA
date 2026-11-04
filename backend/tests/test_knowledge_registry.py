"""Candidate registry, evidence review gate, ownership and fail-closed API tests."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings
from app.knowledge.catalog import (
    candidate_sources, register_candidates, validate_candidate,
)
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.html_extraction import extract_html, EXTRACTION_VERSION
from app.knowledge.snapshot_model import KnowledgeSnapshot, KnowledgePassage
from hashlib import sha256
from app.main import create_app
from conftest import AUDIENCE, ISSUER, JWKS_URL


def test_bundled_sources_are_only_candidates():
    sources = candidate_sources()
    assert len(sources) == 4
    assert len(set(item["id"] for item in sources)) == len(sources)
    assert all(item["jurisdiction"] == "IT-MI-MILANO" for item in sources)
    assert all(item["official_url"].startswith("https://") for item in sources)
    assert all("status" not in item for item in sources)


@pytest.mark.parametrize("url", [
    "http://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza",
    "https://www.comune.milano.it.evil.example/path",
    "https://www.comune.milano.it@attacker.example/path",
    "https://www.comune.milano.it/path?token=secret",
    "https://www.comune.milano.it/path#anchor",
    "https://www.comune.milano.it:444/path",
    "https://169.254.169.254/latest/meta-data/",
])
def test_candidate_urls_are_restricted_to_official_hosts(url):
    source = dict(candidate_sources()[0], official_url=url)
    with pytest.raises(ValueError):
        validate_candidate(source)


def test_candidate_schema_rejects_jurisdiction_and_undocumented_fields():
    candidate = candidate_sources()[0]
    with pytest.raises(ValueError, match="jurisdiction"):
        validate_candidate({**candidate, "jurisdiction": "IT-RM-ROMA"})
    with pytest.raises(ValueError, match="unexpected or missing"):
        validate_candidate({**candidate, "unapproved_rule": "mandatory"})


def test_candidate_registration_is_idempotent_and_cannot_promote(client):
    factory = client.app.state.session_factory
    with factory.begin() as db:
        assert register_candidates(db) == 4
    with factory.begin() as db:
        assert register_candidates(db) == 0
    with factory() as db:
        sources = db.scalars(select(KnowledgeSource)).all()
        assert len(sources) == 4
        assert all(s.status == "candidate" and not s.active_version_id
                   for s in sources)


def test_catalog_requires_login_and_contains_no_pending_sources(client, auth_headers):
    assert client.get("/api/v1/knowledge/sources").status_code == 401
    with client.app.state.session_factory.begin() as db:
        register_candidates(db)
    response = client.get("/api/v1/knowledge/sources", headers=auth_headers())
    assert response.status_code == 200
    assert response.json() == {"status": "insufficient_evidence", "sources": []}


def test_only_approved_active_hash_bound_versions_are_visible(client, auth_headers):
    now = datetime.now(timezone.utc)
    html = b'<html><body><main><h1>Sample procedure</h1><p>Official-like synthetic test text.</p></main></body></html>'
    extracted = extract_html(html)
    digest = sha256(html).hexdigest()
    sid = "milano-residence-change"
    vid = str(uuid4())
    factory = client.app.state.session_factory
    with factory.begin() as db:
        register_candidates(db)
        source = db.get(KnowledgeSource, sid)
        source.active_version_id = vid
        source.status = "approved"
        db.add(KnowledgeSourceVersion(
            id=vid, source_id=sid, revision=1,
            content_sha256=digest,
            retrieved_at=now, status="pending_review",
        ))
        db.add(KnowledgeSnapshot(version_id=vid, fetched_url=source.official_url,
                                 media_type="text/html", size_bytes=len(html),
                                 extraction_version=EXTRACTION_VERSION,
                                 raw_body=html, normalized_text=extracted.normalized_text))
        for passage in extracted.passages:
            db.add(KnowledgePassage(id=f"{vid}:{passage.ordinal:04d}", version_id=vid,
                                    ordinal=passage.ordinal, section_path=passage.section_path,
                                    start_offset=passage.start_offset, end_offset=passage.end_offset,
                                    content=passage.content, content_sha256=passage.content_sha256))
    url = "/api/v1/knowledge/sources"
    headers = auth_headers()
    assert client.get(url, headers=headers).json()["sources"] == []
    with factory.begin() as db:
        version = db.get(KnowledgeSourceVersion, vid)
        version.status = "approved"
        version.reviewed_at = now
        version.reviewed_by = "authorized-reviewer"
    response = client.get(url, headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "approved_sources_available"
    assert len(payload["sources"]) == 1
    assert payload["sources"][0]["source_id"] == sid
    assert payload["sources"][0]["source_version_id"] == vid
    assert payload["sources"][0]["content_sha256"] == digest
    assert "reviewed_at" in payload["sources"][0]

    with factory.begin() as db:
        db.get(KnowledgeSourceVersion, vid).status = "revoked"
    assert client.get(url, headers=headers).json()["sources"] == []
    with factory.begin() as db:
        db.get(KnowledgeSourceVersion, vid).status = "approved"
        db.get(KnowledgeSource, sid).active_version_id = str(uuid4())
    assert client.get(url, headers=headers).json()["sources"] == []


def test_source_mismatch_cannot_expose_different_version(client, auth_headers):
    factory = client.app.state.session_factory
    now = datetime.now(timezone.utc)
    with factory.begin() as db:
        register_candidates(db)
        first = db.get(KnowledgeSource, "milano-residence-change")
        other = db.get(KnowledgeSource, "milano-residence-faq")
        vid = str(uuid4())
        other.status = "approved"
        first.status = "approved"
        first.active_version_id = vid
        db.add(KnowledgeSourceVersion(
            id=vid, source_id=other.id, revision=1,
            content_sha256="b" * 64,
            retrieved_at=now, reviewed_at=now,
            reviewed_by="reviewer", status="approved",
        ))
    assert client.get("/api/v1/knowledge/sources",
                      headers=auth_headers()).json()["sources"] == []


def test_feature_stays_disabled_by_default():
    with TestClient(create_app(Settings())) as http:
        assert http.get("/api/v1/knowledge/sources").status_code == 404


def test_feature_requires_authenticated_backend():
    with pytest.raises(ValueError, match="authenticated case API"):
        create_app(Settings(enable_knowledge_catalog_api=True))


def test_no_information_in_unauthorized_header(client):
    response = client.get("/api/v1/knowledge/sources",
                          headers={"X-User-Id": "attacker"})
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"
