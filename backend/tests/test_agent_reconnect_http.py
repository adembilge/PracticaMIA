"""Exercise the unmounted Phase 4 transport with signed synthetic JWTs."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.agent.checkpoints import CheckpointState, load_checkpoint
from app.agent.contract import AnswerResult, ApprovalProposal, ClarifyingQuestion, SendMessage
from app.agent.reconnect_router import build_reconnect_router
from app.agent.run_events import AgentRunEvent, EventConflict
from app.agent.run_requests import AgentRunRequest, accept_message
from app.agent.threads import create_thread, link_case_to_thread
from app.agent.worker import RequestApproval, RequestClarification, run_worker_step
from app.auth.tokens import Principal

KEY = bytes(range(32))
OWNER = Principal("alice")
ACTIVE_RUNS_URL = "/api/v1/agent/runs/active"


def pause_for_question(client, auth_headers, question, *, language="en"):
    case = client.post("/api/v1/cases", headers=auth_headers(), json={})
    assert case.status_code == 201
    case_id = UUID(case.json()["id"])
    factory = client.app.state.session_factory
    with factory.begin() as db:
        thread_id = create_thread(db, principal=OWNER)
        assert link_case_to_thread(db, principal=OWNER, thread_id=thread_id, case_id=case_id)
        accepted = accept_message(
            db, thread_id=thread_id, principal=OWNER, key=KEY,
            message=SendMessage(client_message_id=uuid4(), case_id=case_id, text="Fixture message", language=language),
        )
    context = {"thread_id": thread_id, "run_id": accepted.run_id, "principal": OWNER, "key": KEY}
    run_worker_step(factory, **context, execute=lambda *_: RequestClarification(
        question, CheckpointState(next_node="find_evidence"),
    ))
    return context, question, case_id


@pytest.fixture
def paused_run(client, auth_headers):
    return pause_for_question(client, auth_headers, ClarifyingQuestion(
        question_id=uuid4(), text="Which option?", answer_shape="single_choice",
        options=["Fixture A", "Fixture B"], missing_fields=["jurisdiction"],
    ))


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


def test_first_message_creates_one_private_conversation_without_a_case(client, auth_headers):
    client.app.include_router(build_reconnect_router(key=KEY))
    url = "/api/v1/agent/conversations"
    owner, other = auth_headers(), auth_headers("bob")
    message = {"client_message_id": str(uuid4()), "text": "Vorrei capire come cambiare residenza.", "language": "it"}
    assert_private_error(client.post(url, json=message), 401, "unauthenticated")
    assert_private_error(client.post(url, headers=owner, json={**message, "case_id": str(uuid4())}), 422, "invalid_request")
    first = client.post(url, headers=owner, json=message)
    assert first.status_code == 202
    assert first.headers["Cache-Control"] == "private, no-store"
    body = first.json()
    assert client.post(url, headers=owner, json=message).json() == body
    assert_private_error(client.post(url, headers=owner, json={**message, "text": "A different request"}), 409, "message_conflict")

    active = client.get(ACTIVE_RUNS_URL, headers=owner).json()["items"]
    assert len(active) == 1
    assert {field: active[0][field] for field in ("thread_id", "run_id")} == {
        field: body[field] for field in ("thread_id", "run_id")
    }
    assert active[0]["case_id"] is None
    assert_private_error(client.get(run_url(body), headers=other), 404, "unavailable")
    separate = client.post(url, headers=other, json=message)
    assert separate.status_code == 202 and separate.json()["thread_id"] != body["thread_id"]


def test_switch_between_owned_cases_and_reopen_the_original_question(client, auth_headers, paused_run):
    first, question, first_case = paused_run
    owner = auth_headers()
    thread_url = f"/api/v1/agent/threads/{first['thread_id']}"
    first_url = run_url(first)
    factory = client.app.state.session_factory
    second_case, archived, unlinked = [
        UUID(client.post("/api/v1/cases", headers=owner, json={}).json()["id"]) for _ in range(3)
    ]
    with factory.begin() as db:
        for case in (second_case, archived):
            assert link_case_to_thread(db, principal=OWNER, thread_id=first["thread_id"], case_id=case)
    assert client.patch(f"/api/v1/cases/{archived}/archive", json={"archived": True}, headers=owner).status_code == 200
    client.app.include_router(build_reconnect_router(key=KEY))

    path = thread_url + "/cases"
    tasks = client.get(path, headers=owner)
    assert tasks.headers["Cache-Control"] == "private, no-store"
    assert {UUID(item["case_id"]): item["run_id"] for item in tasks.json()["items"]} == {
        first_case: str(first["run_id"]), second_case: None,
    }
    ordered = sorted([first_case, second_case])
    assert [item["case_id"] for item in client.get(
        path, headers=owner, params={"after_case_id": str(ordered[0]), "language": "it"},
    ).json()["items"]] == [str(ordered[1])]
    assert_private_error(client.get(path, headers=auth_headers("bob")), 404, "unavailable")

    message = {"client_message_id": str(uuid4()), "case_id": str(second_case), "text": "Second task", "language": "en"}
    send_url = thread_url + "/messages"
    assert_private_error(client.post(send_url, headers=auth_headers("bob"), json=message), 404, "unavailable")
    for unavailable in (archived, unlinked):
        assert_private_error(client.post(
            send_url, headers=owner, json=message | {"case_id": str(unavailable)},
        ), 404, "unavailable")
    assert_private_error(client.post(
        send_url, headers=owner, json=message | {"case_id": str(first_case)},
    ), 409, "conversation_busy")
    before = client.get(first_url, headers=owner).json()
    accepted = client.post(send_url, headers=owner, json=message)
    assert accepted.status_code == 202
    assert client.post(send_url, headers=owner, json=message).json() == accepted.json()
    second = first | {"run_id": UUID(accepted.json()["run_id"])}
    second_url = run_url(second)

    reply = {"client_reply_id": str(uuid4()), "expected_run_revision": before["run_revision"], "text": "Fixture A"}
    reply_url = f"{first_url}/questions/{question.question_id}/reply"
    assert_private_error(client.post(reply_url, headers=owner, json=reply), 409, "conversation_busy")
    assert client.get(first_url, headers=owner).json() == before

    second_question = ClarifyingQuestion(
        question_id=uuid4(), text="Which other detail?", answer_shape="free_text", options=[], missing_fields=["date"],
    )
    second_pause = run_worker_step(factory, **second, execute=lambda *_: RequestClarification(
        second_question, CheckpointState(next_node="find_evidence"),
    ))
    assert second_pause.status == "waiting_for_information"
    assert {item["run_id"] for item in client.get(path, headers=owner).json()["items"]} == {
        str(first["run_id"]), str(second["run_id"]),
    }
    assert client.get(first_url + "/events", headers=owner).json()["events"][-1]["question"] == (
        question.model_dump(mode="json")
    )
    assert_private_error(client.post(
        f"{second_url}/questions/{question.question_id}/reply",
        headers=owner, json=reply | {"expected_run_revision": second_pause.run_revision},
    ), 409, "stale_question")
    answered = client.post(reply_url, headers=owner, json=reply)
    assert answered.status_code == 200
    assert client.post(reply_url, headers=owner, json=reply).json() == answered.json()

    def resume(message, state):
        assert message.case_id == first_case and state.next_node == "find_evidence"
        assert message.clarification_reply.question_id == question.question_id
        return AnswerResult(explanation="First case resumed.", verification_status="insufficient_evidence")

    assert run_worker_step(factory, **first, execute=resume).status == "completed"
    assert client.get(second_url, headers=owner).json()["run_revision"] == second_pause.run_revision
    assert client.get(second_url + "/events", headers=owner).json()["events"][-1]["question"]["question_id"] == (
        str(second_question.question_id)
    )


def test_pending_proposal_replays_the_exact_read_only_preview(client, auth_headers):
    owner = auth_headers()
    case = client.post("/api/v1/cases", headers=owner, json={})
    assert case.status_code == 201
    case_id = UUID(case.json()["id"])
    intake = f"/api/v1/cases/{case_id}/intake"
    before = client.get(intake, headers=owner).json()
    factory = client.app.state.session_factory
    with factory.begin() as db:
        thread_id = create_thread(db, principal=OWNER)
        assert link_case_to_thread(db, principal=OWNER, thread_id=thread_id, case_id=case_id)
        run = accept_message(
            db, thread_id=thread_id, principal=OWNER, key=KEY,
            message=SendMessage(client_message_id=uuid4(), case_id=case_id, text="Fixture change", language="en"),
        )
    context = {"thread_id": thread_id, "run_id": run.run_id, "principal": OWNER, "key": KEY}
    state = CheckpointState(next_node="verify_and_respond")
    proposal = ApprovalProposal(
        proposal_id=uuid4(), case_id=case_id, field_id="move_in_date",
        previous_value=None, proposed_value="2026-11-19", rationale="Synthetic user correction.",
        expected_case_revision=7, expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    foreign = proposal.model_copy(update={"case_id": uuid4()})
    with pytest.raises(EventConflict, match="Proposal must belong to the run's case"):
        run_worker_step(factory, **context, execute=lambda *_: RequestApproval(foreign, state))
    pending = run_worker_step(factory, **context, execute=lambda *_: RequestApproval(proposal, state))
    assert pending.status == "waiting_for_approval"
    assert pending.pending_proposal == proposal
    with factory.begin() as db:
        saved = load_checkpoint(db, **context)
        assert saved.event_seq == pending.last_event_seq
        assert saved.state.pending_proposal_id == proposal.proposal_id
        event = db.get(AgentRunEvent, (str(run.run_id), saved.event_seq))
        assert proposal.rationale.encode() not in event.ciphertext

    client.app.include_router(build_reconnect_router(key=KEY))
    url = run_url(context)
    with TestClient(client.app) as reopened:
        response = reopened.get(url, headers=owner)
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "private, no-store"
        assert response.json()["pending_proposal"] == proposal.model_dump(mode="json")
        events = reopened.get(url + "/events", headers=owner).json()["events"]
        assert [event["type"] for event in events] == ["run.started", "approval.requested"]
        assert events[-1]["proposal"] == response.json()["pending_proposal"]
        assert_private_error(reopened.get(url, headers=auth_headers("bob")), 404, "unavailable")

        stopped = reopened.post(
            url + "/stop", headers=owner, json={"expected_run_revision": pending.run_revision},
        )
        assert stopped.status_code == 200
        assert stopped.json()["pending_proposal"] is None
        assert stopped.json()["status"] == "stopped"
    assert client.get(intake, headers=owner).json() == before


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
        assert saved.json()["origin"] == "user_entered"
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
    invalid_choice = client.post(reply_url, headers=owner, json={**reply, "text": "Fixture C"})
    assert assert_private_error(invalid_choice, 422, "invalid_reply") == "Select one of the offered choices."
    assert "Fixture C" not in invalid_choice.text
    assert_private_error(
        client.post(reply_url, headers=owner, json={**reply, "expected_run_revision": 2}), 409, "stale_question",
    )
    assert client.get(url, headers=owner).json()["status"] == "waiting_for_information"
    assert client.delete(f"/api/v1/cases/{case_id}", headers=owner).status_code == 204
    assert client.get(ACTIVE_RUNS_URL, headers=owner).json() == {"items": [], "next_cursor": None}
    assert_private_error(client.get(url, headers=owner), 404, "unavailable")
    assert_private_error(client.post(reply_url, headers=owner, json=reply), 404, "unavailable")


def test_stale_question_identity_and_revision_leave_the_new_question_pending(client, auth_headers, paused_run):
    context, question, _ = paused_run
    client.app.include_router(build_reconnect_router(key=KEY))
    owner = auth_headers()
    url = run_url(context)
    revision = client.get(url, headers=owner).json()["run_revision"]
    reply_url = f"{url}/questions/{question.question_id}/reply"
    original = {"client_reply_id": str(uuid4()), "expected_run_revision": revision, "text": "Fixture A"}
    accepted = client.post(reply_url, headers=owner, json=original)
    assert accepted.status_code == 200

    followup = question.model_copy(update={"question_id": uuid4(), "text": "Which follow-up option?"})

    def request_followup(message, state):
        assert message.clarification_reply.question_id == question.question_id
        return RequestClarification(followup, state)

    run_worker_step(client.app.state.session_factory, **context, execute=request_followup)
    snapshot = client.get(url, headers=owner).json()
    journal = client.get(url + "/events", headers=owner).json()
    assert snapshot["status"] == "waiting_for_information"
    assert journal["events"][-1]["question"]["question_id"] == str(followup.question_id)
    current_revision = snapshot["run_revision"]
    for question_id, sent_revision in (
        (question.question_id, revision),
        (question.question_id, current_revision),
        (followup.question_id, revision),
        (uuid4(), current_revision),
    ):
        stale = client.post(f"{url}/questions/{question_id}/reply", headers=owner, json={
            "client_reply_id": str(uuid4()), "expected_run_revision": sent_revision, "text": "Fixture B",
        })
        assert_private_error(stale, 409, "stale_question")

    assert client.post(reply_url, headers=owner, json=original).json() == accepted.json()
    assert client.get(url, headers=owner).json() == snapshot
    assert client.get(url + "/events", headers=owner).json() == journal


def test_invalid_free_text_date_explains_the_format_and_preserves_the_same_question(client, auth_headers):
    hint = "Inserisci la data del trasferimento nel formato AAAA-MM-GG o GG/MM/AAAA."
    context, question, _ = pause_for_question(client, auth_headers, ClarifyingQuestion(
        question_id=uuid4(), text="Qual è la data del trasferimento?", answer_shape="free_text",
        missing_fields=["move_in_date"], answer_format="calendar_date", reply_hint=hint,
    ), language="it")
    client.app.include_router(build_reconnect_router(key=KEY))
    owner = auth_headers()
    url = run_url(context)
    before = client.get(url, headers=owner).json()
    reply_url = f"{url}/questions/{question.question_id}/reply"
    reply = {"client_reply_id": str(uuid4()), "expected_run_revision": before["run_revision"]}

    for bad in ("2026-02-30", "Private fixture payload"):
        rejected = client.post(reply_url, headers=owner, json={**reply, "text": bad})
        assert assert_private_error(rejected, 422, "invalid_reply") == hint
        assert bad not in rejected.text
    blank = client.post(reply_url, headers=owner, json={**reply, "text": "  "})
    assert "Enter a reply" in assert_private_error(blank, 422, "invalid_request")
    foreign = client.post(reply_url, headers=auth_headers("bob"), json={**reply, "text": "2026-02-30"})
    assert_private_error(foreign, 404, "unavailable")
    assert hint not in foreign.text
    assert client.get(url, headers=owner).json() == before
    events = client.get(url + "/events", headers=owner).json()["events"]
    assert [event["type"] for event in events] == ["run.started", "question.requested"]
    assert events[-1]["question"] == question.model_dump(mode="json")

    corrected = {**reply, "text": " 18/11/2026 "}
    saved = client.post(reply_url, headers=owner, json=corrected)
    assert saved.status_code == 200
    assert saved.json()["text"] == "18/11/2026"
    assert saved.json()["question_id"] == str(question.question_id)
    assert client.post(reply_url, headers=owner, json=corrected).json() == saved.json()


@pytest.mark.parametrize(("payload", "expected", "original"), [
    ({"disposition": "skip"}, "skip", None),
    ({"disposition": "unknown"}, "unknown", None),
    ({"text": " Non lo so. "}, "unknown", "Non lo so."),
    ({"text": "Skip for now."}, "skip", "Skip for now."),
    ({"text": "Cambia argomento."}, "change_topic", "Cambia argomento."),
])
def test_date_question_accepts_non_answers_without_validating_them_as_dates(
    client, auth_headers, payload, expected, original,
):
    context, question, _ = pause_for_question(client, auth_headers, ClarifyingQuestion(
        question_id=uuid4(), text="When did you move?", answer_shape="free_text",
        missing_fields=["move_in_date"], answer_format="calendar_date",
    ))
    client.app.include_router(build_reconnect_router(key=KEY))
    url = run_url(context)
    reply_url = f"{url}/questions/{question.question_id}/reply"
    owner = auth_headers()
    before = client.get(url, headers=owner).json()
    reply = {"client_reply_id": str(uuid4()), "expected_run_revision": before["run_revision"], **payload}
    foreign = client.post(reply_url, headers=auth_headers("bob"), json=reply)
    assert_private_error(foreign, 404, "unavailable")
    saved = client.post(reply_url, headers=owner, json=reply)
    assert saved.status_code == 200
    assert saved.json()["disposition"] == expected
    assert saved.json()["text"] == original
    assert client.post(reply_url, headers=owner, json=reply).json() == saved.json()
    assert client.get(url, headers=owner).json()["status"] == "running"


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
