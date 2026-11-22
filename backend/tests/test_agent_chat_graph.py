"""Case-free LangGraph execution against a disposable approved-only source registry."""
from uuid import uuid4
import json

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.agent.chat_graph import build_chat_executor
from app.agent.checkpoints import CheckpointState, submit_clarification_reply
from app.agent.contract import AnswerResult, ClarificationReply, QuestionRequested, SendMessage
from app.agent.run_events import read_run_events
from app.agent.run_requests import StoredMessage, accept_message
from app.agent.source_cards import read_run_source_card
from app.agent.threads import create_thread
from app.agent.worker import RequestClarification, run_worker_step
from app.config import Settings
from app.knowledge.entity_matching import CatalogueName
from app.knowledge.search import search_approved_passages
from app.rules.engine import JURISDICTION, PROCEDURE
from test_agent_run_requests import ALICE, KEY
from test_knowledge_search import HTML, _approve, _create


def _names():
    return (
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="change my address", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="address change", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="cambio di indirizzo", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="file the residence change", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="cambio di residenza", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="cambiare la residenza", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="register a new address", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="register my new address", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="comunicare il nuovo indirizzo", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="registrare il nuovo indirizzo", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="update my registered address", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="change my registered residence", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="transfer my residence", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="register my residence", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="trasferire la residenza", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="spostare la residenza", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="fare il cambio di residenza", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=JURISDICTION, entity_type="municipality", display_name="Milano",
            name="Milan", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
        CatalogueName(
            catalogue_id=JURISDICTION, entity_type="municipality", display_name="Milano",
            name="Milano", kind="current_official", evidence_ref="synthetic-reviewed-alias",
            approved_for_search=True,
        ),
    )


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("How can I change my address in Milan?", "en"),
        ("I need to register a new address in Milan.", "en"),
        ("Devo comunicare il nuovo indirizzo a Milano.", "it"),
        ("Devo registrare il nuovo indirizzo a Milano.", "it"),
        ("I need to update my registered address in Milan.", "en"),
        ("I want to change my registered residence in Milan.", "en"),
        ("I need to transfer my residence to Milan.", "en"),
        ("I need to register my residence in Milan.", "en"),
        ("Devo trasferire la residenza a Milano.", "it"),
        ("Voglio spostare la residenza a Milano.", "it"),
        ("Devo fare il cambio di residenza a Milano.", "it"),
    ],
)
def test_case_free_natural_address_phrases_retrieve_only_approved_references(client, text, language):
    version, digest = _create(client, html=HTML)
    _approve(client, version, digest)
    factory = client.app.state.session_factory
    execute = build_chat_executor(factory, catalogue_names=_names())
    message = SendMessage(
        client_message_id=uuid4(),
        text=text,
        language=language,
    )
    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        accepted = accept_message(db, thread_id=thread_id, principal=ALICE, message=message, key=KEY)
        assert accepted.outcome == "accepted"

    snapshot = run_worker_step(
        factory, thread_id=thread_id, run_id=accepted.run_id, principal=ALICE, key=KEY,
        execute=execute,
    )
    assert snapshot.status == "completed"
    assert snapshot.result.verification_status == "insufficient_evidence"
    assert snapshot.result.citations
    assert snapshot.result.claims == []
    assert snapshot.result.official_channel is None
    expected_phrase = "solo riferimenti" if language == "it" else "reference material only"
    assert expected_phrase in snapshot.result.explanation

    citation = snapshot.result.citations[0]
    with factory() as db:
        card = read_run_source_card(
            db, thread_id=thread_id, run_id=accepted.run_id,
            citation_id=citation.citation_id, principal=ALICE, key=KEY,
        )
    assert card is not None
    assert card.passage.citation == citation
    assert "residenza" in card.passage.content.casefold()


