"""Exercise recovery at the end of a corrected-scope worker run."""

from datetime import date
from uuid import UUID, uuid4

import pytest
from psycopg.errors import AdminShutdown, UndefinedTable
from sqlalchemy.exc import OperationalError, ProgrammingError, TimeoutError

from app.agent.checkpoints import AgentRunCheckpoint, CheckpointState, RoutingCorrections, load_checkpoint
from app.agent.contract import SendMessage
from app.agent.reconnect_router import build_reconnect_router
from app.agent.run_requests import accept_message, read_run_message
from app.agent.worker import run_worker_step
from app.knowledge.search import search_approved_passages
from app.rules.engine import PROCEDURE
from test_agent_run_requests import KEY
from test_knowledge_search import FACTS, _approve, _create, _thread_context, create_scoped_case


CORRECTED_SCOPE = CheckpointState(
    next_node="find_evidence", procedure_candidates=[PROCEDURE],
    routing_corrections=RoutingCorrections(move_in_date=date(2026, 4, 2)),
)


def _start_corrected_run(client, auth_headers, *, query="residenza", language="en"):
    owner = auth_headers("bob")
    case_id = UUID(create_scoped_case(client, owner))
    intake = client.put(f"/api/v1/cases/{case_id}/intake", headers=owner, json={"facts": FACTS, "confirm": True})
    assert intake.status_code == 200
    factory = client.app.state.session_factory
    scope = _thread_context(client, case_id, "bob")
    run = {"thread_id": scope["thread_id"], "principal": scope["principal"], "key": KEY}
    with factory.begin() as db:
        accepted = accept_message(db, **run, message=SendMessage(
            client_message_id=uuid4(), text=query, language=language, case_id=case_id,
        ))
    run["run_id"] = accepted.run_id
    assert run_worker_step(factory, **run, execute=lambda *_: CORRECTED_SCOPE).status == "running"
    return factory, run, owner


def _continue(factory, run):
    return run_worker_step(factory, **run, execute=lambda *_: pytest.fail("expected the corrected evidence path"))


@pytest.mark.parametrize("persistent", [False, True])
def test_transient_catalogue_failure_gets_one_fresh_session_retry(client, auth_headers, monkeypatch, persistent):
    factory, run, owner = _start_corrected_run(client, auth_headers)
    version, digest = _create(client)
    _approve(client, version, digest)
    attempts = []

    def interrupted_search(db, **scope):
        attempts.append(db)
        if len(attempts) == 1:
            raise OperationalError("private SQL fixture", {}, AdminShutdown("private storage diagnostic"))
        if persistent:
            raise TimeoutError("private connection pool diagnostic")
        return search_approved_passages(db, **scope)

    monkeypatch.setattr("app.agent.catalogue_evidence.search_approved_passages", interrupted_search)
    snapshot = _continue(factory, run)
    assert len(attempts) == 2 and attempts[0] is not attempts[1]
    assert all(not session.in_transaction() for session in attempts)

    client.app.include_router(build_reconnect_router(key=KEY))
    url = f"/api/v1/agent/threads/{run['thread_id']}/runs/{run['run_id']}"
    page = client.get(f"{url}/events", headers=owner)
    assert page.status_code == 200
    last = page.json()["events"][-1]
    if persistent:
        assert snapshot.status == "failed" and snapshot.result is None
        assert last["type"] == "run.failed"
        assert last["code"] == "catalogue_unavailable"
        assert last["retryable"] is True and last["recovery"] == "retry_later"
        assert "private" not in page.text
        with factory() as db:
            assert db.get(AgentRunCheckpoint, str(run["run_id"])) is None
        assert _continue(factory, run) == snapshot
        assert len(attempts) == 2
        with factory() as db:
            original = read_run_message(db, **run)
        send_url = f"/api/v1/agent/threads/{run['thread_id']}/messages"
        retry = client.post(send_url, headers=owner, json=SendMessage(
            client_message_id=uuid4(), case_id=original.case_id, text=original.text, language=original.language,
        ).model_dump(mode="json"))
        assert retry.status_code == 202 and retry.json()["run_id"] != str(snapshot.run_id)
        retry_run = run | {"run_id": UUID(retry.json()["run_id"])}

        monkeypatch.setattr("app.agent.catalogue_evidence.search_approved_passages", search_approved_passages)
        assert run_worker_step(factory, **retry_run, execute=lambda *_: CORRECTED_SCOPE).status == "running"
        assert _continue(factory, retry_run).status == "running"
        with factory() as db:
            state = load_checkpoint(db, **retry_run).state
            assert state.next_node == "verify_and_respond"
            assert state.evidence_ids and all(passage.startswith(version + ":") for passage in state.evidence_ids)
        assert client.get(f"{url}/events", headers=owner).json() == page.json()
    else:
        assert snapshot.status == "running" and last["type"] == "progress.updated"
        with factory() as db:
            state = load_checkpoint(db, **run).state
            assert state.next_node == "verify_and_respond"
            assert state.evidence_ids and all(passage.startswith(version + ":") for passage in state.evidence_ids)


@pytest.mark.parametrize(("query", "language", "label"), [
    ("!", "en", "Rephrase the search"),
    ("residenza " * 13, "it", "Riformula la ricerca"),
    ("residenza", "en", "Review the case details"),
])
def test_invalid_or_unmatched_search_returns_actionable_unverified_result(client, auth_headers, monkeypatch,
                                                                       query, language, label):
    factory, run, _ = _start_corrected_run(client, auth_headers, query=query, language=language)
    calls = []

    def empty_search(_db, **scope):
        calls.append(scope["query"])
        return []

    monkeypatch.setattr("app.agent.catalogue_evidence.search_approved_passages", empty_search)
    snapshot = _continue(factory, run)
    assert snapshot.status == "completed"
    assert snapshot.result.verification_status == "insufficient_evidence"
    assert snapshot.result.citations == [] and snapshot.result.official_channel is None
    assert snapshot.result.next_action.label == label
    assert snapshot.result.next_action.operation == "provide_information"
    assert calls == ([query] if query == "residenza" else [])


def test_non_transient_storage_error_is_not_retried_or_reported_as_evidence(client, auth_headers, monkeypatch):
    factory, run, _ = _start_corrected_run(client, auth_headers)
    attempts = []

    def broken_reader(*_args, **_kwargs):
        attempts.append(1)
        raise ProgrammingError("synthetic SQL", {}, UndefinedTable("synthetic missing table"))

    monkeypatch.setattr("app.agent.catalogue_evidence.search_approved_passages", broken_reader)
    with pytest.raises(ProgrammingError):
        _continue(factory, run)
    assert len(attempts) == 1
