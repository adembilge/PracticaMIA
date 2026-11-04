"""Reviewer allowlist, explicit review, stale revisions, revocation and audit tests.

Uses signed synthetic JWTs and disposable SQLite. No external government
requests and no production reviewer configuration.
"""
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings
from app.knowledge.catalog import register_candidates
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.review_model import KnowledgeReviewEvent
from app.knowledge.snapshot_model import KnowledgeSnapshot
from app.knowledge.snapshots import ingest_snapshot
from app.main import create_app
from conftest import AUDIENCE, ISSUER, JWKS_URL

SAMPLE_HTML = (
    b"<html><body><h1>Synthetic Milan source</h1>"
    b"<p>Test-only source for reviewer approval. No legal rules.</p>"
    b"</body></html>"
)
NOTE = "Reviewed synthetic snapshot and confirmed source provenance."
API_ROOT = "/api/v1/knowledge/review"


def _create_pending(client, html=SAMPLE_HTML):
    factory = client.app.state.session_factory
    with factory.begin() as db:
        register_candidates(db)
        source = db.get(KnowledgeSource, "milano-residence-change")
        result = ingest_snapshot(db, source, html)
    return result.version_id, sha256(html).hexdigest()


def _post(client, action, version_id, digest, headers, note=NOTE):
    return client.post(
        f"{API_ROOT}/versions/{version_id}/{action}",
        json={"expected_sha256": digest, "review_note": note},
        headers=headers,
    )


def test_review_endpoints_are_strictly_reviewer_only(client, auth_headers):
    vid, digest = _create_pending(client)
    queue = API_ROOT + "/queue"
    preview = f"{API_ROOT}/versions/{vid}"
    history = API_ROOT + "/sources/milano-residence-change/history"
    for path in (queue, preview, history):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=auth_headers("bob")).status_code == 403
        assert client.get(path, headers={"X-User-Id": "alice"}).status_code == 401
    for action in ("approve", "revoke"):
        assert _post(client, action, vid, digest, auth_headers("bob")).status_code == 403
        assert _post(client, action, vid, digest, auth_headers("bob",
            {"https://practicamia.example/role": "admin"})).status_code == 403
    assert client.get(queue, headers=auth_headers("alice")).status_code == 200
    with client.app.state.session_factory() as db:
        assert db.scalars(select(KnowledgeReviewEvent)).all() == []


def test_review_disabled_unless_both_flag_and_allowlist_are_configured():
    with TestClient(create_app(Settings())) as http:
        assert http.get(API_ROOT + "/queue").status_code == 404
    with pytest.raises(ValueError, match="authenticated knowledge catalog"):
        create_app(Settings(enable_knowledge_review_api=True))
    with pytest.raises(ValueError, match="subject allowlist"):
        create_app(Settings(
            enable_demo_case_api=True, enable_knowledge_catalog_api=True,
            enable_knowledge_review_api=True,
        ))
    with pytest.raises(ValueError, match="subject identifiers"):
        create_app(Settings(
            enable_demo_case_api=True, enable_knowledge_catalog_api=True,
            enable_knowledge_review_api=True,
            knowledge_reviewer_subjects=frozenset({"x" * 256}),
        ))


def test_review_queue_preview_hash_and_passages(client, auth_headers):
    vid, digest = _create_pending(client)
    headers = auth_headers("alice")
    queue = client.get(API_ROOT + "/queue", headers=headers)
    assert queue.status_code == 200
    assert len(queue.json()) == 1
    assert queue.json()[0]["version_id"] == vid
    assert queue.json()[0]["content_sha256"] == digest
    assert queue.json()[0]["version_status"] == "pending_review"
    preview = client.get(f"{API_ROOT}/versions/{vid}", headers=headers)
    assert preview.status_code == 200
    data = preview.json()
    assert data["integrity_verified"] is True
    assert "Test-only source" in data["normalized_text"]
    assert "<html>" not in data["normalized_text"]
    assert len(data["passages"]) >= 1
    for passage in data["passages"]:
        assert (data["normalized_text"][passage["start_offset"]:passage["end_offset"]]
                == passage["content"])
    assert client.get(f"{API_ROOT}/versions/{uuid4()}", headers=headers).status_code == 404


def test_hash_confirmation_and_attestation_are_required(client, auth_headers):
    vid, digest = _create_pending(client)
    headers = auth_headers("alice")
    assert _post(client, "approve", vid, "0" * 64, headers).status_code == 409
    assert _post(client, "approve", vid, digest, headers, "No").status_code == 422
    extra = client.post(
        f"{API_ROOT}/versions/{vid}/approve",
        json={"expected_sha256": digest, "review_note": NOTE, "actor_subject": "bob"},
        headers=headers,
    )
    assert extra.status_code == 422
    with client.app.state.session_factory() as db:
        assert db.get(KnowledgeSourceVersion, vid).status == "pending_review"
        assert db.scalars(select(KnowledgeReviewEvent)).all() == []


