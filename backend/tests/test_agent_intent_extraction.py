"""Synthetic inputs and reviewed-name fixtures for the internal worker step."""

from dataclasses import replace
from functools import partial
from uuid import uuid4

import pytest

from app.agent.case_context import WorkerCaseContext
from app.agent.candidate_resolution import choose_candidate_step
from app.agent.checkpoints import AgentRunCheckpoint, CheckpointState, load_checkpoint
from app.agent.contract import SendMessage
from app.agent.intent_extraction import extract_intent, identify_intent_step
from app.agent.reconnect_router import build_reconnect_router
from app.agent.run_requests import StoredMessage, accept_message
from app.agent.threads import create_thread
from app.agent.worker import run_worker_step
from app.cases.intake_schemas import IntakeFacts
from app.knowledge.entity_matching import CatalogueName
from test_agent_run_requests import ALICE, KEY


def reviewed_name(record_id, kind, name):
    return CatalogueName(record_id, kind, name, name, "reviewed_alias", "fixture-review", approved_for_search=True)


CATALOGUE = (
    reviewed_name("municipality-milan", "municipality", "Milano"),
    reviewed_name("municipality-milan", "municipality", "Milan"),
    reviewed_name("city-authority", "authority", "Comune di Milano"),
    reviewed_name("authority-archive", "authority", "Ufficio Archivio"),
    reviewed_name("residence-change", "procedure", "cambio di residenza"),
    reviewed_name("residence-change", "procedure", "change my residence"),
    reviewed_name("residence-change", "procedure", "residence change"),
    reviewed_name("tax-record", "procedure", "update my tax record"),
    reviewed_name("tax-record", "procedure", "aggiornare la posizione TARI"),
)
MULTI_CATALOGUE = (*CATALOGUE, reviewed_name("municipality-como", "municipality", "Como"))


@pytest.mark.parametrize(("language", "text", "label"), [
    ("en", "What is proof of residence?", "request_information"),
    ("it", "Quali documenti devo preparare?", "request_information"),
    ("en", "How do I change my residence in Milan?", "find_procedure"),
    ("it", "Come comunico il mio cambio di residenza a Milano?", "find_procedure"),
    ("en", "What does this letter from the municipality mean?", "explain_notice"),
    ("it", "Cosa significa questo avviso?", "explain_notice"),
    ("en", "What do I enter in this form field?", "explain_form_field"),
    ("it", "Cosa significa ‘titolo di occupazione’ in questo modulo?", "explain_form_field"),
    ("en", "Can we pick up my saved address change?", "resume_case"),
    ("it", "Posso riprendere la mia pratica?", "resume_case"),
    ("en", "How do I change my residence and update my tax record in Milan?", "plan_multiple_tasks"),
    ("it", "Cambio di residenza e aggiornare la posizione TARI a Milano. Da dove inizio?", "plan_multiple_tasks"),
])
def test_extracts_the_six_intents_from_bilingual_messages(language, text, label):
    assert extract_intent(StoredMessage(text, language, None), catalogue_names=CATALOGUE).intent == label


@pytest.mark.parametrize(("language", "text", "label"), [
    ("en", "Can we submit the declaration online?", "find_procedure"),
    ("en", "Where should I lodge the application?", "find_procedure"),
    ("it", "Dove deposito la domanda?", "find_procedure"),
    ("it", "A quale ufficio ci rivolgiamo?", "find_procedure"),
    ("en", "Which exact limit applies in this form?", "request_information"),
    ("it", "Quale massimo vale per gli allegati?", "request_information"),
])
def test_distinguishes_filing_requests_from_requests_for_limits(language, text, label):
    result = extract_intent(StoredMessage(text, language, None), catalogue_names=CATALOGUE)
    assert result.intent == label
    assert result.procedure_candidates == ()
    if label == "find_procedure":
        assert result.missing_context == ("procedure", "procedure_location")


