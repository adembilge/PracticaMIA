"""Re-evaluate corrected conversational details without editing saved intake."""

from dataclasses import replace
from datetime import date, datetime, timezone
from functools import partial
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from app.agent.candidate_resolution import choose_candidate_step
from app.agent.catalogue_evidence import refresh_corrected_evidence
from app.agent.checkpoints import CheckpointState, RoutingCorrections, load_checkpoint, submit_clarification_reply
from app.agent.contract import ClarificationReply, ClarifyingQuestion, QuestionAnswered, SendMessage
from app.agent.intent_extraction import identify_intent_step
from app.agent.reconnect_router import build_reconnect_router
from app.agent.routing_corrections import apply_routing_reply
from app.agent.run_events import read_run_events
from app.agent.run_requests import StoredMessage, accept_message
from app.agent.worker import RequestClarification, run_worker_step
from app.auth.tokens import Principal
from app.knowledge.entity_matching import CatalogueName
from app.knowledge.service_areas import CaseLocation, EffectivePeriod
from app.rules.engine import JURISDICTION, PROCEDURE
from test_agent_run_requests import KEY
from test_knowledge_search import FACTS, OTHER_HTML, _approve, _create, _search, _thread_context, create_scoped_case
from test_service_areas import TRUSTED, area


def _answer(text, fields):
    question_id = uuid4()
    return StoredMessage(
        "Original details", "en", None,
        clarification_reply=QuestionAnswered(
            schema_version=1, type="question.answered", thread_id=uuid4(), run_id=uuid4(),
            event_seq=3, occurred_at=datetime.now(timezone.utc), question_id=question_id,
            client_reply_id=uuid4(), text=text,
        ),
        clarification_question=ClarifyingQuestion(
            question_id=question_id, text="Which detail applies?", answer_shape="free_text",
            missing_fields=fields,
        ),
    )


def test_reviewed_procedure_correction_clears_old_scope_before_evaluating_the_new_candidate():
    name = CatalogueName("new-procedure", "procedure", "New procedure", "New procedure", "current_official",
                         "synthetic-name", approved_for_search=True)
    state = CheckpointState(
        next_node="choose_next_step", intent="find_procedure", procedure_candidates=["old-procedure"],
        missing_fields=["procedure"], evidence_ids=[f"{uuid4()}:0001"],
        routing_corrections=RoutingCorrections(
            procedure="old-procedure", destination="old-town", reply_event_seqs={"destination": 2},
        ),
    )
    answer = _answer("New procedure", ["procedure"])
    result = choose_candidate_step(
        answer, state, catalogue_names=(name,),
        case_locations={"destination": CaseLocation(municipality_id="old-town", confirmed=True)},
        confirmed_dates={}, confirmed_circumstances={},
        assignments=(area(procedure_id="new-procedure", unit_ids=("old-town",)),),
        trusted_passage_ids=TRUSTED, reviewed_labels={},
    )
    assert isinstance(result, RequestClarification)
    assert result.question.missing_fields == ["destination"]
    assert result.resume_state.procedure_candidates == ["new-procedure"]
    assert result.resume_state.routing_corrections == RoutingCorrections(
        procedure="new-procedure", reply_event_seqs={"procedure": 3},
    )
    assert result.resume_state.evidence_ids == []
    assert apply_routing_reply(replace(answer, clarification_question=None), state, (name,)) == state
    assert apply_routing_reply(answer, state, (replace(name, approved_for_search=False),)) == state


def test_grouped_correction_applies_only_unambiguous_requested_fields_and_asks_for_the_rest():
    state = CheckpointState(next_node="choose_next_step", procedure_candidates=["procedure-a"])
    message = _answer(
        "Filing date: 18/11/2026\nHousing arrangement: owner\nHousing arrangement: guest\nDestination: another city",
        ["filing_date", "housing_basis"],
    )
    assignment = replace(
        area(), effective_period=EffectivePeriod("filing_date", effective_from=date(2026, 4, 1)),
        required_circumstances=(("housing_basis", "owner"),),
    )
    result = choose_candidate_step(
        message, state, case_locations={"destination": CaseLocation(municipality_id="municipality-b", confirmed=True)},
        confirmed_dates={}, confirmed_circumstances={}, assignments=(assignment,),
        trusted_passage_ids=TRUSTED, reviewed_labels={},
    )
    assert isinstance(result, RequestClarification)
    assert result.question.missing_fields == ["housing_basis"]
    assert result.resume_state.routing_corrections == RoutingCorrections(
        filing_date=date(2026, 11, 18), reply_event_seqs={"filing_date": 3},
    )


