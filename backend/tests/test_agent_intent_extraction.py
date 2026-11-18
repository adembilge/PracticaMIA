"""Synthetic inputs and reviewed-name fixtures for the internal worker step."""

from dataclasses import replace
from functools import partial
from uuid import uuid4

import pytest

from app.agent.case_context import WorkerCaseContext
from app.agent.checkpoints import CheckpointState, load_checkpoint
from app.agent.contract import SendMessage
from app.agent.intent_extraction import extract_intent, identify_intent_step
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