def test_italian_registration_address_resolves_only_with_the_reviewed_alias():
    alias = reviewed_name("residence-change", "procedure", "indirizzo all’anagrafe")
    message = StoredMessage("Dove invio la richiesta per l'indirizzo all'anagrafe?", "it", None)
    assert extract_intent(message, catalogue_names=CATALOGUE).procedure_candidates == ()
    pending = replace(alias, approved_for_search=False)
    assert extract_intent(message, catalogue_names=(*CATALOGUE, pending)).procedure_candidates == ()
    result = extract_intent(message, catalogue_names=(*CATALOGUE, alias))
    assert (result.intent, result.procedure_candidates, result.missing_context) == (
        "find_procedure", ("residence-change",), ("procedure_location",),
    )
    generic = extract_intent(
        StoredMessage("Dove invio la richiesta per il nuovo indirizzo di domicilio?", "it", None),
        catalogue_names=(*CATALOGUE, alias),
    )
    assert generic.intent == "find_procedure" and generic.procedure_candidates == ()


def test_uses_reviewed_matches_preserves_authority_mentions_and_skips_nested_place():
    unreviewed = replace(reviewed_name("unreviewed", "procedure", "tax"), approved_for_search=False)
    no_evidence = replace(reviewed_name("candidate", "authority", "Ufficio Finto"), evidence_ref="")
    text = "Cambio di residenza: Comune di Milano, Ufficio Archivio o Ufficio Finto per il tax?"
    result = extract_intent(StoredMessage(text, "it", None), catalogue_names=(*CATALOGUE, unreviewed, no_evidence))
    assert [mention.expression for mention in result.mentions] == [
        "Cambio di residenza", "Comune di Milano", "Ufficio Archivio",
    ]
    assert [mention.match.selected_id for mention in result.mentions] == [
        "residence-change", "city-authority", "authority-archive",
    ]
    assert result.procedure_candidates == ("residence-change",)
    assert result.missing_context == ("procedure_location",)


def test_ambiguous_names_stay_candidates_even_with_a_confirmed_case():
    catalogue = (
        *CATALOGUE,
        reviewed_name("other-procedure", "procedure", "residence change"),
        reviewed_name("province-milan", "province", "Milan"),
    )
    case_id = uuid4()
    context = WorkerCaseContext(case_id, IntakeFacts(destination_municipality="milano"), None, ())
    result = extract_intent(
        StoredMessage("Residence change in Milan", "en", case_id, case_context=context),
        catalogue_names=catalogue,
    )
    assert set(result.procedure_candidates) == {"residence-change", "other-procedure"}
    assert [mention.match.status for mention in result.mentions] == ["ambiguous", "ambiguous"]
    assert result.missing_context == ("procedure", "procedure_location")


@pytest.mark.parametrize(("spoken", "registered"), [
    ("ANPR", "A.N.P.R."),
    ("A.N.P.R.", "ANPR"),
    ("A N P R", "ANPR"),
])
def test_acronym_variants_use_reviewed_catalogue_without_selecting_an_authority(spoken, registered):
    acronym = replace(reviewed_name("population-register", "authority", registered), kind="official_acronym")
    unreviewed = replace(acronym, catalogue_id="unreviewed", approved_for_search=False)
    result = extract_intent(
        StoredMessage(f"Change my residence in Milan through {spoken}", "en", None),
        catalogue_names=(*CATALOGUE, acronym, unreviewed),
    )
    mention = result.mentions[-1]
    assert mention.expression.rstrip(".") == spoken.rstrip(".")
    assert mention.match.status == "needs_confirmation"
    assert mention.match.selected_id is None
    assert [candidate.catalogue_id for candidate in mention.match.candidates] == ["population-register"]


def test_reviewed_everyday_wording_keeps_residence_and_domicile_candidates_distinct():
    catalogue = (
        *CATALOGUE,
        replace(reviewed_name("residence-change", "procedure", "change my registered address"), kind="search_variant"),
        reviewed_name("fictional-domicile-record", "procedure", "domicilio"),
    )
    assert extract_intent(
        StoredMessage("How do I change my registered address in Milan?", "en", None),
        catalogue_names=catalogue,
    ).procedure_candidates == ("residence-change",)
    assert extract_intent(
        StoredMessage("Cosa significa domicilio?", "it", None), catalogue_names=catalogue,
    ).procedure_candidates == ("fictional-domicile-record",)


