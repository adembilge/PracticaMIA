"""Case-free LangGraph execution against a disposable approved-only source registry."""
from uuid import uuid4

from app.agent.chat_graph import build_chat_executor
from app.agent.checkpoints import CheckpointState, submit_clarification_reply
from app.agent.contract import AnswerResult, ClarificationReply, QuestionRequested, SendMessage
from app.agent.run_events import read_run_events
from app.agent.run_requests import StoredMessage, accept_message
from app.agent.source_cards import read_run_source_card
from app.agent.threads import create_thread
from app.agent.worker import RequestClarification, run_worker_step
from app.knowledge.entity_matching import CatalogueName
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
            name="cambio di residenza", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
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


def test_case_free_message_retrieves_only_active_approved_reference_and_reconnects(client):
    version, digest = _create(client, html=HTML)
    _approve(client, version, digest)
    factory = client.app.state.session_factory
    execute = build_chat_executor(factory, catalogue_names=_names())
    message = SendMessage(
        client_message_id=uuid4(),
        text="How can I change my address in Milan?",
        language="en",
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
    assert "reference material only" in snapshot.result.explanation

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
