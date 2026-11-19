"""Source cards resolve only cited, current registry passages in an owned run."""

from dataclasses import replace
from uuid import UUID, uuid4

import pytest

from app.agent.contract import SendMessage
from app.agent.reconnect_router import build_reconnect_router
from app.agent.run_requests import accept_message
from app.agent.threads import create_thread, link_case_to_thread
from app.agent.worker import run_worker_step
from app.knowledge.review_service import revoke_version
from app.knowledge.search import resolve_approved_passage
from test_agent_answer_evidence import _citation_for, approved_citation, proposal  # noqa: F401
from test_agent_run_requests import ALICE, KEY
from test_knowledge_search import OTHER_HTML, SCOPE, _approve, _create


def _publish(client, answer, scope, language, *, read_evidence_scope=None, case_id=None):
    factory = client.app.state.session_factory
    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        if case_id is not None:
            assert link_case_to_thread(db, thread_id=thread_id, case_id=case_id, principal=ALICE)
        message = SendMessage(client_message_id=uuid4(), text="Synthetic source test", language=language, case_id=case_id)
        run = accept_message(db, thread_id=thread_id, principal=ALICE, key=KEY, message=message)
    scope = replace(scope, claim_reviews=tuple(replace(review, language=language) for review in scope.claim_reviews))
    snapshot = run_worker_step(
        factory, thread_id=thread_id, run_id=run.run_id, principal=ALICE, key=KEY,
        execute=lambda *_: answer, read_evidence_scope=lambda *_: scope,
    )
    assert snapshot.result.citations == answer.citations
    client.app.include_router(build_reconnect_router(key=KEY, read_evidence_scope=read_evidence_scope))
    return f"/api/v1/agent/threads/{thread_id}/runs/{run.run_id}"


@pytest.mark.parametrize(("language", "expected"), [
    ("en", "Updating the address recorded for your registered residence."),
    ("it", "Aggiornamento dell’indirizzo della residenza registrata."),
])
def test_card_keeps_exact_text_and_explains_terms_in_the_saved_language(client, auth_headers, proposal, language, expected):
    answer, scope = proposal
    citation = answer.citations[0]
    base = _publish(client, answer, scope, language)
    url = f"{base}/sources/{citation.citation_id}"
    response = client.get(url, headers=auth_headers("alice"))
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "private, no-store"
    payload = response.json()
    with client.app.state.session_factory() as db:
        source = resolve_approved_passage(db, citation_id=citation.citation_id, **SCOPE)
    assert payload["passage"] == {
        "citation": citation.model_dump(mode="json"), "section_path": source.section_path,
        "content": source.content, "source_revision": source.source_revision,
    }
    assert payload["title"] == source.title
    assert payload["source_language"] == "it"
    assert payload["explanation_language"] == language
    assert {"term": "cambio di residenza", "explanation": expected} in payload["terms"]
    assert all(term["term"] in source.content for term in payload["terms"])
    assert client.get(base, headers=auth_headers("alice")).json()["handoff"]["status"] == "verification_required"

    other = _citation_for(client, auth_headers, "scadenza")
    assert other.passage_id != citation.passage_id
    assert client.get(f"{base}/sources/{other.passage_id}", headers=auth_headers("alice")).status_code == 404
    assert client.get(url, headers=auth_headers("bob")).status_code == 404
    assert client.get(url).status_code == 401


