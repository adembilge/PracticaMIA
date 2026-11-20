"""Exercise synthetic timeouts and lost acknowledgements at signed HTTP boundaries."""

from datetime import timedelta
import json
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.agent.checkpoints import CheckpointState, load_checkpoint
from app.agent.contract import AnswerResult
from app.agent.reconnect_router import build_reconnect_router
from app.agent.run_requests import AgentRunRequest
from app.agent.threads import AgentThread, create_thread, link_case_to_thread
from app.agent.worker import ModelProviderTimeout, run_worker_batch
from test_agent_reconnect_http import KEY, OWNER, assert_private_error


@pytest.fixture
def conversation(client, auth_headers):
    owner = auth_headers()
    case = client.post("/api/v1/cases", headers=owner, json={})
    assert case.status_code == 201
    case_id = UUID(case.json()["id"])
    factory = client.app.state.session_factory
    with factory.begin() as db:
        thread_id = create_thread(db, principal=OWNER)
        assert link_case_to_thread(db, principal=OWNER, thread_id=thread_id, case_id=case_id)
    client.app.include_router(build_reconnect_router(key=KEY))
    thread = f"/api/v1/agent/threads/{thread_id}"
    message = {
        "client_message_id": str(uuid4()), "text": "Synthetic question", "language": "en", "case_id": str(case_id),
        "expected_thread_revision": 1,
    }
    return factory, owner, thread, thread_id, message


def test_model_timeout_replays_a_safe_failure_and_allows_an_explicit_retry(client, auth_headers, conversation, caplog):
    factory, owner, thread, thread_id, message = conversation
    accepted = client.post(thread + "/messages", headers=owner, json=message)
    assert accepted.status_code == 202
    run_id = UUID(accepted.json()["run_id"])
    run_url = f"{thread}/runs/{run_id}"
    visits = []

    def timed_out(_message, state):
        visits.append(state.next_node)
        if state.next_node == "load_context":
            return CheckpointState(next_node="verify_and_respond", intent="find_procedure")
        raise ModelProviderTimeout("private provider diagnostic")

    options = {"key": KEY, "lease_for": timedelta(minutes=1)}
    assert run_worker_batch(factory, **options, execute=timed_out, max_steps=4) == 2
    assert visits == ["load_context", "verify_and_respond"]

    snapshot = client.get(run_url, headers=owner).json()
    assert snapshot["status"] == "failed"
    assert snapshot["result"] is None and snapshot["handoff"] is None
    response = client.get(run_url + "/events", headers=owner, params={"after_seq": 2})
    assert response.status_code == 200 and response.headers["Cache-Control"] == "private, no-store"
    [failure] = response.json()["events"]
    assert failure["type"] == "run.failed"
    assert failure["code"] == "provider_unavailable"
    assert failure["retryable"] is True and failure["recovery"] == "retry_later"
    assert "private provider diagnostic" not in response.text
    assert_private_error(client.get(run_url + "/events", headers=auth_headers("bob")), 404, "unavailable")
    [record] = [row for row in caplog.records if row.name == "app.agent.diagnostics"]
    assert json.loads(record.getMessage()) == {
        "event": "agent_failure", "schema_version": 1, "code": "provider_unavailable",
        "stage": "verify_and_respond", "intent": "find_procedure", "query_kind": "model_request",
        "tool": None, "source_version_ids": [],
    }
    assert record.exc_info is None
    assert "private provider diagnostic" not in caplog.text and message["text"] not in caplog.text
    assert str(run_id) not in caplog.text and message["case_id"] not in caplog.text
    with factory() as db:
        assert load_checkpoint(db, thread_id=thread_id, run_id=run_id, principal=OWNER, key=KEY) is None
        run = db.get(AgentRunRequest, str(run_id))
        assert run.lease_token is None and run.lease_expires_at is None

    retried = client.post(thread + "/messages", headers=owner, json=message | {
        "client_message_id": str(uuid4()), "expected_thread_revision": accepted.json()["accepted_revision"],
    })
    assert retried.status_code == 202 and retried.json()["run_id"] != str(run_id)
    answer = AnswerResult(explanation="Synthetic recovery", verification_status="insufficient_evidence")
    assert run_worker_batch(factory, **options, execute=lambda *_: answer, max_steps=2) == 1
    assert client.get(f"{thread}/runs/{retried.json()['run_id']}", headers=owner).json()["status"] == "completed"
    assert client.get(run_url, headers=owner).json() == snapshot


def test_duplicate_message_after_a_lost_acknowledgement_keeps_one_run_and_answer(client, conversation):
    factory, owner, thread, thread_id, message = conversation
    send = thread + "/messages"
    first = client.post(send, headers=owner, json=message)
    assert first.status_code == 202
    replay = client.post(send, headers=owner, json=message)
    assert replay.status_code == 202 and replay.json() == first.json()
    accepted = replay.json()

    assert_private_error(
        client.post(send, headers=owner, json=message | {"text": "Changed body"}), 409, "message_conflict",
    )

    calls = []

    def respond(stored, _state):
        calls.append(stored.text)
        return AnswerResult(explanation="Synthetic answer", verification_status="insufficient_evidence")

    options = {"key": KEY, "lease_for": timedelta(minutes=1), "execute": respond, "max_steps": 3}
    assert run_worker_batch(factory, **options) == 1
    assert client.post(send, headers=owner, json=message).json() == accepted
    assert run_worker_batch(factory, **options) == 0
    assert calls == [message["text"]]

    events_url = f"{thread}/runs/{accepted['run_id']}/events"
    journal = client.get(events_url, headers=owner).json()["events"]
    assert [event["type"] for event in journal] == ["run.started", "answer.completed"]
    assert journal[0]["client_message_id"] == message["client_message_id"]
    with factory() as db:
        run_ids = db.scalars(select(AgentRunRequest.id).where(AgentRunRequest.thread_id == str(thread_id))).all()
        assert run_ids == [accepted["run_id"]]
        assert db.get(AgentThread, str(thread_id)).revision == accepted["accepted_revision"]
