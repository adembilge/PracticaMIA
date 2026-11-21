"""Offline no-guidance worker integration: no synthetic official claims leak."""
from datetime import timedelta
from uuid import uuid4

import pytest

from app.agent.checkpoints import CheckpointState
from app.agent.contract import AnswerResult
from app.agent.preview_worker import (
    LEASE_SECONDS, MAX_STEPS_PER_INVOCATION, main, preview_unverified_step, run_preview_worker_once,
)
from app.agent.reconnect_router import build_reconnect_router
from app.agent.worker import run_worker_batch
from app.config import Settings

KEY = bytes(range(32))


def test_worker_is_disabled_without_explicit_isolated_preview_configuration():
    with pytest.raises(ValueError, match="step budget"):
        run_preview_worker_once(Settings(), max_steps=MAX_STEPS_PER_INVOCATION + 1)
    with pytest.raises(ValueError, match="explicitly enabled"):
        run_preview_worker_once(Settings(), max_steps=1)


def test_one_shot_cli_requires_both_explicit_acknowledgements():
    for args in ([], ["--once"], ["--unverified-only"], ["--once", "--unverified-only", "--max-steps", "0"]):
        with pytest.raises((SystemExit, ValueError)):
            main(args)


def test_no_guidance_adapter_never_invents_citations_or_official_handoff():
    from types import SimpleNamespace
    for language in ("en", "it"):
        message = SimpleNamespace(
            text="How do I change registered address in Milano?",
            language=language, corrects_destination=False,
        )
        state = preview_unverified_step(message, CheckpointState(next_node="load_context"))
        assert state.next_node == "identify_intent"
        # Avoid testing language routing as an official answer. The final
        # result is explicitly unverified whatever route the heuristic finds.
        result = preview_unverified_step(message, CheckpointState(next_node="find_evidence"))
        assert isinstance(result, AnswerResult)
        assert result.verification_status == "insufficient_evidence"
        assert result.citations == []
        assert result.official_channel is None
        assert result.next_action is None
        assert not result.claims
        assert ("Preview" if language == "en" else "anteprima") in result.explanation


@pytest.mark.parametrize("language", ["en", "it"])
def test_signed_conversation_runs_to_read_only_unverified_answer_without_a_case(
    client, auth_headers, language,
):
    client.app.include_router(build_reconnect_router(key=KEY))
    owner = auth_headers("alice")
    foreign = auth_headers("bob")
    question = "How can I change my address?" if language == "en" else "Come cambio residenza?"
    started = client.post("/api/v1/agent/conversations", headers=owner, json={
        "client_message_id": str(uuid4()), "text": question, "language": language,
    })
    assert started.status_code == 202, started.text
    ids = started.json()
    path = f"/api/v1/agent/threads/{ids['thread_id']}/runs/{ids['run_id']}"
    assert client.get(path, headers=owner).json()["status"] == "queued"

    executed = run_worker_batch(
        client.app.state.session_factory, key=KEY, lease_for=timedelta(seconds=LEASE_SECONDS),
        execute=preview_unverified_step, max_steps=8,
    )
    assert 2 <= executed <= 4
    response = client.get(path, headers=owner)
    assert response.status_code == 200
    saved = response.json()
    assert saved["status"] == "completed"
    assert saved["result"]["verification_status"] == "insufficient_evidence"
    assert saved["result"]["citations"] == []
    assert saved["result"]["official_channel"] is None
    assert saved["handoff"] is None
    assert client.get(path, headers=foreign).status_code == 404

    history = client.get(
        f"/api/v1/agent/threads/{ids['thread_id']}/history", headers=owner,
    )
    assert history.status_code == 200
    assert history.json()["items"][0]["user_message"] == question
    assert history.json()["items"][0]["answer"]["verification_status"] == "insufficient_evidence"
    assert run_worker_batch(
        client.app.state.session_factory, key=KEY, lease_for=timedelta(seconds=LEASE_SECONDS),
        execute=preview_unverified_step, max_steps=8,
    ) == 0


def test_unknown_worker_node_fails_before_persisted_answer():
    from types import SimpleNamespace
    with pytest.raises(ValueError, match="Unexpected"):
        preview_unverified_step(
            SimpleNamespace(language="en"),
            CheckpointState(next_node="load_context").model_copy(update={"next_node": "bad-node"}),
        )