def test_approval_populates_trusted_catalog_and_durable_audit(client, auth_headers):
    vid, digest = _create_pending(client)
    headers = auth_headers("alice")
    response = _post(client, "approve", vid, digest, headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["source_status"] == payload["version_status"] == "approved"
    assert payload["audit_id"]
    result = client.get("/api/v1/knowledge/sources", headers=headers)
    assert result.status_code == 200
    assert result.json()["sources"][0]["source_version_id"] == vid
    assert _post(client, "approve", vid, digest, headers).status_code == 409
    history = client.get(
        API_ROOT + "/sources/milano-residence-change/history", headers=headers
    ).json()
    assert [e["action"] for e in history] == ["approved"]
    assert history[0]["actor_subject"] == "alice"
    assert history[0]["reason"] == NOTE
    assert history[0]["content_sha256"] == digest
    assert history[0]["old_source_status"] == "candidate"
    assert history[0]["new_source_status"] == "approved"
    assert history[0]["old_version_status"] == "pending_review"
    assert history[0]["new_version_status"] == "approved"
    with client.app.state.session_factory() as db:
        version = db.get(KnowledgeSourceVersion, vid)
        assert version.reviewed_by == "alice"
        assert version.reviewed_at is not None
        assert len(db.scalars(select(KnowledgeReviewEvent)).all()) == 1


def test_revoke_requires_current_active_version_and_is_audited(client, auth_headers):
    vid, digest = _create_pending(client)
    headers = auth_headers("alice")
    assert _post(client, "revoke", vid, digest, headers).status_code == 409
    assert _post(client, "approve", vid, digest, headers).status_code == 200
    assert _post(client, "revoke", vid, "b" * 64, headers).status_code == 409
    revocation = _post(client, "revoke", vid, digest, headers, note=
                       "Official material was withdrawn; reviewer revoked approval.")
    assert revocation.status_code == 200, revocation.text
    assert revocation.json()["source_status"] == "revoked"
    assert revocation.json()["version_status"] == "revoked"
    assert _post(client, "revoke", vid, digest, headers).status_code == 409
    assert client.get("/api/v1/knowledge/sources",
                      headers=headers).json()["sources"] == []
    with client.app.state.session_factory() as db:
        source = db.get(KnowledgeSource, "milano-residence-change")
        assert source.active_version_id is None
        events = db.scalars(select(KnowledgeReviewEvent).order_by(
            KnowledgeReviewEvent.occurred_at)).all()
        assert [e.action for e in events] == ["approved", "revoked"]


def test_new_content_invalidates_prior_approval_and_audits_change(
    client, auth_headers,
):
    vid, digest = _create_pending(client)
    headers = auth_headers("alice")
    assert _post(client, "approve", vid, digest, headers).status_code == 200
    updated = SAMPLE_HTML.replace(b"Test-only", b"Updated synthetic")
    with client.app.state.session_factory.begin() as db:
        source = db.get(KnowledgeSource, "milano-residence-change")
        result = ingest_snapshot(db, source, updated)
        assert result.revision == 2
        assert result.previous_approval_invalidated
    assert client.get("/api/v1/knowledge/sources",
                      headers=headers).json()["sources"] == []
    assert _post(client, "approve", vid, digest, headers).status_code == 409
    new_digest = sha256(updated).hexdigest()
    assert _post(client, "approve", result.version_id, new_digest,
                 headers).status_code == 200
    with client.app.state.session_factory() as db:
        events = db.scalars(
            select(KnowledgeReviewEvent).order_by(KnowledgeReviewEvent.occurred_at)
        ).all()
        assert [event.action for event in events] == [
            "approved", "source_changed", "approved",
        ]
        assert events[1].actor_subject == "system:ingestion"
        assert events[1].new_source_status == "candidate"
        assert db.get(KnowledgeSourceVersion, vid).status == "approved"


def test_older_pending_version_cannot_be_approved(client, auth_headers):
    first_id, first_digest = _create_pending(client)
    updated = SAMPLE_HTML.replace(b"Test-only", b"New synthetic")
    with client.app.state.session_factory.begin() as db:
        source = db.get(KnowledgeSource, "milano-residence-change")
        second = ingest_snapshot(db, source, updated)
    headers = auth_headers("alice")
    assert _post(client, "approve", first_id, first_digest, headers).status_code == 409
    assert _post(client, "approve", second.version_id, sha256(updated).hexdigest(),
                 headers).status_code == 200


def test_corrupted_snapshot_and_changed_url_fail_closed(client, auth_headers):
    vid, digest = _create_pending(client)
    headers = auth_headers("alice")
    with client.app.state.session_factory.begin() as db:
        db.get(KnowledgeSnapshot, vid).normalized_text = "tampered text"
    assert client.get(f"{API_ROOT}/versions/{vid}", headers=headers).status_code == 409
    assert _post(client, "approve", vid, digest, headers).status_code == 409
    with client.app.state.session_factory.begin() as db:
        db.get(KnowledgeSnapshot, vid).raw_body = b"<p>altered</p>"
    assert _post(client, "approve", vid, digest, headers).status_code == 409
    with client.app.state.session_factory() as db:
        assert db.scalars(select(KnowledgeReviewEvent)).all() == []


def test_case_routes_still_operate_when_review_enabled(client, auth_headers):
    owner = auth_headers("alice")
    created = client.post("/api/v1/cases", json={}, headers=owner)
    assert created.status_code == 201
    assert client.get("/api/v1/cases", headers=owner).status_code == 200
    assert client.delete("/api/v1/cases/" + created.json()["id"],
                         headers=owner).status_code == 204
