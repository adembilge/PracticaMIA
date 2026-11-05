"""Deterministic approved-evidence retrieval tests, with no live government data."""
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings
from app.knowledge.catalog import register_candidates
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.review_service import approve_version, revoke_version
from app.knowledge.snapshot_model import KnowledgePassage, KnowledgeSnapshot
from app.knowledge.snapshots import ingest_snapshot
from app.main import create_app

HTML = (b"<html><body><h1>Cambio di residenza</h1>"
        b"<p>Per questa simulazione il cambio di residenza a Milano "
        b"richiede dati sintetici per la procedura.</p>"
        b"<h2>Contratto</h2>"
        b"<p>Il contratto di locazione e una prova sintetica, "
        b"non una regola ufficiale.</p></body></html>")
OTHER_HTML = (b"<html><body><h1>Cambio di residenza</h1>"
              b"<p>Questa pagina dimostrativa indica un nuovo contenuto.</p>"
              b"</body></html>")
SCOPE = {"jurisdiction": "IT-MI-MILANO",
         "procedure_id": "milan_residence_change", "language": "it"}
SEARCH_URL = "/api/v1/knowledge/search"
CITATION_ROOT = "/api/v1/knowledge/passages/"


def _create(client, source_id="milano-residence-change", html=HTML):
    factory = client.app.state.session_factory
    with factory.begin() as db:
        register_candidates(db)
        source = db.get(KnowledgeSource, source_id)
        version = ingest_snapshot(db, source, html)
    return version.version_id, version.sha256


def _approve(client, version_id, digest):
    with client.app.state.session_factory.begin() as db:
        return approve_version(
            db, version_id=version_id,
            expected_digest=digest, actor_subject="synthetic-reviewer",
            reason="Reviewed synthetic evidence text and source applicability.",
        )


def _search(client, headers, query="residenza", **overrides):
    return client.get(
        SEARCH_URL, headers=headers,
        params={"query": query, **SCOPE, **overrides},
    )


def test_search_disabled_by_default_and_requires_catalog():
    with TestClient(create_app(Settings())) as http:
        assert http.get(SEARCH_URL, params={"query": "residenza", **SCOPE}).status_code == 404
    with pytest.raises(ValueError, match="authenticated knowledge catalog"):
        create_app(Settings(enable_knowledge_search_api=True))


def test_search_requires_valid_authentication_not_reviewer_privilege(client, auth_headers):
    assert _search(client, {}).status_code == 401
    assert _search(client, {"X-User-Id": "alice"}).status_code == 401
    _create(client)
    # Ordinary authenticated users can read approved public evidence; not approve it.
    assert _search(client, auth_headers("bob")).status_code == 200
    assert _search(client, auth_headers("bob")).json()["status"] == "insufficient_evidence"


def test_unapproved_and_unmatched_query_return_insufficient_evidence(client, auth_headers):
    _create(client)
    response = _search(client, auth_headers("bob"))
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["evidence"] == []
    assert response.json()["jurisdiction"] == SCOPE["jurisdiction"]
    assert response.json()["procedure_id"] == SCOPE["procedure_id"]


def test_approved_passages_have_resolvable_exact_citations(client, auth_headers):
    vid, digest = _create(client)
    _approve(client, vid, digest)
    user = auth_headers("bob")
    response = _search(client, user, query="residenza")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "evidence_found"
    assert data["normalized_query"] == "residenza"
    assert data["evidence"]
    found = data["evidence"][0]
    assert found["source_version_id"] == vid
    assert found["source_revision"] == 1
    assert found["source_sha256"] == digest
    assert found["source_id"] == "milano-residence-change"
    assert found["institution"] == "Comune di Milano"
    assert found["jurisdiction"] == SCOPE["jurisdiction"]
    assert found["procedure_id"] == SCOPE["procedure_id"]
    assert found["language"] == "it"
    assert "residenza" in found["content"].lower()
    assert found["citation_id"] == found["passage_id"]
    assert found["citation_id"].startswith(vid + ":")
    assert sha256(found["content"].encode()).hexdigest() == found["passage_sha256"]
    assert found["reviewed_at"] and found["retrieved_at"]
    resolved = client.get(CITATION_ROOT + found["citation_id"],
                          params=SCOPE, headers=user)
    assert resolved.status_code == 200
    assert resolved.json() == found
    assert len(_search(client, user, limit=1).json()["evidence"]) == 1


