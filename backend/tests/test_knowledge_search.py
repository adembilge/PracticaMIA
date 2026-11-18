"""Deterministic approved-evidence retrieval tests, with no live government data."""
from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.agent.catalogue_evidence import (
    find_catalogue_evidence, resolve_catalogue_evidence,
)
from app.auth.tokens import Principal
from app.cases.intake_model import CaseIntake
from app.config import Settings
from app.knowledge.catalog import register_candidates
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.review_service import approve_version, revoke_version
from app.knowledge.snapshot_model import KnowledgePassage, KnowledgeSnapshot
from app.knowledge.snapshots import ingest_snapshot
from app.main import create_app
from test_case_intake import FACTS, create_scoped_case

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


def test_phase4_catalogue_and_search_api_share_exact_approved_evidence(client, auth_headers):
    user = auth_headers("bob")
    case_id = UUID(create_scoped_case(client, user))
    intake = f"/api/v1/cases/{case_id}/intake"
    assert client.put(intake, headers=user, json={"facts": FACTS, "confirm": True}).status_code == 200
    context = {"case_id": case_id, "principal": Principal("bob")}
    version, digest = _create(client)
    _approve(client, version, digest)

    found = _search(client, user, limit=1).json()["evidence"][0]
    with client.app.state.session_factory() as db:
        result = find_catalogue_evidence(db, **context, query="residenza", limit=1)
        assert result.status == "evidence_found"
        match, = result.passages
        assert resolve_catalogue_evidence(
            db, **context, citation_id=found["citation_id"],
        ).passages == result.passages

    assert str(match.citation.source_version_id) == found["source_version_id"] == version
    assert match.citation.source_id == found["source_id"]
    assert match.citation.passage_id == found["passage_id"]
    assert match.citation.citation_id == found["citation_id"]
    assert match.citation.location_id == found["jurisdiction"]
    assert match.citation.procedure_id == found["procedure_id"]
    assert str(match.citation.official_url) == found["official_url"]
    assert match.citation.publisher == found["institution"]
    assert match.content == found["content"]
    assert match.section_path == found["section_path"]

    revised_body = OTHER_HTML.replace(b"nuovo contenuto", b"nuovo contenuto sulla residenza")
    revised, revised_digest = _create(client, html=revised_body)
    with client.app.state.session_factory() as db:
        assert find_catalogue_evidence(db, **context, query="residenza").passages == ()
        assert resolve_catalogue_evidence(
            db, **context, citation_id=match.citation.citation_id,
        ).status == "insufficient_evidence"
    _approve(client, revised, revised_digest)
    updated = _search(client, user, limit=1).json()["evidence"][0]
    assert updated["source_version_id"] == revised != version
    assert client.get(
        CITATION_ROOT + found["citation_id"], params=SCOPE, headers=user,
    ).status_code == 404
    with client.app.state.session_factory() as db:
        latest = resolve_catalogue_evidence(db, **context, citation_id=updated["citation_id"])
        assert updated["source_version_id"] == str(latest.passages[0].citation.source_version_id)
        assert latest.passages[0].citation.passage_id != match.citation.passage_id

    with client.app.state.session_factory.begin() as db:
        revoke_version(
            db, version_id=revised, expected_digest=revised_digest,
            actor_subject="synthetic-reviewer", reason="Withdrawal of this local fixture.",
        )
    assert client.get(CITATION_ROOT + updated["citation_id"], params=SCOPE, headers=user).status_code == 404
    with client.app.state.session_factory() as db:
        assert resolve_catalogue_evidence(
            db, **context, citation_id=updated["citation_id"],
        ).passages == ()


def test_phase4_case_evidence_hides_foreign_or_missing_cases(client, auth_headers):
    user = auth_headers("alice")
    case_id = UUID(create_scoped_case(client, user))
    assert client.put(
        f"/api/v1/cases/{case_id}/intake", headers=user, json={"facts": FACTS, "confirm": True},
    ).status_code == 200
    version, digest = _create(client)
    _approve(client, version, digest)
    citation_id = _search(client, user, limit=1).json()["evidence"][0]["citation_id"]

    with client.app.state.session_factory() as db:
        for target, subject in ((case_id, "bob"), (uuid4(), "alice")):
            found = find_catalogue_evidence(
                db, case_id=target, principal=Principal(subject), query="residenza",
            )
            resolved = resolve_catalogue_evidence(
                db, case_id=target, principal=Principal(subject), citation_id=citation_id,
            )
            assert found == resolved
            assert found.status == "case_unavailable"
            assert found.passages == ()
            assert found.missing_fields == ()


def test_phase4_case_evidence_reloads_confirmation_and_scope(client, auth_headers):
    user = auth_headers("alice")
    case_id = UUID(client.post("/api/v1/cases", json={}, headers=user).json()["id"])
    root = f"/api/v1/cases/{case_id}"
    context = {"case_id": case_id, "principal": Principal("alice")}
    version, digest = _create(client)
    _approve(client, version, digest)
    citation_id = _search(client, user, limit=1).json()["evidence"][0]["citation_id"]

    def check(status, fields=()):
        with client.app.state.session_factory() as db:
            result = find_catalogue_evidence(db, **context, query="residenza", limit=1)
            exact = resolve_catalogue_evidence(db, **context, citation_id=citation_id)
            assert result == exact
            assert result.status == status
            assert result.missing_fields == fields
            assert bool(result.passages) == (status == "evidence_found")

    check("needs_information", ("scope_answers",))
    assert client.patch(root + "/scope", headers=user, json={
        "answers": ["yes", "yes", "yes", "no", "yes"],
    }).status_code == 200
    check("needs_information", ("intake_confirmation",))

    for facts, confirmed, status, fields in (
        (FACTS, False, "needs_information", ("intake_confirmation",)),
        (FACTS, True, "evidence_found", ()),
        ({**FACTS, "destination_municipality": "other"}, True, "unsupported_scope", ()),
        (FACTS, True, "evidence_found", ()),
        (FACTS, False, "needs_information", ("intake_confirmation",)),
    ):
        response = client.put(root + "/intake", headers=user, json={"facts": facts, "confirm": confirmed})
        assert response.status_code == 200
        check(status, fields)

    assert client.patch(root + "/scope", headers=user, json={
        "answers": ["no"],
    }).status_code == 200
    check("unsupported_scope")


def test_phase4_case_evidence_fails_closed_for_invalid_or_foreign_intake(client, auth_headers):
    user = auth_headers("alice")
    case_id = UUID(create_scoped_case(client, user))
    assert client.put(
        f"/api/v1/cases/{case_id}/intake", headers=user, json={"facts": FACTS, "confirm": True},
    ).status_code == 200
    context = {"case_id": case_id, "principal": Principal("alice")}
    for changes, expected in (
        ({"facts": {"destination_municipality": ["milano"]}}, ("intake_confirmation",)),
        ({"facts": {"destination_municipality": "milano"}}, (
            "citizenship_class", "registration_context", "household_scope", "housing_basis",
        )),
        ({"facts": FACTS, "owner_subject": "bob"}, ("intake_confirmation",)),
    ):
        with client.app.state.session_factory.begin() as db:
            row = db.get(CaseIntake, str(case_id))
            for name, value in changes.items():
                setattr(row, name, value)
        with client.app.state.session_factory() as db:
            result = find_catalogue_evidence(db, **context, query="residenza")
            assert result.status == "needs_information"
            assert result.missing_fields == expected
            assert not result.passages
