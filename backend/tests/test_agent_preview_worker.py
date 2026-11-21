"""Preview worker configuration and case-free LangGraph contract tests."""
from uuid import uuid4

import pytest

from app.agent.chat_graph import build_chat_executor
from app.agent.checkpoints import CheckpointState
from app.agent.worker import RequestClarification
from app.config import Settings
from app.agent.preview_worker import MAX_STEPS_PER_INVOCATION, main, run_preview_worker_once
from app.agent.run_requests import StoredMessage


def test_worker_is_disabled_without_explicit_isolated_preview_configuration():
    with pytest.raises(ValueError, match="step budget"):
        run_preview_worker_once(Settings(), max_steps=MAX_STEPS_PER_INVOCATION + 1)
    with pytest.raises(ValueError, match="explicitly enabled"):
        run_preview_worker_once(Settings(), max_steps=1)


def test_one_shot_cli_requires_both_explicit_acknowledgements():
    for args in ([], ["--once"], ["--unverified-only"], ["--once", "--unverified-only", "--max-steps", "0"]):
        with pytest.raises((SystemExit, ValueError)):
            main(args)


def test_chat_graph_starts_from_one_message_without_a_case_or_case_picker(client):
    execute = build_chat_executor(client.app.state.session_factory, catalogue_names=())
    message = StoredMessage(
        text="How can I change my address?",
        language="en",
        case_id=None,
    )
    result = execute(message, CheckpointState(next_node="load_context"))
    assert isinstance(result, RequestClarification)
    assert result.question.missing_fields == ["procedure"]
    assert "case" not in result.question.text.casefold()


def test_chat_graph_fails_closed_if_a_legacy_case_link_is_passed(client):
    execute = build_chat_executor(client.app.state.session_factory, catalogue_names=())
    message = StoredMessage(
        text="How can I change my address?",
        language="en",
        case_id=uuid4(),
    )
    with pytest.raises(ValueError, match="case-linked"):
        execute(message, CheckpointState(next_node="load_context"))


def test_unknown_worker_node_fails_before_a_result_is_published(client):
    execute = build_chat_executor(client.app.state.session_factory, catalogue_names=())
    message = StoredMessage(text="Question", language="en", case_id=None)
    with pytest.raises((KeyError, ValueError)):
        execute(message, CheckpointState(next_node="bad-node"))
