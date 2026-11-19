"""Owner-scoped case choices through the real worker and signed reply API."""

from functools import partial
from uuid import UUID, uuid4

import pytest

from app.agent.candidate_resolution import choose_candidate_step
from app.agent.checkpoints import CheckpointState
from app.agent.contract import MessageGoal, SendMessage
from app.agent.intent_extraction import identify_intent_step
from app.agent.reconnect_router import build_reconnect_router
from app.agent.run_requests import AgentRunRequest, accept_message
from app.agent.threads import create_thread, link_case_to_thread
from app.agent.tool_access import ToolAccessDenied, authorize_tool_call
from app.agent.tool_contract import ReadCaseContext
from app.agent.worker import run_worker_step
from app.cases.model import CaseRecord
from test_agent_run_requests import ALICE, KEY


def _run(client, text, *, language="en", bind=False):
    factory = client.app.state.session_factory
    bound, other, second_other, unlinked, foreign = [uuid4() for _ in range(5)]
    with factory.begin() as db:
        db.add_all(CaseRecord(id=str(case), owner_subject=ALICE.subject)
                   for case in [bound, other, second_other, unlinked])
        db.add(CaseRecord(id=str(foreign), owner_subject="bob"))
        db.flush()
        thread = create_thread(db, principal=ALICE)
        for case in (bound, other, second_other):
            assert link_case_to_thread(db, thread_id=thread, case_id=case, principal=ALICE)
        assert not link_case_to_thread(db, thread_id=thread, case_id=foreign, principal=ALICE)
        accepted = accept_message(
            db, thread_id=thread, principal=ALICE, key=KEY,
            message=SendMessage(
                client_message_id=uuid4(), language=language, text=text, case_id=bound if bind else None,
            ),
        )
    context = {"thread_id": thread, "run_id": accepted.run_id, "principal": ALICE, "key": KEY}
    client.app.include_router(build_reconnect_router(key=KEY))
    url = f"/api/v1/agent/threads/{thread}/runs/{accepted.run_id}"
    return factory, context, url, bound, other, second_other


def _read_question(client, url, owner):
    snapshot = client.get(url, headers=owner).json()
    assert snapshot["status"] == "waiting_for_information"
    page = client.get(url + "/events", headers=owner, params={"after_seq": snapshot["last_event_seq"] - 1}).json()
    [asked] = page["events"]
    return snapshot, asked["question"]


def _select(client, url, owner, snapshot, question, case_id):
    option = next(choice["label"] for choice in question["case_choices"] if choice["case_id"] == str(case_id))
    reply = {"client_reply_id": str(uuid4()), "expected_run_revision": snapshot["run_revision"], "text": option}
    path = f"{url}/questions/{question['question_id']}/reply"
    return path, reply, client.post(path, headers=owner, json=reply)


def _resume_case(factory, context):
    run_worker_step(factory, **context, execute=lambda *_: CheckpointState(next_node="identify_intent"))
    run_worker_step(factory, **context, execute=partial(identify_intent_step, catalogue_names=()))
    return run_worker_step(factory, **context, execute=_no_routing)


def _no_routing(*_):
    pytest.fail("Case selection must not route or read case facts")


@pytest.mark.parametrize(("language", "text", "prompt"), [
    ("en", "What is the status of the other application?", "Which saved case do you mean?"),
    ("it", "E per l’altra pratica?", "A quale pratica salvata ti riferisci?"),
])
def test_other_case_is_clarified_with_only_active_owned_links(client, auth_headers, language, text, prompt):
    factory, context, url, bound, other, second_other = _run(client, text, language=language, bind=True)
    owner = auth_headers("alice")
    _resume_case(factory, context)
    snapshot, question = _read_question(client, url, owner)
    assert question["text"] == prompt
    assert {choice["case_id"] for choice in question["case_choices"]} == {str(other), str(second_other)}
    assert client.get(url + "/events", headers=auth_headers("bob")).status_code == 404

    path, reply, response = _select(client, url, owner, snapshot, question, other)
    assert response.status_code == 200 and response.json()["selected_case_id"] == str(other)
    assert client.post(path, headers=auth_headers("bob"), json=reply).status_code == 404
    assert client.post(path, headers=owner, json=reply).json() == response.json()
    assert run_worker_step(factory, **context, execute=_no_routing).selected_case.case_id == other
    result = client.get(url, headers=owner).json()
    assert result["selected_case"]["case_id"] == str(other)
    assert result["handoff"] is None and result["result"]["citations"] == []

    with factory.begin() as db:
        run = db.get(AgentRunRequest, str(context["run_id"]))
        assert run.case_id == str(bound)
        with pytest.raises(ToolAccessDenied):
            authorize_tool_call(
                db, thread_id=context["thread_id"], run_id=context["run_id"], principal=ALICE,
                call=ReadCaseContext(tool="read_case_context", case_id=other),
            )
        assert accept_message(
            db, thread_id=context["thread_id"], principal=ALICE, key=KEY,
            message=SendMessage(client_message_id=uuid4(), language=language, text="Continue", case_id=other),
        ).outcome == "accepted"


