"""Exercise the unmounted Phase 4 transport with signed synthetic JWTs."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.agent.checkpoints import CheckpointState
from app.agent.contract import AnswerResult, ClarifyingQuestion, SendMessage
from app.agent.reconnect_router import build_reconnect_router
from app.agent.run_requests import AgentRunRequest, accept_message
from app.agent.threads import create_thread, link_case_to_thread
from app.agent.worker import RequestClarification, run_worker_step
from app.auth.tokens import Principal

KEY = bytes(range(32))
OWNER = Principal("alice")
ACTIVE_RUNS_URL = "/api/v1/agent/runs/active"


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
    assert client.get(ACTIVE_RUNS_URL, headers=auth_headers()).status_code == 404
    assert not any(path.startswith("/api/v1/agent/") for path in client.get("/openapi.json").json()["paths"])


def test_owner_reconnects_replies_and_resumes_the_same_run(client, auth_headers, paused_run):
    context, question, case_id = paused_run
    client.app.include_router(build_reconnect_router(key=KEY))
    url = run_url(context)
    first = client.get(url + "/events", headers=auth_headers(), params={"limit": 1})
    assert first.status_code == 200
    assert first.headers["Cache-Control"] == "private, no-store"
    assert first.json()["events"][0]["type"] == "run.started"
    assert first.json()["has_more"] is True

    with TestClient(client.app) as reconnected:
        owner = auth_headers()
        discovery = reconnected.get(ACTIVE_RUNS_URL, headers=owner)
        assert discovery.status_code == 200
        assert discovery.headers["Cache-Control"] == "private, no-store"
        active, = discovery.json()["items"]
        assert discovery.json()["next_cursor"] is None
        assert set(active) == {"thread_id", "run_id", "case_id", "status", "accepted_at"}
        assert active["case_id"] == str(case_id)
        assert active["status"] == "waiting_for_information"
        url = run_url(active)
        snapshot = reconnected.get(url, headers=owner)
        assert snapshot.status_code == 200
        assert snapshot.headers["Cache-Control"] == "private, no-store"
        assert snapshot.json()["status"] == "waiting_for_information"
        page = reconnected.get(url + "/events", headers=owner)
        assert page.status_code == 200
        assert page.json()["events"][0] == first.json()["events"][0]
        assert page.json()["events"][-1]["question"] == question.model_dump(mode="json")
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
        late_stop = reconnected.post(
            url + "/stop", headers=owner, json={"expected_run_revision": snapshot.json()["run_revision"]},
        )
        assert late_stop.status_code == 200
        assert late_stop.json() == finished.json()
        assert reconnected.get(ACTIVE_RUNS_URL, headers=owner).json() == {"items": [], "next_cursor": None}
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

    assert_private_error(client.get(ACTIVE_RUNS_URL), 401, "unauthenticated")
    assert client.get(ACTIVE_RUNS_URL, headers=other).json() == {"items": [], "next_cursor": None}

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
    assert client.get(ACTIVE_RUNS_URL, headers=owner).json() == {"items": [], "next_cursor": None}
    assert_private_error(client.get(url, headers=owner), 404, "unavailable")
    assert_private_error(client.post(reply_url, headers=owner, json=reply), 404, "unavailable")


def test_active_run_cursor_handles_equal_timestamps_and_a_run_that_finishes_between_pages(client, auth_headers):
    client.app.include_router(build_reconnect_router(key=KEY))
    factory = client.app.state.session_factory
    owner, other = OWNER, Principal("bob")
    accepted_at = datetime(2026, 11, 18, 8, 30, tzinfo=timezone.utc)
    alice_runs = {}
    with factory.begin() as db:
        for principal in (owner, owner, owner, other):
            thread_id = create_thread(db, principal=principal)
            result = accept_message(
                db, thread_id=thread_id, principal=principal, key=KEY,
                message=SendMessage(client_message_id=uuid4(), text="Private fixture", language="en"),
            )
            run = db.get(AgentRunRequest, str(result.run_id))
            run.accepted_at = accepted_at
            if principal == owner:
                alice_runs[run.id] = thread_id

    headers = auth_headers()
    first_response = client.get(ACTIVE_RUNS_URL, headers=headers, params={"limit": 2})
    assert first_response.status_code == 200
    first = first_response.json()
    expected_ids = sorted(alice_runs, reverse=True)
    assert [item["run_id"] for item in first["items"]] == expected_ids[:2]
    assert all(item["status"] == "queued" and item["case_id"] is None for item in first["items"])
    cursor = first["next_cursor"]
    assert cursor["run_id"] == expected_ids[1]

    def finish(*_):
        return AnswerResult(explanation="Synthetic answer", verification_status="insufficient_evidence")

    run_worker_step(
        factory, thread_id=alice_runs[cursor["run_id"]], run_id=UUID(cursor["run_id"]),
        principal=owner, key=KEY, execute=finish,
    )
    offset_time = datetime.fromisoformat(cursor["accepted_at"]).astimezone(timezone(timedelta(hours=1)))
    params = {"limit": 2, "before_accepted_at": offset_time.isoformat(), "before_run_id": cursor["run_id"]}
    next_response = client.get(ACTIVE_RUNS_URL, headers=headers, params=params)
    assert next_response.status_code == 200
    assert [item["run_id"] for item in next_response.json()["items"]] == expected_ids[2:]
    assert next_response.json()["next_cursor"] is None

    for invalid in (
        {"before_run_id": cursor["run_id"]},
        {**params, "before_accepted_at": "2026-11-18T08:30:00"},
        {**params, "before_accepted_at": "0001-01-01T00:00:00+14:00"},
        {"limit": 51},
    ):
        response = client.get(ACTIVE_RUNS_URL, headers=headers, params=invalid)
        assert_private_error(response, 422, "invalid_request")


def test_stop_requires_the_owner_and_current_revision_and_invalidates_pending_replies(client, auth_headers, paused_run):
    context, question, _ = paused_run
    client.app.include_router(build_reconnect_router(key=KEY))
    url = run_url(context)
    owner = auth_headers()
    before = client.get(url, headers=owner).json()
    payload = {"expected_run_revision": before["run_revision"]}
    stop_url = url + "/stop"
    assert_private_error(client.post(stop_url, headers=auth_headers("bob"), json=payload), 404, "unavailable")
    assert_private_error(client.post(
        stop_url, headers=owner, json={"expected_run_revision": before["run_revision"] - 1},
    ), 409, "stale_run")
    assert client.get(url, headers=owner).json() == before

    stopped = client.post(stop_url, headers=owner, json=payload)
    assert stopped.status_code == 200
    assert stopped.headers["Cache-Control"] == "private, no-store"
    assert stopped.json()["status"] == "stopped"
    assert client.post(stop_url, headers=owner, json=payload).json() == stopped.json()
    assert client.get(ACTIVE_RUNS_URL, headers=owner).json()["items"] == []
    replay = client.get(url + "/events", headers=owner, params={"after_seq": before["last_event_seq"]})
    event, = replay.json()["events"]
    assert event["type"] == "run.stopped" and event["committed_operation_ids"] == []

    late_reply = {"client_reply_id": str(uuid4()), "text": "Fixture A", **payload}
    assert_private_error(client.post(
        f"{url}/questions/{question.question_id}/reply", headers=owner, json=late_reply,
    ), 409, "stale_question")
