"""Exercise the unmounted Phase 4 transport with signed synthetic JWTs."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.agent.checkpoints import CheckpointState
from app.agent.contract import AnswerResult, ClarifyingQuestion, SendMessage
from app.agent.reconnect_router import build_reconnect_router
from app.agent.run_requests import accept_message
from app.agent.threads import create_thread, link_case_to_thread
from app.agent.worker import RequestClarification, run_worker_step
from app.auth.tokens import Principal

KEY = bytes(range(32))
OWNER = Principal("alice")


@pytest.fixture
def paused_run(client, auth_headers):
    case = client.post("/api/v1/cases", headers=auth_headers(), json={})
    assert case.status_code == 201
    case_id = UUID(case.json()["id"])
    factory = client.app.state.session_factory
    with factory.begin() as db:
        thread_id = create_thread(db, principal=OWNER)
        assert link_case_to_thread(db, principal=OWNER, thread_id=thread_id, case_id=case_id)
        accepted = accept_message(
            db, thread_id=thread_id, principal=OWNER, key=KEY,
            message=SendMessage(client_message_id=uuid4(), case_id=case_id, text="Fixture message", language="en"),
        )
    question = ClarifyingQuestion(
        question_id=uuid4(), text="Which option?", answer_shape="single_choice",
        options=["Fixture A", "Fixture B"], missing_fields=["jurisdiction"],
    )
    context = {"thread_id": thread_id, "run_id": accepted.run_id, "principal": OWNER, "key": KEY}
    run_worker_step(factory, **context, execute=lambda *_: RequestClarification(
        question, CheckpointState(next_node="find_evidence"),
    ))
    return context, question, case_id


def run_url(context):
    return f"/api/v1/agent/threads/{context['thread_id']}/runs/{context['run_id']}"


def assert_private_error(response, status, code):
    assert response.status_code == status
    assert response.headers["Cache-Control"] == "private, no-store"
    body = response.json()
    assert set(body) == {"code", "message", "request_id"}
    assert body["code"] == code
    assert UUID(body["request_id"]).version == 4
    return body["message"]


def test_default_application_does_not_mount_phase_four_transport(client, auth_headers, paused_run):
    context, _, _ = paused_run
    response = client.get(run_url(context), headers=auth_headers())
    assert response.status_code == 404
    assert not any(path.startswith("/api/v1/agent/") for path in client.get("/openapi.json").json()["paths"])


def test_owner_reconnects_replies_and_resumes_the_same_run(client, auth_headers, paused_run):
    context, question, _ = paused_run
    client.app.include_router(build_reconnect_router(key=KEY))
    url = run_url(context)
    first = client.get(url + "/events", headers=auth_headers(), params={"limit": 1})
    assert first.status_code == 200
    assert first.headers["Cache-Control"] == "private, no-store"
    assert first.json()["events"][0]["type"] == "run.started"
    assert first.json()["has_more"] is True

    with TestClient(client.app) as reconnected:
        owner = auth_headers()
        snapshot = reconnected.get(url, headers=owner)
        assert snapshot.status_code == 200
        assert snapshot.headers["Cache-Control"] == "private, no-store"
        assert snapshot.json()["status"] == "waiting_for_information"
        page = reconnected.get(
            url + "/events", headers=owner, params={"after_seq": first.json()["last_event_seq"]},
        )
        assert page.status_code == 200
        assert page.json()["events"][0]["question"] == question.model_dump(mode="json")
        assert page.json()["last_event_seq"] == snapshot.json()["last_event_seq"]

        reply_url = f"{url}/questions/{question.question_id}/reply"
        reply = {
            "client_reply_id": str(uuid4()),
            "expected_run_revision": snapshot.json()["run_revision"],
            "text": "Fixture B",
        }
        saved = reconnected.post(reply_url, headers=owner, json=reply)
        assert saved.status_code == 200
        assert saved.headers["Cache-Control"] == "private, no-store"
        assert saved.json()["type"] == "question.answered"
        assert saved.json()["run_id"] == str(context["run_id"])
        assert reconnected.post(reply_url, headers=owner, json=reply).json() == saved.json()

        def finish(message, state):
            assert state.next_node == "find_evidence"
            assert message.clarification_reply.text == reply["text"]
            return AnswerResult(explanation="Synthetic answer", verification_status="insufficient_evidence")

        run_worker_step(client.app.state.session_factory, **context, execute=finish)
        finished = reconnected.get(url, headers=owner)
        assert finished.status_code == 200
        assert finished.json()["status"] == "completed"
        assert finished.json()["result"]["explanation"] == "Synthetic answer"
        replay = reconnected.get(url + "/events", headers=owner, params={"after_seq": page.json()["last_event_seq"]})
        assert replay.status_code == 200
        assert replay.json()["events"][0] == saved.json()
        assert replay.json()["events"][1]["type"] == "answer.completed"


def test_private_errors_hide_payloads_and_foreign_or_deleted_runs(client, auth_headers, paused_run):
    context, question, case_id = paused_run
    client.app.include_router(build_reconnect_router(key=KEY))
    url = run_url(context)
    owner, other = auth_headers(), auth_headers("bob")
    reply_url = f"{url}/questions/{question.question_id}/reply"
    reply = {"client_reply_id": str(uuid4()), "expected_run_revision": 3, "text": "Fixture A"}

    for headers in ({}, auth_headers(overrides={"aud": "wrong-audience"})):
        unauthorized = client.get(url, headers=headers)
        assert_private_error(unauthorized, 401, "unauthenticated")
        assert unauthorized.headers["WWW-Authenticate"] == "Bearer"

    foreign = client.get(url, headers=other)
    absent = client.get(run_url({**context, "run_id": uuid4()}), headers=owner)
    assert assert_private_error(foreign, 404, "unavailable") == assert_private_error(absent, 404, "unavailable")
    assert_private_error(client.get(url + "/events", headers=other), 404, "unavailable")
    assert_private_error(client.post(reply_url, headers=other, json=reply), 404, "unavailable")
    assert_private_error(
        client.get(url + "/events", headers=owner, params={"after_seq": 50}), 422, "invalid_cursor",
    )
    malformed = client.post(reply_url, headers=owner, json={**reply, "unexpected": "private fixture payload"})
    assert_private_error(malformed, 422, "invalid_request")
    assert "private fixture payload" not in malformed.text
    assert_private_error(client.post(reply_url, headers=owner, json={**reply, "text": "Fixture C"}), 422, "invalid_reply")
    assert_private_error(
        client.post(reply_url, headers=owner, json={**reply, "expected_run_revision": 2}), 409, "stale_question",
    )
    assert client.get(url, headers=owner).json()["status"] == "waiting_for_information"
    assert client.delete(f"/api/v1/cases/{case_id}", headers=owner).status_code == 204
    assert_private_error(client.get(url, headers=owner), 404, "unavailable")
    assert_private_error(client.post(reply_url, headers=owner, json=reply), 404, "unavailable")