def test_reports_missing_information_without_assuming_a_procedure_place_or_owned_case():
    unlinked_case_id = uuid4()
    assert extract_intent(
        StoredMessage("How do I file at the Unknown Office?", "en", None), catalogue_names=CATALOGUE,
    ).missing_context == ("procedure", "procedure_location")
    assert extract_intent(
        StoredMessage("Resume case", "en", unlinked_case_id), catalogue_names=CATALOGUE,
    ).missing_context == ("case_reference",)
    assert extract_intent(
        StoredMessage("Hello", "en", None), catalogue_names=CATALOGUE,
    ).missing_context == ("intent",)

    confirmed = WorkerCaseContext(unlinked_case_id, IntakeFacts(destination_municipality="milano"), None, ())
    assert extract_intent(
        StoredMessage("Residence change in an unrecognized town", "en", unlinked_case_id, case_context=confirmed),
        catalogue_names=CATALOGUE,
    ).missing_context == ("procedure_location",)
    assert extract_intent(
        StoredMessage("Resume case", "en", unlinked_case_id, case_context=confirmed),
        catalogue_names=CATALOGUE,
    ).missing_context == ()


def test_distinguishes_a_single_workflow_from_a_request_to_plan_several_goals():
    assert extract_intent(
        StoredMessage("Da dove inizio con il cambio di residenza?", "it", None),
        catalogue_names=CATALOGUE,
    ).intent == "find_procedure"
    result = extract_intent(
        StoredMessage("Can you help me plan several tasks in Milan?", "en", None),
        catalogue_names=CATALOGUE,
    )
    assert result.intent == "plan_multiple_tasks"
    assert result.missing_context == ("procedure",)


def test_worker_saves_catalogue_ids_and_intent_at_the_next_boundary(client):
    factory = client.app.state.session_factory
    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        accepted = accept_message(
            db, thread_id=thread_id, principal=ALICE, key=KEY,
            message=SendMessage(
                client_message_id=uuid4(), language="it",
                text="Come comunico il mio cambio di residenza a Milano?",
            ),
        )
    context = {"thread_id": thread_id, "run_id": accepted.run_id, "principal": ALICE, "key": KEY}
    run_worker_step(factory, **context, execute=lambda *_: CheckpointState(next_node="identify_intent"))
    run_worker_step(factory, **context, execute=partial(identify_intent_step, catalogue_names=CATALOGUE))
    with factory.begin() as db:
        assert load_checkpoint(db, **context).state == CheckpointState(
            next_node="find_evidence", intent="find_procedure", procedure_candidates=["residence-change"],
        )


def test_checkpoint_requests_distinction_if_candidates_exceed_its_bound():
    names = tuple(reviewed_name(f"choice-{index}", "procedure", "Residence change") for index in range(11))
    state = identify_intent_step(
        StoredMessage("Residence change in Milan", "en", None), CheckpointState(next_node="identify_intent"),
        catalogue_names=(*names, *CATALOGUE),
    )
    assert state.next_node == "choose_next_step"
    assert state.procedure_candidates == []
    assert state.missing_fields == ["procedure"]


@pytest.mark.parametrize(("language", "text", "expected"), [
    ("en", "Change my residence in Milan and update my tax record in Como.", [
        (["residence-change"], ["municipality-milan"], []),
        (["tax-record"], ["municipality-como"], []),
    ]),
    ("en", "Change my residence in Milan, update my tax record in Como.", [
        (["residence-change"], ["municipality-milan"], []),
        (["tax-record"], ["municipality-como"], []),
    ]),
    ("it", "Cambio di residenza e aggiornare la posizione TARI a Como.", [
        (["residence-change"], [], ["procedure_location"]),
        (["tax-record"], ["municipality-como"], []),
    ]),
    ("en", "Change my residence at Comune di Milano; apply for a synthetic permit in Como.", [
        (["residence-change"], [], ["procedure_location"]),
        ([], ["municipality-como"], ["procedure"]),
    ]),
    ("it", "Cambio di residenza a Milano. Vorrei richiedere un permesso fittizio.", [
        (["residence-change"], ["municipality-milan"], []),
        ([], [], ["procedure", "procedure_location"]),
    ]),
    ("en", "Change my residence in Milan and change my residence in Como.", [
        (["residence-change"], ["municipality-milan"], []),
        (["residence-change"], ["municipality-como"], []),
    ]),
])
def test_groups_candidates_and_context_by_bilingual_goal(language, text, expected):
    result = extract_intent(StoredMessage(text, language, None), catalogue_names=MULTI_CATALOGUE)
    assert result.intent == "plan_multiple_tasks" and result.procedure_candidates == ()
    assert [(goal.procedure_candidates, goal.location_candidates, goal.missing_fields)
            for goal in result.goals] == expected