def test_jurisdiction_procedure_and_language_mismatches_never_cross(client, auth_headers):
    vid, digest = _create(client)
    _approve(client, vid, digest)
    user = auth_headers("bob")
    valid = _search(client, user).json()["evidence"]
    assert valid
    mismatch = [
        {"jurisdiction": "IT-RM-ROMA"},
        {"procedure_id": "rome_residence_change"},
        {"language": "en"},
    ]
    for filters in mismatch:
        assert _search(client, user, **filters).json()["evidence"] == []
        assert client.get(CITATION_ROOT + valid[0]["citation_id"],
                          params={**SCOPE, **filters}, headers=user).status_code == 404


def test_unreviewed_second_source_never_leaks(client, auth_headers):
    vid, digest = _create(client)
    _approve(client, vid, digest)
    _create(client, source_id="milano-residence-faq", html=HTML)
    results = _search(client, auth_headers("bob")).json()["evidence"]
    assert results
    assert {r["source_id"] for r in results} == {"milano-residence-change"}


def test_revocation_removes_search_and_resolved_citation(client, auth_headers):
    vid, digest = _create(client)
    _approve(client, vid, digest)
    user = auth_headers("bob")
    citation = _search(client, user).json()["evidence"][0]["citation_id"]
    with client.app.state.session_factory.begin() as db:
        revoke_version(
            db, version_id=vid, expected_digest=digest,
            actor_subject="synthetic-reviewer",
            reason="Revoked synthetic source due to withdrawal notice.",
        )
    assert _search(client, user).json()["status"] == "insufficient_evidence"
    assert client.get(CITATION_ROOT + citation, params=SCOPE, headers=user).status_code == 404


def test_changed_source_invalidates_old_citation_and_cannot_revive_old_revision(
    client, auth_headers,
):
    vid, digest = _create(client)
    _approve(client, vid, digest)
    user = auth_headers("bob")
    citation = _search(client, user).json()["evidence"][0]["citation_id"]
    with client.app.state.session_factory.begin() as db:
        source = db.get(KnowledgeSource, "milano-residence-change")
        ingest_snapshot(db, source, OTHER_HTML)
    assert _search(client, user).json()["evidence"] == []
    assert client.get(CITATION_ROOT + citation, params=SCOPE, headers=user).status_code == 404
    # Even manually re-pointing an old version cannot bypass the latest-revision gate.
    with client.app.state.session_factory.begin() as db:
        source = db.get(KnowledgeSource, "milano-residence-change")
        source.status = "approved"
        source.active_version_id = vid
    assert _search(client, user).json()["evidence"] == []


def test_tampered_snapshot_or_passage_is_excluded(client, auth_headers):
    vid, digest = _create(client)
    _approve(client, vid, digest)
    user = auth_headers("bob")
    citation = _search(client, user).json()["evidence"][0]["citation_id"]
    with client.app.state.session_factory.begin() as db:
        db.get(KnowledgeSnapshot, vid).raw_body = b"<p>tampered</p>"
    assert _search(client, user).json()["evidence"] == []
    assert client.get(CITATION_ROOT + citation, params=SCOPE, headers=user).status_code == 404


def test_approval_status_without_audit_is_insufficient(client, auth_headers):
    vid, _digest = _create(client)
    with client.app.state.session_factory.begin() as db:
        source = db.get(KnowledgeSource, "milano-residence-change")
        version = db.get(KnowledgeSourceVersion, vid)
        source.status = "approved"
        source.active_version_id = vid
        version.status = "approved"
        version.reviewed_at = datetime.now(timezone.utc)
        version.reviewed_by = "unverified-direct-write"
    assert _search(client, auth_headers("bob")).json()["evidence"] == []


@pytest.mark.parametrize("query", ["!!!", "-", " ", "x " * 13, "x" * 181])
def test_invalid_queries_fail_closed(client, auth_headers, query):
    assert _search(client, auth_headers(), query=query).status_code == 422


def test_query_validation_and_injection_cannot_expand_search(client, auth_headers):
    vid, digest = _create(client)
    _approve(client, vid, digest)
    user = auth_headers("bob")
    assert _search(client, user, query="residenza ; DROP TABLE cases").json()["evidence"] == []
    assert _search(client, user, query="residenzaa").json()["evidence"] == []
    assert _search(client, user, limit=999).status_code == 422
    assert _search(client, user, jurisdiction="malformed").status_code == 422
    assert _search(client, user, procedure_id="../../secrets").status_code == 422
    assert client.get(SEARCH_URL, headers=user, params={"query": "residenza"}).status_code == 422
    assert client.get(CITATION_ROOT + "invalid", params=SCOPE, headers=user).status_code == 422
    # The other parts of the authenticated API remain unaffected.
    assert client.get("/api/v1/cases", headers=user).status_code == 200
