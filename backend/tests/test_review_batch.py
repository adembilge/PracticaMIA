"""Authenticated, atomic browser-source review from a phone-sized client.

Only synthetic official-looking text is used in disposable SQLite. The tests
never approve real municipal evidence, use real Auth0 tokens, or modify Neon.
"""
from dataclasses import replace

from sqlalchemy import select

from app.knowledge.catalog import register_candidates
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.review_model import KnowledgeReviewEvent
from app.knowledge.snapshot_model import KnowledgeSnapshot
from app.knowledge.snapshots import ingest_snapshot

API = "/api/v1/knowledge/review"
NOTE = ("I checked each captured official article and its applicability, "
        "including the browser-rendered evidence limitation.")
SOURCES = [
    ("milano-residence-faq", "KA-00330", "Come chiedere/cambiare residenza?"),
    ("milano-residence-minor-documents", "KA-00434",
     "Quali documenti servono per cambiare la residenza di un minore?"),
]


def prepare(client):
    results = []
    with client.app.state.session_factory.begin() as db:
        register_candidates(db)
        for source_id, code, title in SOURCES:
            source = db.get(KnowledgeSource, source_id)
            body = ("Synthetic private test only for " + code
                    + ". There are no actual government rules here.").encode()
            original_url = source.official_url
            if source_id == "milano-residence-faq":
                observed_url = original_url + "Richiestacambio-residenza-come-procedere"
            else:
                observed_url = original_url
            version = ingest_snapshot(
                db, source, body, media_type="text/plain",
                capture_method="browser_rendered_text",
                observed_url=observed_url, observed_title=title,
                observed_last_updated="23/07/2026",
            )
            results.append({
                "source_id": source_id, "version_id": version.version_id,
                "expected_sha256": version.sha256,
            })
    return results


def payload(items):
    return {
        "items": items, "review_note": NOTE,
        "confirmed_source_review": True,
    }


def test_mobile_queue_does_not_expose_unapproved_pdf_and_reviewer_access(
    client, auth_headers,
):
    items = prepare(client)
    missing = client.get(API + "/browser-queue")
    assert missing.status_code == 401
    forbidden = client.get(API + "/browser-queue", headers=auth_headers("bob"))
    assert forbidden.status_code == 403
    response = client.get(API + "/browser-queue", headers=auth_headers("alice"))
    assert response.status_code == 200
    rows = response.json()
    assert {r["source_id"] for r in rows} == {x["source_id"] for x in items}
    assert all(r["integrity_verified"] for r in rows)
    assert all(r["captured_text_preview"] for r in rows)
    assert all(r["observed_last_updated"] == "23/07/2026" for r in rows)
    assert all("Allegato" not in r["title"] for r in rows)


def test_batch_approval_is_atomic_audited_and_requires_verified_reviewer(
    client, auth_headers,
):
    items = prepare(client)
    route = API + "/approve-browser-batch"
    assert client.post(route, json=payload(items)).status_code == 401
    assert client.post(route, json=payload(items),
                       headers=auth_headers("bob")).status_code == 403
    assert client.post(route, json=payload(items),
                       headers=auth_headers("bob", {
                           "https://practicamia.example/role": "admin",
                       })).status_code == 403
    result = client.post(route, json=payload(items),
                         headers=auth_headers("alice"))
    assert result.status_code == 200, result.text
    assert len(result.json()) == 2
    assert all(r["version_status"] == "approved" for r in result.json())
    with client.app.state.session_factory() as db:
        versions = db.scalars(select(KnowledgeSourceVersion)).all()
        assert len(versions) == 2
        assert all(v.status == "approved" and v.reviewed_by == "alice"
                   for v in versions)
        events = db.scalars(select(KnowledgeReviewEvent)).all()
        assert len(events) == 2
        assert all(e.action == "approved" and
                   e.actor_subject == "alice" and
                   e.reason.startswith("Batch browser-source review:")
                   for e in events)
    empty = client.get(API + "/browser-queue", headers=auth_headers("alice"))
    assert empty.json() == []


def test_bad_digest_reverts_entire_batch_and_never_writes_partial_audit(
    client, auth_headers,
):
    items = prepare(client)
    items[1]["expected_sha256"] = "a" * 64
    response = client.post(API + "/approve-browser-batch", json=payload(items),
                           headers=auth_headers("alice"))
    assert response.status_code == 409
    with client.app.state.session_factory() as db:
        versions = db.scalars(select(KnowledgeSourceVersion)).all()
        assert all(v.status == "pending_review" and v.reviewed_by is None
                   for v in versions)
        assert db.scalars(select(KnowledgeReviewEvent)).all() == []


def test_duplicate_versions_no_attestation_and_extra_keys_are_forbidden(
    client, auth_headers,
):
    items = prepare(client)
    path = API + "/approve-browser-batch"
    for bad in [
        {**payload(items), "confirmed_source_review": False},
        payload([items[0], items[0]]),
        {**payload(items), "actor_subject": "alice"},
        {**payload(items), "review_note": "approved"},
    ]:
        assert client.post(path, json=bad,
                           headers=auth_headers("alice")).status_code == 422
    with client.app.state.session_factory() as db:
        assert all(v.status == "pending_review"
                   for v in db.scalars(select(KnowledgeSourceVersion)).all())


def test_original_pdf_cannot_enter_bulk_approval(client, auth_headers):
    items = prepare(client)
    with client.app.state.session_factory.begin() as db:
        source = db.get(KnowledgeSource, "milano-residence-non-eu-allegato-a")
        fake_pdf = b"<html><body><p>Not a real government PDF.</p></body></html>"
        # This is an ORIGINAL-HTML test fixture to demonstrate media
        # separation; real PDF parsing is independently covered elsewhere.
        version = ingest_snapshot(db, source, fake_pdf, media_type="text/html")
    items.append({
        "source_id": source.id,
        "version_id": version.version_id,
        "expected_sha256": version.sha256,
    })
    result = client.post(API + "/approve-browser-batch", json=payload(items),
                         headers=auth_headers("alice"))
    assert result.status_code == 409
    with client.app.state.session_factory() as db:
        assert db.scalars(select(KnowledgeReviewEvent)).all() == []


def test_batch_approval_is_disabled_in_production_even_for_reviewers(
    client, auth_headers,
):
    items = prepare(client)
    client.app.state.settings = replace(
        client.app.state.settings, deployment_environment="production",
    )
    response = client.post(API + "/approve-browser-batch", json=payload(items),
                           headers=auth_headers("alice"))
    assert response.status_code == 404
    with client.app.state.session_factory() as db:
        assert db.scalars(select(KnowledgeReviewEvent)).all() == []


def test_corrupt_browser_text_blocks_batch_and_rolls_back_all(
    client, auth_headers,
):
    items = prepare(client)
    with client.app.state.session_factory.begin() as db:
        db.get(KnowledgeSnapshot, items[1]["version_id"]).normalized_text = "tampered"
    result = client.post(API + "/approve-browser-batch", json=payload(items),
                         headers=auth_headers("alice"))
    assert result.status_code == 409
    with client.app.state.session_factory() as db:
        assert all(v.status == "pending_review"
                   for v in db.scalars(select(KnowledgeSourceVersion)).all())