@pytest.mark.parametrize(("text", "missing"), [
    ("Residence change and change my residence in Milan", ()),
    ("Residence change or update my tax record in Milan?", ("procedure",)),
    ("Residence change, or update my tax record in Milan?", ("procedure",)),
    ("I want to change my residence and not update my tax record in Milan.", ("procedure_location",)),
    ("Residence change in Milan and update the address field.", ()),
])
def test_aliases_alternatives_and_steps_do_not_create_independent_goals(text, missing):
    result = extract_intent(StoredMessage(text, "en", None), catalogue_names=MULTI_CATALOGUE)
    assert result.intent == "find_procedure"
    assert result.goals == ()
    assert result.missing_context == missing


def test_conjunction_inside_reviewed_name_does_not_split_a_goal():
    reviewed = reviewed_name("synthetic-training", "procedure", "training and learning request")
    result = extract_intent(
        StoredMessage("Training and learning request in Milan; change my residence in Como", "en", None),
        catalogue_names=(*MULTI_CATALOGUE, reviewed),
    )
    assert [goal.procedure_candidates for goal in result.goals] == [["synthetic-training"], ["residence-change"]]


def test_goal_and_per_goal_candidate_bounds_fail_closed():
    many = tuple(reviewed_name(f"candidate-{i}", "procedure", "residence change") for i in range(10))
    result = extract_intent(
        StoredMessage("Residence change in Milan; update my tax record in Como", "en", None),
        catalogue_names=(*MULTI_CATALOGUE, *many),
    )
    assert result.goals[0].procedure_candidates == []
    assert result.goals[0].missing_fields == ["procedure"]
    assert result.goals[1].procedure_candidates == ["tax-record"]

    text = "; ".join(f"Apply for a synthetic permit {i}" for i in range(7))
    result = extract_intent(StoredMessage(text, "en", None), catalogue_names=MULTI_CATALOGUE)
    assert result.intent == "plan_multiple_tasks"
    assert result.goals == () and result.procedure_candidates == () and result.missing_context == ("procedure",)


@pytest.mark.parametrize(("language", "message", "preferred"), [
    ("en", "Change my residence in Milan; update my tax record in Como. Start with task 2.", 2),
    ("it", "Cambio di residenza a Milano; aggiornare la posizione TARI a Como. Iniziamo dalla pratica 1.", 1),
    ("en", "Change my residence in Milan; update my tax record in Como. Start with residence change.", 1),
    ("en", "Start with residence change; update my tax record in Como.", 1),
    ("it", "Cambio di residenza a Milano; aggiornare la posizione TARI a Como. Cominciamo dal cambio di residenza.", 1),
    ("en", "Change my residence in Milan; update my tax record in Como. Start with task 6.", None),
    ("en", "Change my residence in Milan; change my residence in Como. Start with residence change.", None),
    ("en", "Change my residence in Milan; update my tax record. Start with task 1. Start with task 2.", None),
])
def test_only_unambiguous_explicit_preferences_select_a_goal(language, message, preferred):
    stored = StoredMessage(message, language, None)
    state = identify_intent_step(stored, CheckpointState(next_node="identify_intent"), catalogue_names=MULTI_CATALOGUE)
    assert len(state.goals) == 2 and state.preferred_goal == preferred
    outcome = choose_candidate_step(
        stored, state, case_locations={}, confirmed_dates={}, confirmed_circumstances={},
        assignments=(), trusted_passage_ids=frozenset(), reviewed_labels={},
    )
    if preferred is not None:
        assert outcome.goal_selection.active_goal == preferred
        assert outcome.missing_information == state.goals[preferred - 1].missing_fields
    else:
        assert outcome.question.missing_fields == ["active_goal"]
        assert len(outcome.question.options) == 2