def test_destination_correction_uses_a_unique_reviewed_municipality_and_drops_old_evidence():
    name = CatalogueName("new-town", "municipality", "New Town", "New Town", "current_official",
                         "synthetic-name", approved_for_search=True)
    state = CheckpointState(
        next_node="choose_next_step", procedure_candidates=["procedure-a"], evidence_ids=[f"{uuid4()}:0001"],
    )
    message = _answer("New Town", ["destination"])
    result = choose_candidate_step(
        message, state, catalogue_names=(name,),
        case_locations={"destination": CaseLocation(municipality_id="old-town", confirmed=True)},
        confirmed_dates={}, confirmed_circumstances={},
        assignments=(area(unit_ids=("new-town",)),), trusted_passage_ids=TRUSTED, reviewed_labels={},
    )
    assert result.next_node == "find_evidence"
    assert result.routing_corrections.destination == "new-town"
    assert result.evidence_ids == []
    other = replace(name, catalogue_id="another-town")
    assert apply_routing_reply(message, state, (name, other)) == state


@pytest.mark.parametrize(("language", "text", "ambiguous"), [
    ("en", "The destination is the municipality of Milan.", "The destination is Milan or Como."),
    ("it", "Il Comune di destinazione è Milano.", "Il Comune di destinazione è Milano?"),
])
def test_destination_sentence_uses_only_the_requested_field_and_a_unique_reviewed_name(language, text, ambiguous):
    name = "Milan" if language == "en" else "Milano"
    catalogue = (CatalogueName(
        JURISDICTION, "municipality", "Milano", name, "reviewed_alias", "synthetic-name", approved_for_search=True,
    ),)
    state = CheckpointState(next_node="choose_next_step")
    reply = replace(_answer(text, ["destination"]), language=language)
    assert apply_routing_reply(reply, state, catalogue).routing_corrections == RoutingCorrections(
        destination=JURISDICTION, reply_event_seqs={"destination": 3},
    )
    assert apply_routing_reply(replace(_answer(ambiguous, ["destination"]), language=language), state, catalogue) == state
    assert apply_routing_reply(replace(_answer(text, ["activity_location"]), language=language), state, catalogue) == state
    namesake = replace(catalogue[0], catalogue_id="other-municipality")
    assert apply_routing_reply(reply, state, (*catalogue, namesake)) == state


