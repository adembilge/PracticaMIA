"""Exercise durable worker recovery using synthetic, read-only steps."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from app.agent.case_context import read_worker_case_context
from app.agent.checkpoints import (
    AgentRunCheckpoint, CheckpointConflict, CheckpointState, load_checkpoint, stop_run, submit_clarification_reply,
)
from app.agent.contract import AnswerResult, ClarificationReply, ClarifyingQuestion, SendMessage
from app.agent.run_events import append_run_event, read_run_events, read_run_snapshot
from app.agent.run_requests import AgentRunRequest, RecentUserMessage, accept_message
from app.agent.threads import create_thread, link_case_to_thread
from app.agent.worker import RequestClarification, run_worker_step
from app.auth.tokens import Principal
from app.cases import checklist_service as checklist
from app.cases.intake_schemas import IntakeFacts
from test_agent_run_events import queued_run  # noqa: F401 - shared synthetic run fixture
from test_agent_run_requests import ALICE, KEY
from test_case_checklist import FACTS, confirmed_intake, create_case
from test_case_workflow import evidence


def test_replacement_worker_skips_completed_node_after_interruption(queued_run):
    factory, context, _, _ = queued_run
    calls = []

    def first(message, state):
        assert message.text
        assert message.case_context is None
        calls.append(state.next_node)
        return CheckpointState(next_node="identify_intent")

    assert run_worker_step(factory, **context, execute=first).last_event_seq == 2

    def interrupted(_message, state):
        calls.append(state.next_node)
        raise RuntimeError("synthetic interruption before checkpoint commit")

    with pytest.raises(RuntimeError, match="synthetic interruption"):
        run_worker_step(factory, **context, execute=interrupted)

    replacement = sessionmaker(bind=factory.kw["bind"])

    def resumed(_message, state):
        calls.append(state.next_node)
        return CheckpointState(next_node="verify_and_respond")

    assert run_worker_step(replacement, **context, execute=resumed).last_event_seq == 3

    def finish(_message, state):
        calls.append(state.next_node)
        return AnswerResult(
            explanation="There is no applicable evidence in this fixture.",
            verification_status="insufficient_evidence",
        )

    snapshot = run_worker_step(replacement, **context, execute=finish)
    assert snapshot.status == "completed"
    assert snapshot.result.verification_status == "insufficient_evidence"
    assert calls == ["load_context", "identify_intent", "identify_intent", "verify_and_respond"]
    assert run_worker_step(replacement, **context, execute=lambda *_: pytest.fail("already done")) == snapshot
    with replacement.begin() as db:
        assert read_run_events(db, **context, after_seq=2).events[-1].type == "answer.completed"
        assert db.get(AgentRunCheckpoint, str(context["run_id"])) is None


def test_stale_worker_cannot_commit_its_terminal_answer(queued_run):
    factory, context, _, _ = queued_run

    def stale(_message, _state):
        result = run_worker_step(factory, **context, execute=lambda *_: CheckpointState(
            next_node="find_evidence",
        ))
        assert result.last_event_seq == 2
        return AnswerResult(explanation="Stale result", verification_status="unsupported")

    with pytest.raises(CheckpointConflict, match="watermark"):
        run_worker_step(factory, **context, execute=stale)
    with factory.begin() as db:
        saved = load_checkpoint(db, **context)
        assert saved.state.next_node == "find_evidence"
        assert read_run_snapshot(db, **context).status == "running"
        assert all(item.type != "answer.completed" for item in read_run_events(db, **context, after_seq=0).events)


def test_worker_does_not_execute_foreign_or_waiting_run(queued_run):
    factory, context, _, event = queued_run

    def must_not_execute(*_):
        pytest.fail("the callback should not be called")

    assert run_worker_step(
        factory, **{**context, "principal": Principal("other-owner")}, execute=must_not_execute,
    ) is None

    run_worker_step(factory, **context, execute=lambda *_: CheckpointState(next_node="identify_intent"))
    question = event("question.requested", 3, question={
        "question_id": uuid4(), "text": "Which city?", "answer_shape": "free_text",
        "missing_fields": ["jurisdiction"],
    })
    with factory.begin() as db:
        append_run_event(db, principal=context["principal"], key=context["key"], event=question)
    assert run_worker_step(factory, **context, execute=must_not_execute).status == "waiting_for_information"


def _enqueue(factory, thread_id, text, *, case_id=None, language="en"):
    context = {"thread_id": thread_id, "principal": ALICE, "key": KEY}
    with factory.begin() as db:
        accepted = accept_message(
            db, **context,
            message=SendMessage(client_message_id=uuid4(), text=text, language=language, case_id=case_id),
        )
        assert accepted.outcome == "accepted"
    return {**context, "run_id": accepted.run_id}


def _finish(*_):
    return AnswerResult(explanation="Synthetic result", verification_status="insufficient_evidence")


def test_topic_change_keeps_the_original_question_open_and_fences_old_thread_context(client, auth_headers):
    factory = client.app.state.session_factory
    case_id = UUID(client.post("/api/v1/conversations/tasks", headers=auth_headers(), json={}).json()["id"])
    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        assert link_case_to_thread(db, thread_id=thread_id, case_id=case_id, principal=ALICE)

    old = _enqueue(factory, thread_id, "Previous unlinked topic")
    run_worker_step(factory, **old, execute=_finish)
    current = _enqueue(factory, thread_id, "Linked topic", case_id=case_id, language="it")
    question = ClarifyingQuestion(
        question_id=uuid4(), text="Quale comune?", answer_shape="free_text", missing_fields=["destination"],
    )
    paused = run_worker_step(factory, **current, execute=lambda *_: RequestClarification(
        question, CheckpointState(next_node="choose_next_step"),
    ))
    reply = ClarificationReply(
        client_reply_id=uuid4(), expected_run_revision=paused.run_revision, disposition="change_topic",
    )
    with factory.begin() as db:
        saved = submit_clarification_reply(db, **current, question_id=question.question_id, reply=reply)

    finished = run_worker_step(factory, **current, execute=lambda *_: pytest.fail("old topic must not execute"))
    assert finished.status == "completed"
    assert finished.result.next_action.operation == "start_new_topic"
    assert finished.result.missing_information == ["destination"]
    assert finished.result.verification_status == "insufficient_evidence"
    assert finished.result.explanation.startswith("La domanda precedente")
    with factory.begin() as db:
        assert submit_clarification_reply(db, **current, question_id=question.question_id, reply=reply) == saved
        answered, terminal = read_run_events(db, **current, after_seq=paused.last_event_seq).events
        assert answered == saved
        assert terminal.type == "answer.completed"

    new = _enqueue(factory, thread_id, "New unlinked topic")

    def clear_context(message, _):
        assert not message.recent_user_messages
        assert message.case_context is None
        assert message.clarification_reply is None
        return _finish()

    run_worker_step(factory, **new, execute=clear_context)
    followup = _enqueue(factory, thread_id, "New-topic follow-up")

    def fresh_history(message, _):
        assert message.recent_user_messages == (RecentUserMessage("New unlinked topic", "en"),)
        return _finish()

    run_worker_step(factory, **followup, execute=fresh_history)


def test_worker_history_is_bounded_to_prior_completed_messages_for_this_thread_and_case(client, auth_headers):
    case_a = UUID(client.post("/api/v1/conversations/tasks", headers=auth_headers(), json={}).json()["id"])
    case_b = UUID(client.post("/api/v1/conversations/tasks", headers=auth_headers(), json={}).json()["id"])
    factory = client.app.state.session_factory
    with factory.begin() as db:
        main_thread = create_thread(db, principal=ALICE)
        other_thread = create_thread(db, principal=ALICE)
        for thread_id, case_id in ((main_thread, case_a), (main_thread, case_b), (other_thread, case_a)):
            assert link_case_to_thread(db, thread_id=thread_id, case_id=case_id, principal=ALICE)

    for index in range(4):
        context = _enqueue(factory, main_thread, f"Case A fixture {index}", case_id=case_a, language="it")
        assert run_worker_step(factory, **context, execute=_finish).status == "completed"
    for (thread_id, case_id, text) in (
        (main_thread, case_b, "Other case fixture"),
        (other_thread, case_a, "Other thread fixture"),
        (main_thread, None, "Unlinked fixture"),
    ):
        context = _enqueue(factory, thread_id, text, case_id=case_id)
        assert run_worker_step(factory, **context, execute=_finish).status == "completed"

    stopped = _enqueue(factory, main_thread, "Stopped fixture", case_id=case_a)
    with factory.begin() as db:
        assert stop_run(db, **stopped, expected_run_revision=1).status == "stopped"

    active = _enqueue(factory, main_thread, "Current fixture", case_id=case_a)
    expected = tuple(RecentUserMessage(f"Case A fixture {index}", "it") for index in range(1, 4))

    def advance(message, state):
        assert message.text == "Current fixture"
        assert message.recent_user_messages == expected
        if state.next_node == "load_context":
            return CheckpointState(next_node="find_evidence")
        return _finish()

    assert run_worker_step(factory, **active, execute=advance).status == "running"
    replacement = sessionmaker(bind=factory.kw["bind"])
    assert run_worker_step(replacement, **active, execute=advance).status == "completed"

    def verify_unlinked(message, _state):
        assert message.recent_user_messages == (RecentUserMessage("Unlinked fixture", "en"),)
        return _finish()

    unlinked = _enqueue(factory, main_thread, "Current unlinked fixture")
    assert run_worker_step(factory, **unlinked, execute=verify_unlinked).status == "completed"


def test_unreadable_historical_ciphertext_does_not_block_the_current_run(queued_run):
    factory, context, _, _ = queued_run
    assert run_worker_step(factory, **context, execute=_finish).status == "completed"
    older_valid = _enqueue(factory, context["thread_id"], "Valid fixture")
    assert run_worker_step(factory, **older_valid, execute=_finish).status == "completed"
    with factory.begin() as db:
        prior = db.get(AgentRunRequest, str(context["run_id"]))
        prior.message_ciphertext = b"\x01" * len(prior.message_ciphertext)

    def verify(message, _state):
        assert message.recent_user_messages == (RecentUserMessage("Valid fixture", "en"),)
        return _finish()

    current = _enqueue(factory, context["thread_id"], "Current fixture")
    assert run_worker_step(factory, **current, execute=verify).status == "completed"


def test_worker_reads_current_confirmed_facts_and_open_review_actions(client, auth_headers, monkeypatch):
    current_review = {"date": "2026-11-08", "revoked": False}

    def resolve(_db, *, citation_id, **_):
        if current_review["revoked"]:
            return None
        return evidence(citation_id, current_review["date"])

    monkeypatch.setattr(checklist, "resolve_approved_passage", resolve)
    owner = auth_headers()
    case_id = UUID(create_case(client, owner))
    path = f"/api/v1/conversations/tasks/{case_id}"
    assert client.put(f"/api/v1/conversations/tasks/{case_id}/intake", headers=owner, json={"facts": FACTS, "confirm": False}).status_code == 200
    factory = client.app.state.session_factory
    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        assert link_case_to_thread(db, thread_id=thread_id, case_id=case_id, principal=ALICE)
    context = _enqueue(factory, thread_id, "Review the current case", case_id=case_id)

    def check_draft(message, _state):
        case = message.case_context
        assert case.case_id == case_id
        assert case.user_confirmed_facts is None
        assert case.next_action == "confirm_intake"
        assert case.open_review_action_ids == ()
        return CheckpointState(next_node="find_evidence")

    assert run_worker_step(factory, **context, execute=check_draft).status == "running"
    confirmed_intake(client, owner, str(case_id), facts={**FACTS, "move_in_date": "2026-11-05"})
    workflow = client.get(path + "/workflow", headers=owner).json()
    review_ids = tuple(item["id"] for item in workflow["checklist"]["items"])
    assert len(review_ids) == 5
    assert client.patch(path + "/workflow/checklist", headers=owner, json={
        "item_id": review_ids[0], "reviewed": True, "fingerprint": workflow["checklist"]["fingerprint"],
    }).status_code == 200

    def check_confirmed(message, _state):
        case = message.case_context
        assert case.user_confirmed_facts == IntakeFacts(**FACTS, move_in_date="2026-11-05")
        assert case.next_action == "review_checklist"
        assert case.open_review_action_ids == review_ids[1:]
        case.user_confirmed_facts.housing_basis = "guest"
        return CheckpointState(next_node="choose_next_step")

    assert run_worker_step(factory, **context, execute=check_confirmed).status == "running"
    assert client.get(f"/api/v1/conversations/tasks/{case_id}/intake", headers=owner).json()["facts"]["housing_basis"] == FACTS["housing_basis"]

    current_review["date"] = "2026-11-09"

    def check_fresh_review(message, _state):
        assert message.case_context.open_review_action_ids == review_ids
        return CheckpointState(next_node="verify_and_respond")

    assert run_worker_step(factory, **context, execute=check_fresh_review).status == "running"
    current_review["revoked"] = True

    def check_revocation(message, _state):
        case = message.case_context
        assert case.user_confirmed_facts.housing_basis == FACTS["housing_basis"]
        assert case.next_action == "review_sources"
        assert case.open_review_action_ids == ()
        return _finish()

    assert run_worker_step(factory, **context, execute=check_revocation).status == "completed"


def test_worker_case_context_requires_both_ownership_and_the_explicit_link(client, auth_headers):
    owner = auth_headers()
    case_id = UUID(create_case(client, owner))
    unlinked_case = UUID(create_case(client, owner))
    confirmed_intake(client, owner, str(case_id))
    factory = client.app.state.session_factory
    bob = Principal("bob")
    with factory.begin() as db:
        thread_id = create_thread(db, principal=ALICE)
        foreign_thread_id = create_thread(db, principal=bob)
        assert link_case_to_thread(db, thread_id=thread_id, case_id=case_id, principal=ALICE)
        assert read_worker_case_context(db, thread_id=thread_id, case_id=case_id, principal=bob) is None
        assert read_worker_case_context(db, thread_id=foreign_thread_id, case_id=case_id, principal=ALICE) is None
        assert read_worker_case_context(db, thread_id=thread_id, case_id=unlinked_case, principal=ALICE) is None