def test_case_archive_between_offer_and_reply_is_rejected_and_live_selection_is_rechecked(client, auth_headers):
    factory, context, url, _, other, second_other = _run(client, "Resume my case")
    owner = auth_headers("alice")
    _resume_case(factory, context)
    snapshot, question = _read_question(client, url, owner)
    archive = client.patch(f"/api/v1/cases/{other}/archive", headers=owner, json={"archived": True})
    assert archive.status_code == 200
    _, _, stale = _select(client, url, owner, snapshot, question, other)
    assert stale.status_code == 409
    _, _, fresh = _select(client, url, owner, snapshot, question, second_other)
    assert fresh.status_code == 200
    run_worker_step(factory, **context, execute=_no_routing)
    assert client.get(url, headers=owner).json()["selected_case"]["case_id"] == str(second_other)
    assert client.patch(f"/api/v1/cases/{second_other}/archive", headers=owner, json={"archived": True}).status_code == 200
    reopened = client.get(url, headers=owner).json()
    assert reopened["selected_case"] is None and reopened["result"]["selected_case"] is None


def test_explicit_linked_case_is_verified_without_another_question(client, auth_headers):
    factory, context, url, bound, _, _ = _run(client, "Resume my case", bind=True)
    snapshot = _resume_case(factory, context)
    assert snapshot.status == "completed" and snapshot.selected_case.case_id == bound
    assert client.get(url, headers=auth_headers("alice")).json()["selected_case"]["case_id"] == str(bound)


def test_active_goal_case_choices_preserve_goal_and_filter_by_its_procedure(client, auth_headers):
    factory, context, url, _, other, second_other = _run(client, "Synthetic task choice")
    with factory.begin() as db:
        db.get(CaseRecord, str(other)).procedure = "fixture-tax"
        db.get(CaseRecord, str(second_other)).procedure = "fixture-tax"
    state = CheckpointState(
        next_node="choose_next_step", intent="plan_multiple_tasks", preferred_goal=2,
        goals=[MessageGoal(procedure_candidates=["milan_residence_change"]),
               MessageGoal(procedure_candidates=["fixture-tax"])],
    )
    run_worker_step(factory, **context, execute=lambda *_: state)
    run_worker_step(factory, **context, execute=partial(
        choose_candidate_step, case_locations={}, confirmed_dates={}, confirmed_circumstances={},
        assignments=(), trusted_passage_ids=frozenset(), reviewed_labels={"fixture-tax": "Synthetic tax task"},
    ))
    owner = auth_headers("alice")
    snapshot, question = _read_question(client, url, owner)
    assert snapshot["goal_selection"]["active_goal"] == 2
    assert {choice["case_id"] for choice in question["case_choices"]} == {str(other), str(second_other)}
    _, _, reply = _select(client, url, owner, snapshot, question, second_other)
    assert reply.status_code == 200
    final = run_worker_step(factory, **context, execute=_no_routing)
    assert final.goal_selection.active_goal == 2 and final.selected_case.case_id == second_other


def test_worker_reasks_when_a_case_is_archived_after_an_accepted_reply(client, auth_headers):
    factory, context, url, _, other, _ = _run(client, "Resume my case")
    owner = auth_headers("alice")
    _resume_case(factory, context)
    snapshot, question = _read_question(client, url, owner)
    _, _, reply = _select(client, url, owner, snapshot, question, other)
    assert reply.status_code == 200
    assert client.patch(f"/api/v1/cases/{other}/archive", headers=owner, json={"archived": True}).status_code == 200
    assert run_worker_step(factory, **context, execute=_no_routing).status == "waiting_for_information"
    _, refreshed = _read_question(client, url, owner)
    assert refreshed["question_id"] != question["question_id"]
    assert all(choice["case_id"] != str(other) for choice in refreshed["case_choices"])


def test_a_goal_with_a_different_destination_does_not_use_the_bound_milan_case(client):
    factory, context, _, _, _, _ = _run(client, "Synthetic task choice", bind=True)
    state = CheckpointState(
        next_node="choose_next_step", intent="plan_multiple_tasks", preferred_goal=2,
        goals=[MessageGoal(procedure_candidates=["milan_residence_change"], location_candidates=["IT-MI-MILANO"]),
               MessageGoal(procedure_candidates=["milan_residence_change"], location_candidates=["IT-CO-COMO"])],
    )
    run_worker_step(factory, **context, execute=lambda *_: state)
    result = run_worker_step(factory, **context, execute=partial(
        choose_candidate_step, case_locations={}, confirmed_dates={}, confirmed_circumstances={},
        assignments=(), trusted_passage_ids=frozenset(), reviewed_labels={},
    ))
    assert result.goal_selection.active_goal == 2
    assert result.selected_case is None and result.result.missing_information == ["case_reference"]