def test_case_free_worker_resumes_a_real_clarification_reply(client):
    version, digest = _create(client, html=HTML)
    _approve(client, version, digest)
    factory = client.app.state.session_factory
    execute = build_chat_executor(factory, catalogue_names=_names())
    message = SendMessage(
        client_message_id=uuid4(), text="How can I change my address?", language="en",
    )
    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        accepted = accept_message(db, thread_id=thread_id, principal=ALICE, message=message, key=KEY)
    context = {
        "thread_id": thread_id, "run_id": accepted.run_id, "principal": ALICE, "key": KEY,
    }

    paused = run_worker_step(factory, **context, execute=execute)
    assert paused.status == "waiting_for_information"
    with factory() as db:
        events = read_run_events(db, **context, after_seq=0).events
    question = next(event.question for event in events if isinstance(event, QuestionRequested))
    assert question.missing_fields == ["destination"]

    reply = ClarificationReply(
        client_reply_id=uuid4(), expected_run_revision=paused.run_revision, text="Milano",
    )
    with factory.begin() as db:
        submitted = submit_clarification_reply(
            db, **context, question_id=question.question_id, reply=reply,
        )
    assert submitted.text == "Milano"

    completed = run_worker_step(factory, **context, execute=execute)
    assert completed.status == "completed"
    assert completed.result.verification_status == "insufficient_evidence"
    assert completed.result.citations
    assert completed.result.claims == []
    assert completed.result.official_channel is None


def test_chat_graph_does_not_publish_unapproved_or_missing_passages(client):
    _create(client, html=HTML)  # deliberately not approved
    execute = build_chat_executor(client.app.state.session_factory, catalogue_names=_names())
    message = StoredMessage(
        text="How can I change my address in Milan?",
        language="en", case_id=None,
    )
    answer = execute(message, CheckpointState(next_node="load_context"))
    assert isinstance(answer, AnswerResult)
    assert answer.verification_status == "insufficient_evidence"
    assert answer.citations == []
    assert answer.claims == []
    assert answer.official_channel is None



def test_case_free_italian_message_retrieves_only_active_approved_reference(client):
    version, digest = _create(client, html=HTML)
    _approve(client, version, digest)
    factory = client.app.state.session_factory
    execute = build_chat_executor(factory, catalogue_names=_names())
    message = SendMessage(
        client_message_id=uuid4(),
        text="Come posso cambiare la residenza a Milano?",
        language="it",
    )
    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        accepted = accept_message(db, thread_id=thread_id, principal=ALICE, message=message, key=KEY)
        assert accepted.outcome == "accepted"

    snapshot = run_worker_step(
        factory, thread_id=thread_id, run_id=accepted.run_id, principal=ALICE, key=KEY,
        execute=execute,
    )
    while snapshot.status in {"queued", "running"}:
        snapshot = run_worker_step(
            factory, thread_id=thread_id, run_id=accepted.run_id, principal=ALICE, key=KEY,
            execute=execute,
        )

    assert snapshot.status == "completed"
    assert snapshot.result.verification_status == "insufficient_evidence"
    assert snapshot.result.citations
    assert snapshot.result.claims == []
    assert snapshot.result.official_channel is None
    assert "solo riferimenti" in snapshot.result.explanation


def test_case_free_graph_abstains_when_user_selects_another_municipality(client):
    version, digest = _create(client, html=HTML)
    _approve(client, version, digest)
    factory = client.app.state.session_factory
    execute = build_chat_executor(factory, catalogue_names=_names())
    message = SendMessage(
        client_message_id=uuid4(), text="How can I change my address?", language="en",
    )
    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        accepted = accept_message(db, thread_id=thread_id, principal=ALICE, message=message, key=KEY)
    context = {
        "thread_id": thread_id, "run_id": accepted.run_id, "principal": ALICE, "key": KEY,
    }

    paused = run_worker_step(factory, **context, execute=execute)
    assert paused.status == "waiting_for_information"
    with factory() as db:
        events = read_run_events(db, **context, after_seq=0).events
    question = next(event.question for event in events if isinstance(event, QuestionRequested))
    assert question.options == ["Milano", "Another municipality"]

    reply = ClarificationReply(
        client_reply_id=uuid4(), expected_run_revision=paused.run_revision, text="Another municipality",
    )
    with factory.begin() as db:
        submit_clarification_reply(
            db, **context, question_id=question.question_id, reply=reply,
        )

    completed = run_worker_step(factory, **context, execute=execute)
    assert completed.status == "completed"
    assert completed.result.verification_status == "unsupported"
    assert completed.result.citations == []
    assert completed.result.claims == []
    assert completed.result.official_channel is None

