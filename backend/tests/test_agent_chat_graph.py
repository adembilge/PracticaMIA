"""Case-free LangGraph execution against a disposable approved-only source registry."""
from uuid import uuid4

from app.agent.chat_graph import build_chat_executor
from app.agent.checkpoints import CheckpointState
from app.agent.contract import AnswerResult, QuestionAnswered, SendMessage
from app.agent.run_requests import accept_message
from app.agent.source_cards import read_run_source_card
from app.agent.threads import create_thread
from app.agent.worker import RequestClarification, run_worker_step
from app.knowledge.entity_matching import CatalogueName
from app.rules.engine import JURISDICTION, PROCEDURE
from test_agent_run_requests import ALICE, KEY
from test_knowledge_search import HTML, SCOPE, _approve, _create


def _names():
    return (
        CatalogueName(
            catalogue_id=PROCEDURE, entity_type="procedure", display_name="Cambio di residenza",
            name="change my address", kind="search_variant", evidence_ref="synthetic-reviewed-alias",
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


def test_chat_graph_clarifies_location_and_resumes_without_a_case(client):
    version, digest = _create(client, html=HTML)
    _approve(client, version, digest)
    execute = build_chat_executor(client.app.state.session_factory, catalogue_names=_names())
    opening = __import__("app.agent.run_requests", fromlist=["StoredMessage"]).StoredMessage(
        text="How can I change my address?",
        language="en",
        case_id=None,
    )
    pending = execute(opening, CheckpointState(next_node="load_context"))
    assert isinstance(pending, RequestClarification)
    assert pending.question.missing_fields == ["destination"]
    assert pending.question.options == ["Milano", "Another municipality"]
    assert "case" not in pending.question.text.casefold()

    reply = QuestionAnswered.model_construct(
        event_seq=2, question_id=pending.question.question_id,
        client_reply_id=uuid4(), text="Milano", disposition="answer",
    )
    resumed = __import__("app.agent.run_requests", fromlist=["StoredMessage"]).StoredMessage(
        text=opening.text, language="en", case_id=None,
        clarification_reply=reply, clarification_question=pending.question,
    )
    answer = execute(resumed, pending.resume_state)
    assert isinstance(answer, AnswerResult)
    assert answer.verification_status == "insufficient_evidence"
    assert answer.citations and not answer.claims
    assert answer.official_channel is None


def test_chat_graph_does_not_publish_unapproved_or_missing_passages(client):
    _create(client, html=HTML)  # deliberately not approved
    execute = build_chat_executor(client.app.state.session_factory, catalogue_names=_names())
    message = __import__("app.agent.run_requests", fromlist=["StoredMessage"]).StoredMessage(
        text="How can I change my address in Milan?",
        language="en", case_id=None,
    )
    answer = execute(message, CheckpointState(next_node="load_context"))
    assert isinstance(answer, AnswerResult)
    assert answer.verification_status == "insufficient_evidence"
    assert answer.citations == []
    assert answer.claims == []
    assert answer.official_channel is None