@pytest.mark.parametrize("change", ["revoked", "superseded"])
def test_card_stops_opening_when_its_exact_version_is_no_longer_current(client, auth_headers, proposal, change):
    answer, scope = proposal
    citation = answer.citations[0]
    base = _publish(client, answer, scope, "it", read_evidence_scope=lambda *_: scope)
    owner = auth_headers("alice")
    url = f"{base}/sources/{citation.citation_id}"
    assert client.get(url, headers=owner).status_code == 200
    assert client.get(base, headers=owner).json()["handoff"]["status"] == "verified_channel"
    if change == "revoked":
        with client.app.state.session_factory.begin() as db:
            active = resolve_approved_passage(db, citation_id=citation.citation_id, **SCOPE)
            revoke_version(
                db, version_id=active.source_version_id, expected_digest=active.source_sha256,
                actor_subject="synthetic-reviewer", reason="Withdrawn source card test fixture",
            )
    else:
        version, digest = _create(client, html=OTHER_HTML)
        _approve(client, version, digest)
    unavailable = client.get(url, headers=owner)
    assert unavailable.status_code == 404
    assert unavailable.headers["Cache-Control"] == "private, no-store"
    replay = client.get(base, headers=owner).json()
    assert replay["result"]["citations"] == [citation.model_dump(mode="json")]
    assert replay["handoff"]["status"] == "verification_required"
    assert replay["handoff"]["official_channel"] is None
    assert replay["handoff"]["evidence_ids"] == []
    assert replay["handoff"]["submission_status"] == "unconfirmed"


@pytest.mark.parametrize(("language", "missing", "operation", "label"), [
    ("en", [], "open_official_channel", "Open the official channel"),
    ("it", ["housing_basis"], "provide_information", "Conferma prima i dati della pratica"),
])
def test_live_handoff_follows_current_case_scope_and_retains_submission_uncertainty(
    client, auth_headers, proposal, language, missing, operation, label,
):
    answer, scope = proposal
    answer = answer.model_copy(update={"missing_information": missing})
    current_scope = replace(
        scope, claim_reviews=tuple(replace(review, language=language) for review in scope.claim_reviews),
    )

    def read_scope(db, thread_id, run_id, case_id, principal):
        assert db.in_transaction() and principal == ALICE and case_id is None
        assert f"/threads/{thread_id}/runs/{run_id}" in base
        return current_scope

    base = _publish(client, answer, scope, language, read_evidence_scope=read_scope)
    owner = auth_headers("alice")
    response = client.get(base, headers=owner)
    assert response.headers["Cache-Control"] == "private, no-store"
    assert response.json()["handoff"] == {
        "language": language,
        "status": "verified_channel",
        "next_action": {"label": label, "operation": operation, "origin": "agent_proposal"},
        "official_channel": answer.official_channel.model_dump(mode="json"),
        "evidence_ids": [answer.citations[0].passage_id],
        "submission_status": "unconfirmed",
    }
    assert client.get(base, headers=auth_headers("bob")).status_code == 404
    assert client.get(base).status_code == 401
    current_scope = replace(current_scope, case_locations={})
    updated = client.get(base, headers=owner).json()
    assert updated["handoff"]["status"] == "verification_required"
    assert updated["handoff"]["official_channel"] is None
    assert updated["handoff"]["submission_status"] == "unconfirmed"
    assert updated["run_revision"] == response.json()["run_revision"]


def test_handoff_uses_the_owned_linked_case_and_withholds_action_after_archiving(client, auth_headers, proposal):
    answer, scope = proposal
    owner = auth_headers("alice")
    created = client.post("/api/v1/cases", headers=owner, json={})
    assert created.status_code == 201
    owned_case_id = UUID(created.json()["id"])
    current_reads = []

    def read_scope(_db, _thread_id, _run_id, case_id, principal):
        assert principal == ALICE and case_id == owned_case_id
        current_reads.append(case_id)
        return scope

    base = _publish(client, answer, scope, "it", case_id=owned_case_id, read_evidence_scope=read_scope)
    assert client.get(base, headers=owner).json()["handoff"]["status"] == "verified_channel"
    assert current_reads == [owned_case_id]
    archived = client.patch(f"/api/v1/cases/{owned_case_id}/archive", headers=owner, json={"archived": True})
    assert archived.status_code == 200
    after = client.get(base, headers=owner).json()["handoff"]
    assert after["status"] == "verification_required"
    assert after["official_channel"] is None
    assert current_reads == [owned_case_id]