def test_case_free_model_selects_only_approved_references_without_user_message(client):
    version, digest = _create(client, html=HTML)
    _approve(client, version, digest)
    factory = client.app.state.session_factory
    with factory() as db:
        candidates = search_approved_passages(
            db, query="residenza", jurisdiction=JURISDICTION,
            procedure_id=PROCEDURE, language="it", limit=5,
        )
    assert candidates
    selected_id = candidates[0].passage_id
    model_inputs = []

    def model(prompt):
        model_inputs.append(prompt.to_string())
        return AIMessage(content=json.dumps([selected_id]))

    settings = Settings(
        deployment_environment="preview",
        deployment_git_branch="preview/auth-review-isolated",
        enable_case_free_agent_model=True,
        assistant_model_privacy_approved=True,
        assistant_chat_model="synthetic-model",
        assistant_llm_provider="openai",
        assistant_openai_api_key="test-key-not-used",
        assistant_usage_hash_key="unit-test-only-case-free-usage-secret-32-bytes",
        assistant_daily_limit=2,
    )
    execute = build_chat_executor(
        factory, catalogue_names=_names(), settings=settings,
        model_factory=lambda: RunnableLambda(model),
    )
    message = SendMessage(
        client_message_id=uuid4(),
        text="How can I change my address in Milan? My email is alice@example.test",
        language="en",
    )
    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        accepted = accept_message(db, thread_id=thread_id, principal=ALICE, message=message, key=KEY)
    context = {
        "thread_id": thread_id, "run_id": accepted.run_id, "principal": ALICE, "key": KEY,
    }

    snapshot = run_worker_step(factory, **context, execute=execute)
    for _ in range(4):
        if snapshot.status not in {"queued", "running"}:
            break
        snapshot = run_worker_step(factory, **context, execute=execute)

    assert snapshot.status == "completed"
    assert [item.citation_id for item in snapshot.result.citations] == [selected_id]
    assert snapshot.result.verification_status == "insufficient_evidence"
    assert snapshot.result.claims == []
    assert snapshot.result.official_channel is None
    assert len(model_inputs) == 1
    assert "residenza" in model_inputs[0]
    assert "alice@example.test" not in model_inputs[0]
    assert "How can I change my address" not in model_inputs[0]

def test_case_free_model_is_not_invoked_without_approved_evidence(client):
    _create(client, html=HTML)  # deliberately not approved
    factory = client.app.state.session_factory
    factory_calls = []
    settings = Settings(
        deployment_environment="preview",
        deployment_git_branch="preview/auth-review-isolated",
        enable_case_free_agent_model=True,
        assistant_model_privacy_approved=True,
        assistant_chat_model="synthetic-model",
        assistant_llm_provider="openai",
        assistant_openai_api_key="test-key-not-used",
        assistant_usage_hash_key="unit-test-only-case-free-usage-secret-32-bytes",
        assistant_daily_limit=2,
    )
    execute = build_chat_executor(
        factory, catalogue_names=_names(), settings=settings,
        model_factory=lambda: factory_calls.append("constructed") or RunnableLambda(
            lambda _prompt: AIMessage(content="[]")
        ),
    )
    message = SendMessage(
        client_message_id=uuid4(),
        text="How can I change my address in Milan?",
        language="en",
    )
    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        accepted = accept_message(db, thread_id=thread_id, principal=ALICE, message=message, key=KEY)
    snapshot = run_worker_step(
        factory, thread_id=thread_id, run_id=accepted.run_id, principal=ALICE,
        key=KEY, execute=execute,
    )

    assert snapshot.status == "completed"
    assert snapshot.result.citations == []
    assert snapshot.result.claims == []
    assert snapshot.result.official_channel is None
    assert factory_calls == []

