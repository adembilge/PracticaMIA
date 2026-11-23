"""One owned thread, two private documents and two municipal case boundaries."""

from dataclasses import replace
from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.agent.answer_evidence import AnswerEvidenceScope, ClaimPassageSupport, ReviewedClaimSupport
from app.agent.candidate_resolution import choose_candidate_step
from app.agent.catalogue_evidence import catalogue_passage
from app.agent.contract import AnswerResult, EvidenceLinkedClaim
from app.agent.reconnect_router import build_reconnect_router
from app.agent.run_requests import AgentRunRequest
from app.agent.run_events import read_run_events
from app.agent.threads import create_thread, link_case_to_thread
from app.agent.worker import run_worker_step
from app.knowledge.model import KnowledgeSource
from app.knowledge.review_service import approve_version
from app.knowledge.search import search_approved_passages
from app.knowledge.service_areas import CaseLocation, EffectivePeriod
from app.knowledge.snapshots import ingest_snapshot
from app.rules.engine import JURISDICTION, PROCEDURE
from test_agent_clarification_context import STATE
from test_agent_reconnect_http import assert_private_error
from test_agent_run_requests import ALICE, KEY
from test_private_document_intelligence import FACTS, prepare_case, review_payload, sample_pdf, upload
from test_private_documents import document_client  # noqa: F401 - shared signed vault fixture
from test_service_areas import area


COMO_FIXTURE = "IT-CO-COMO"


def _source(db, *, municipality, label):
    """Seed and review a fictional passage in the disposable test database."""
    statement = f"La scheda sintetica riguarda solo il comune di {label}."
    source = KnowledgeSource(
        id=f"synthetic-isolation-{municipality}", institution=f"Archivio sintetico {label}",
        jurisdiction=municipality, procedure_id=PROCEDURE, language="it",
        title="Scheda sintetica", document_type="service_page",
        official_url=f"https://www.comune.milano.it/synthetic-test-{municipality}",
    )
    db.add(source)
    db.flush()
    version = ingest_snapshot(db, source, f"<html><body><p>{statement}</p></body></html>".encode())
    approve_version(
        db, version_id=version.version_id, expected_digest=version.sha256,
        actor_subject="synthetic-isolation-fixture", reason="Local cross-case test fixture",
    )
    [passage] = search_approved_passages(
        db, jurisdiction=municipality, procedure_id=PROCEDURE, language="it", query="scheda sintetica",
    )
    citation = catalogue_passage(passage).citation
    assignment = replace(
        area(
            assignment_id=f"synthetic-area-{municipality}", authority_id=f"synthetic-authority-{municipality}",
            procedure_id=PROCEDURE, unit_ids=(municipality,), evidence_ref=citation.passage_id,
        ),
        # Both dates fall within both periods, so only the locality can exclude the other passage.
        effective_period=EffectivePeriod("move_in_date", date(2026, 11, 1), date(2026, 11, 30)),
    )
    review = ReviewedClaimSupport(
        kind="authority", language="it", statement=statement,
        passages=(ClaimPassageSupport(citation.passage_id, assignment.assignment_id, statement),),
    )
    return citation, assignment, review