@pytest.mark.parametrize("saved_state", ["draft", "confirmed", "archived"])
@pytest.mark.parametrize(("language", "opening", "name", "reply", "confirm_label"), [
    ("en", "Can we finish the address change I saved?", "Milan", "The destination is the municipality of Milan.",
     "Confirm saved case details"),
    ("it", "Possiamo finire il cambio di residenza che ho salvato?", "Milano", "Il Comune di destinazione è Milano.",
     "Conferma i dati della pratica"),
])
def test_reopened_destination_question_rechecks_saved_intake_before_retrieving(
    client, auth_headers, monkeypatch, saved_state, language, opening, name, reply, confirm_label,
):
    owner = auth_headers("bob")
    case_id = UUID(create_scoped_case(client, owner))
    intake_url = f"/api/v1/cases/{case_id}/intake"
    draft = {key: value for key, value in FACTS.items() if key != "destination_municipality"}
    assert client.put(intake_url, headers=owner, json={"facts": draft}).status_code == 200

    version, digest = _create(client)
    _approve(client, version, digest)
    scope = _thread_context(client, case_id, "bob")
    factory = client.app.state.session_factory
    client.app.include_router(build_reconnect_router(key=KEY))
    thread_url = f"/api/v1/agent/threads/{scope['thread_id']}"
    sent = client.post(thread_url + "/messages", headers=owner, json={
        "client_message_id": str(uuid4()), "case_id": str(case_id), "text": opening, "language": language,
    })
    assert sent.status_code == 202
    run_id = UUID(sent.json()["run_id"])
    context = {"thread_id": scope["thread_id"], "run_id": run_id, "principal": scope["principal"], "key": KEY}
    catalogue = (
        CatalogueName(JURISDICTION, "municipality", "Milano", name, "reviewed_alias", "synthetic-name",
                      approved_for_search=True),
        CatalogueName(PROCEDURE, "procedure", "Cambio di residenza",
                      "address change" if language == "en" else "cambio di residenza",
                      "reviewed_alias", "synthetic-name", approved_for_search=True),
    )
    choose = partial(
        choose_candidate_step, catalogue_names=catalogue,
        case_locations={}, confirmed_dates={}, confirmed_circumstances={},
        assignments=(area(procedure_id=PROCEDURE, unit_ids=(JURISDICTION,)),),
        trusted_passage_ids=TRUSTED, reviewed_labels={},
    )
    run_worker_step(factory, **context, execute=lambda *_: CheckpointState(next_node="identify_intent"))
    run_worker_step(factory, **context, execute=partial(identify_intent_step, catalogue_names=catalogue))
    paused = run_worker_step(factory, **context, execute=choose)
    assert paused.status == "waiting_for_information"
    run_url = f"{thread_url}/runs/{run_id}"
    snapshot = client.get(run_url, headers=owner).json()
    assert snapshot["run_revision"] == paused.run_revision
    page = client.get(run_url + "/events", headers=owner, params={"after_seq": paused.last_event_seq - 1})
    [event] = page.json()["events"]
    assert event["type"] == "question.requested" and event["question"]["missing_fields"] == ["destination"]
    assert client.post(run_url + "/questions/" + event["question"]["question_id"] + "/reply",
                       headers=owner, json={
                           "client_reply_id": str(uuid4()), "expected_run_revision": paused.run_revision,
                           "text": reply,
                       }).status_code == 200

    restarted = sessionmaker(bind=factory.kw["bind"])
    assert run_worker_step(restarted, **context, execute=choose).status == "running"
    with restarted() as db:
        state = load_checkpoint(db, **context).state
        assert state.routing_corrections.reply_event_seqs == {"destination": paused.run_revision}
        assert state.routing_corrections.destination == JURISDICTION
        assert state.evidence_ids == []
    if saved_state != "draft":
        assert client.put(intake_url, headers=owner, json={"facts": FACTS, "confirm": True}).status_code == 200
    if saved_state == "archived":
        archive_url = f"/api/v1/cases/{case_id}/archive"
        assert client.patch(archive_url, headers=owner, json={"archived": True}).status_code == 200
    if saved_state != "confirmed":
        monkeypatch.setattr(
            "app.agent.catalogue_evidence.search_approved_passages",
            lambda *_args, **_kwargs: pytest.fail("draft or archived intake must not be searched"),
        )
    saved = client.get(intake_url, headers=owner).json()
    result = run_worker_step(restarted, **context, execute=lambda *_: pytest.fail("expected the corrected scope adapter"))
    if saved_state == "confirmed":
        assert result.status == "running"
        with restarted() as db:
            next_state = load_checkpoint(db, **context).state
            assert next_state.next_node == "verify_and_respond"
            assert next_state.evidence_ids and all(item.startswith(version + ":") for item in next_state.evidence_ids)
    else:
        assert result.status == "completed"
        assert result.result.verification_status == "insufficient_evidence"
        assert result.result.official_channel is None and not result.result.citations
        if saved_state == "draft":
            assert result.result.missing_information == ["intake_confirmation"]
            assert result.result.next_action.label == confirm_label
    assert client.get(intake_url, headers=owner).json() == saved


