"""Source cards resolve only cited, current registry passages in an owned run."""

from dataclasses import replace
from uuid import uuid4

import pytest

from app.agent.contract import SendMessage
from app.agent.reconnect_router import build_reconnect_router
from app.agent.run_requests import accept_message
from app.agent.threads import create_thread
from app.agent.worker import run_worker_step
from app.knowledge.review_service import revoke_version
from app.knowledge.search import resolve_approved_passage
from test_agent_answer_evidence import _citation_for, approved_citation, proposal  # noqa: F401
from test_agent_run_requests import ALICE, KEY
from test_knowledge_search import OTHER_HTML, SCOPE, _approve, _create


def _publish(client, answer, scope, language):
    factory = client.app.state.session_factory
    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        message = SendMessage(client_message_id=uuid4(), text="Synthetic source test", language=language)
        run = accept_message(db, thread_id=thread_id, principal=ALICE, key=KEY, message=message)
    scope = replace(scope, claim_reviews=tuple(replace(review, language=language) for review in scope.claim_reviews))
    snapshot = run_worker_step(
        factory, thread_id=thread_id, run_id=run.run_id, principal=ALICE, key=KEY,
        execute=lambda *_: answer, read_evidence_scope=lambda *_: scope,
    )
    assert snapshot.result.citations == answer.citations
    client.app.include_router(build_reconnect_router(key=KEY))
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

    other = _citation_for(client, auth_headers, "scadenza")
    assert other.passage_id != citation.passage_id
    assert client.get(f"{base}/sources/{other.passage_id}", headers=auth_headers("alice")).status_code == 404
    assert client.get(url, headers=auth_headers("bob")).status_code == 404
    assert client.get(url).status_code == 401


@pytest.mark.parametrize("change", ["revoked", "superseded"])
def test_card_stops_opening_when_its_exact_version_is_no_longer_current(client, auth_headers, proposal, change):
    answer, scope = proposal
    citation = answer.citations[0]
    base = _publish(client, answer, scope, "it")
    owner = auth_headers("alice")
    url = f"{base}/sources/{citation.citation_id}"
    assert client.get(url, headers=owner).status_code == 200
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