@pytest.mark.parametrize("order", [(0, 1), (1, 0)], ids=["milan-first", "como-first"])
def test_two_pending_cases_keep_documents_replies_and_citations_separate(document_client, auth_headers, order):
    client = document_client
    owner, other_account = auth_headers("alice"), auth_headers("bob")
    factory, settings = client.app.state.session_factory, client.app.state.settings
    milan_case = prepare_case(client, owner)
    como_case = client.post("/api/v1/conversations/tasks", json={}, headers=owner).json()["id"]
    case_ids = (milan_case, como_case)
    municipalities = (JURISDICTION, COMO_FIXTURE)
    labels = ("Milano", "Como")
    dates = (date(2026, 11, 5), date(2026, 11, 16))
    statuses = ("reviewed", "needs_review")
    milan_facts = {field: value for field, value in FACTS.items() if field != "move_in_date"}
    assert client.put(f"/api/v1/conversations/tasks/{milan_case}/intake", headers=owner, json={
        "facts": milan_facts, "confirm": True,
    }).status_code == 200
    unsuited = client.patch(f"/api/v1/conversations/tasks/{como_case}/scope", headers=owner, json={"answers": ["yes", "no"]})
    assert unsuited.status_code == 200 and unsuited.json()["status"] == "unsupported"

    # The signed vault helper sends the same original filename for both distinct PDFs.
    document_ids, intelligence_urls = [], []
    for case_id, move_date in zip(case_ids, dates, strict=True):
        doc_id = upload(client, owner, case_id, sample_pdf(f"Move-in date: {move_date.isoformat()}"))
        path = f"/api/v1/conversations/tasks/{case_id}/private-documents"
        assert [row["id"] for row in client.get(path, headers=owner).json()] == [doc_id]
        doc_url = f"{path}/{doc_id}/intelligence"
        extracted = client.post(doc_url + "/extract", headers=owner)
        assert extracted.status_code == 200
        assert [item["suggested_value"] for item in extracted.json()["candidates"]] == [move_date.isoformat()]
        if case_id == milan_case:
            assert client.put(doc_url + "/review", headers=owner, json=review_payload(extracted.json())).status_code == 200
        document_ids.append(doc_id)
        intelligence_urls.append(doc_url)
    assert document_ids[0] != document_ids[1]
    for index, case_id in enumerate(case_ids):
        wrong = f"/api/v1/conversations/tasks/{case_id}/private-documents/{document_ids[1 - index]}/intelligence"
        assert client.get(wrong, headers=owner).status_code == 404
        assert client.get(intelligence_urls[index], headers=other_account).status_code == 404

    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        for case_id in case_ids:
            assert link_case_to_thread(db, thread_id=thread_id, case_id=UUID(case_id), principal=ALICE)
        sources = [
            _source(db, municipality=municipality, label=label)
            for municipality, label in zip(municipalities, labels, strict=True)
        ]
    citations, assignments, reviews = zip(*sources, strict=True)
    trusted = frozenset(citation.passage_id for citation in citations)
    claims = [
        EvidenceLinkedClaim(kind=review.kind, statement=review.statement, evidence_ids=[citation.passage_id])
        for citation, review in zip(citations, reviews, strict=True)
    ]
    client.app.include_router(build_reconnect_router(key=KEY))
    thread_url = f"/api/v1/agent/threads/{thread_id}"
    contexts, urls, questions, waiting = [], [], [], []

    def route(message, state, index):
        # Como has no supported production route. Its municipality is supplied by the isolated fixture.
        locations = {} if index == 0 else {"destination": CaseLocation(municipality_id=COMO_FIXTURE, confirmed=True)}
        return choose_candidate_step(
            message, state, case_locations=locations, confirmed_dates={}, confirmed_circumstances={},
            assignments=assignments, trusted_passage_ids=trusted, reviewed_labels={},
        )

    for index, case_id in enumerate(case_ids):
        posted = client.post(thread_url + "/messages", headers=owner, json={
            "client_message_id": str(uuid4()), "case_id": case_id, "language": "it",
            "text": f"Pratica sintetica {labels[index]}",
        })
        assert posted.status_code == 202, posted.text
        run_id = UUID(posted.json()["run_id"])
        context = {"thread_id": thread_id, "run_id": run_id, "principal": ALICE, "key": KEY}
        assert run_worker_step(factory, **context, execute=lambda *_: STATE).status == "running"

        def ask(message, state):
            assert message.case_context.case_id == UUID(case_id)
            assert message.case_context.document_fields == {"move_in_date": statuses[index]}
            return route(message, state, index)

        paused = run_worker_step(factory, **context, execute=ask, document_settings=settings)
        assert paused.status == "waiting_for_information"
        url = f"{thread_url}/runs/{run_id}"
        replay = client.get(url + "/events", headers=owner)
        assert replay.status_code == 200
        question = replay.json()["events"][-1]["question"]
        assert question["missing_fields"] == ["move_in_date"]
        assert ("verificato" if index == 0 else "controllare") in question["text"]
        assert all(secret not in replay.text for secret in (*document_ids, *(d.isoformat() for d in dates)))
        assert_private_error(client.get(url + "/events", headers=other_account), 404, "unavailable")
        contexts.append(context)
        urls.append(url)
        questions.append(question)
        waiting.append(client.get(url, headers=owner).json())

    assert questions[0]["question_id"] != questions[1]["question_id"]
    # Verify per-case active run binding directly; the customer task-picker endpoint is removed.
    with factory() as db:
        active_runs = db.scalars(select(AgentRunRequest).where(
            AgentRunRequest.thread_id == str(thread_id),
            AgentRunRequest.case_id.in_([str(case_id) for case_id in case_ids]),
        )).all()
    assert {run.case_id: run.id for run in active_runs} == {
        case_id: str(context["run_id"]) for case_id, context in zip(case_ids, contexts, strict=True)
    }
    assert client.get(thread_url + "/cases", headers=owner).status_code == 404
    assert client.get(thread_url + "/tasks", headers=owner).status_code == 404
    for index, sibling in (order, order[::-1]):
        sibling_before = client.get(urls[sibling] + "/events", headers=owner).json()
        reply = {
            "client_reply_id": str(uuid4()), "expected_run_revision": waiting[index]["run_revision"],
            "text": dates[index].isoformat(),
        }
        assert_private_error(client.post(
            f"{urls[index]}/questions/{questions[sibling]['question_id']}/reply", headers=owner, json=reply,
        ), 409, "stale_question")
        submitted = client.post(
            f"{urls[index]}/questions/{questions[index]['question_id']}/reply", headers=owner, json=reply,
        )
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["run_id"] == str(contexts[index]["run_id"])

        def finish(message, state):
            assert message.case_id == UUID(case_ids[index])
            assert str(message.clarification_question.question_id) == questions[index]["question_id"]
            assert message.recent_user_messages == ()
            routed = route(message, state, index)
            assert routed.next_node == "find_evidence"
            assert routed.routing_corrections.move_in_date == dates[index]
            return AnswerResult(
                explanation="Both fictional municipal passages were proposed.",
                verification_status="verified", citations=list(citations), claims=claims,
            )

        def read_scope(db, stored_thread, stored_run, stored_case, principal):
            assert (stored_thread, stored_run, stored_case, principal) == (
                thread_id, contexts[index]["run_id"], UUID(case_ids[index]), ALICE,
            )
            [event] = read_run_events(db, **contexts[index], after_seq=waiting[index]["last_event_seq"]).events
            assert event.type == "question.answered"
            return AnswerEvidenceScope(
                procedure_id=PROCEDURE, confirmed_dates={"move_in_date": date.fromisoformat(event.text)},
                case_locations={"destination": CaseLocation(municipality_id=municipalities[index], confirmed=True)},
                confirmed_circumstances={}, assignments=assignments, claim_reviews=reviews,
            )

        done = run_worker_step(
            factory, **contexts[index], execute=finish, document_settings=settings, read_evidence_scope=read_scope,
        )
        assert done.status == "completed"
        result = client.get(urls[index], headers=owner).json()["result"]
        assert [c["passage_id"] for c in result["citations"]] == [citations[index].passage_id]
        assert result["claims"] == [claims[index].model_dump(mode="json")]
        assert result["document_observations"] == [{
            "field_id": "move_in_date", "status": statuses[index], "origin": "user_document",
        }]
        assert client.get(urls[sibling] + "/events", headers=owner).json() == sibling_before
        assert_private_error(client.get(
            f"{urls[index]}/sources/{citations[sibling].passage_id}", headers=owner,
        ), 404, "unavailable")
        own_source_url = f"{urls[index]}/sources/{citations[index].passage_id}"
        own_source = client.get(own_source_url, headers=owner)
        assert own_source.status_code == 200
        assert own_source.json()["passage"]["citation"]["location_id"] == municipalities[index]
        assert_private_error(client.get(own_source_url, headers=other_account), 404, "unavailable")

    assert client.get(f"/api/v1/conversations/tasks/{milan_case}/intake", headers=owner).json()["facts"] == milan_facts
    assert client.get(f"/api/v1/conversations/tasks/{como_case}/intake", headers=owner).json()["facts"] == {}