@pytest.mark.parametrize("correction", [
    RoutingCorrections(destination="outside-milan"),
    RoutingCorrections(housing_basis="owner"),
])
def test_corrected_scope_cannot_reuse_the_previous_cases_milan_evidence(client, monkeypatch, correction):
    monkeypatch.setattr(
        "app.agent.catalogue_evidence.find_catalogue_evidence",
        lambda *args, **kwargs: pytest.fail("old scope must not be searched"),
    )
    state = CheckpointState(next_node="find_evidence", procedure_candidates=[PROCEDURE], routing_corrections=correction)
    with client.app.state.session_factory() as db:
        result = refresh_corrected_evidence(
            db, state=state, thread_id=uuid4(), run_id=uuid4(), case_id=uuid4(), principal=Principal("alice"),
            query="residenza", language="en",
        )
    assert result.verification_status == "insufficient_evidence"
    assert result.citations == []


@pytest.mark.parametrize("approve_replacement", [True, False])
def test_corrected_date_rechecks_routing_and_fresh_evidence_across_worker_restart(
    client, auth_headers, approve_replacement,
):
    owner = auth_headers("bob")
    case_id = UUID(create_scoped_case(client, owner))
    intake_url = f"/api/v1/cases/{case_id}/intake"
    facts = FACTS | {"move_in_date": "2026-03-31"}
    assert client.put(intake_url, headers=owner, json={"facts": facts, "confirm": True}).status_code == 200
    old_version, old_digest = _create(client)
    _approve(client, old_version, old_digest)
    old_citation = _search(client, owner, limit=1).json()["evidence"][0]["citation_id"]

    scope = _thread_context(client, case_id, "bob")
    factory = client.app.state.session_factory
    context = {"thread_id": scope["thread_id"], "principal": scope["principal"], "key": KEY}
    with factory.begin() as db:
        accepted = accept_message(db, **context, message=SendMessage(
            client_message_id=uuid4(), text="residenza\nMove-in date: 2026-04-02",
            language="en", case_id=case_id,
        ))
    context["run_id"] = accepted.run_id
    initial = CheckpointState(next_node="choose_next_step", procedure_candidates=[PROCEDURE], evidence_ids=[old_citation])
    run_worker_step(factory, **context, execute=lambda *_: initial)
    step = partial(
        choose_candidate_step, case_locations={}, confirmed_dates={}, confirmed_circumstances={},
        assignments=(replace(
            area(procedure_id=PROCEDURE, unit_ids=(JURISDICTION,)),
            effective_period=EffectivePeriod("move_in_date", effective_from=date(2026, 4, 1)),
        ),),
        trusted_passage_ids=TRUSTED, reviewed_labels={},
    )
    paused = run_worker_step(factory, **context, execute=step)
    assert paused.status == "waiting_for_information"
    with factory.begin() as db:
        [requested] = read_run_events(db, **context, after_seq=paused.last_event_seq - 1).events
        assert requested.question.missing_fields == ["move_in_date"]
        submit_clarification_reply(db, **context, question_id=requested.question.question_id, reply=ClarificationReply(
            client_reply_id=uuid4(), expected_run_revision=paused.run_revision, text="02/04/2026",
        ))

    replacement, digest = _create(client, html=OTHER_HTML.replace(b"nuovo contenuto", b"indicazioni sulla residenza"))
    if approve_replacement:
        _approve(client, replacement, digest)
    restarted = sessionmaker(bind=factory.kw["bind"])
    assert run_worker_step(restarted, **context, execute=step).status == "running"
    with restarted.begin() as db:
        refreshed = load_checkpoint(db, **context).state
        assert refreshed.next_node == "find_evidence"
        assert refreshed.evidence_ids == []
        assert refreshed.routing_corrections.move_in_date == date(2026, 4, 2)

    result = run_worker_step(restarted, **context, execute=lambda *_: pytest.fail("use the approved evidence adapter"))
    if approve_replacement:
        assert result.status == "running"
        with restarted.begin() as db:
            state = load_checkpoint(db, **context).state
        assert state.next_node == "verify_and_respond"
        assert state.routing_corrections.reply_event_seqs == {"move_in_date": paused.run_revision}
        assert state.evidence_ids and all(citation.startswith(replacement + ":") for citation in state.evidence_ids)
    else:
        assert result.status == "completed"
        assert result.result.verification_status == "insufficient_evidence"
        assert result.result.citations == []
    assert client.get(intake_url, headers=owner).json()["facts"]["move_in_date"] == "2026-03-31"