@pytest.mark.parametrize("disposition", ["answer", "skip"])
def test_worker_retains_goal_sets_and_replays_the_owner_choice(client, auth_headers, disposition):
    factory = client.app.state.session_factory
    text = "Change my residence in Milan; update my tax record in Como."
    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        accepted = accept_message(
            db, thread_id=thread_id, principal=ALICE, key=KEY,
            message=SendMessage(client_message_id=uuid4(), language="en", text=text),
        )
    context = {"thread_id": thread_id, "run_id": accepted.run_id, "principal": ALICE, "key": KEY}
    run_worker_step(factory, **context, execute=lambda *_: CheckpointState(next_node="identify_intent"))
    run_worker_step(factory, **context, execute=partial(identify_intent_step, catalogue_names=MULTI_CATALOGUE))
    with factory.begin() as db:
        saved = load_checkpoint(db, **context).state
        assert saved.next_node == "choose_next_step" and saved.procedure_candidates == []
        assert [goal.location_candidates for goal in saved.goals] == [["municipality-milan"], ["municipality-como"]]
        assert b"municipality-como" not in db.get(AgentRunCheckpoint, str(accepted.run_id)).ciphertext

    choose = partial(
        choose_candidate_step, case_locations={}, confirmed_dates={}, confirmed_circumstances={},
        assignments=(), trusted_passage_ids=frozenset(), reviewed_labels={
            "residence-change": "Residence change", "tax-record": "Tax record",
            "municipality-milan": "Milan", "municipality-como": "Como",
        },
    )
    run_worker_step(factory, **context, execute=choose)
    client.app.include_router(build_reconnect_router(key=KEY))
    url = f"/api/v1/agent/threads/{thread_id}/runs/{accepted.run_id}"
    owner = auth_headers("alice")
    response = client.get(url, headers=owner)
    assert response.status_code == 200 and response.headers["Cache-Control"] == "private, no-store"
    pending = response.json()
    assert pending["status"] == "waiting_for_information" and pending["goal_selection"] is None
    [asked] = client.get(url + "/events", headers=owner, params={"after_seq": pending["last_event_seq"] - 1}).json()["events"]
    question = asked["question"]
    assert question["options"] == ["1. Residence change · Milan", "2. Tax record · Como"]
    assert question["goal_selection_language"] == "en"
    reply_url = url + f"/questions/{question['question_id']}/reply"
    reply = {
        "client_reply_id": str(uuid4()), "expected_run_revision": pending["run_revision"],
        "disposition": disposition, "text": question["options"][1] if disposition == "answer" else None,
    }
    assert client.post(reply_url, headers=auth_headers("bob"), json=reply).status_code == 404
    invalid = {**reply, "disposition": "answer", "text": "3. Forged option"}
    assert client.post(reply_url, headers=owner, json=invalid).status_code == 422
    accepted_reply = client.post(reply_url, headers=owner, json=reply)
    assert accepted_reply.status_code == 200
    selected = 2 if disposition == "answer" else None
    assert accepted_reply.json()["selected_goal"] == selected
    assert client.post(reply_url, headers=owner, json=reply).json() == accepted_reply.json()
    in_progress = client.get(url, headers=owner).json()
    assert in_progress["status"] == "running"
    if selected:
        assert in_progress["goal_selection"]["active_goal"] == selected
    else:
        assert in_progress["goal_selection"] is None

    run_worker_step(factory, **context, execute=partial(choose, reviewed_labels={}))
    wire = client.get(url, headers=owner).json()
    assert wire["result"]["goals"] == [goal.model_dump() for goal in saved.goals]
    assert wire["goal_selection"] == wire["result"]["goal_selection"] == {
        "language": "en", "options": question["options"], "active_goal": selected,
    }
    assert wire["handoff"] is None and wire["result"]["citations"] == []
    assert client.get(url + "/events", headers=owner).json()["events"][-1]["result"] == wire["result"]
    assert client.get(url, headers=auth_headers("bob")).status_code == 404
