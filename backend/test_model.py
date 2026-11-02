"""A checked reply. No network and no stop."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from model import complete


def test_local_reply_does_not_call_the_transport(monkeypatch):
    monkeypatch.delenv("PAPERPILOT_MODEL", raising=False)
    calls = []

    def transport(prompt):
        calls.append(prompt)
        return {"reply": "unused"}

    assert complete("hello", transport) == {"reply": "The model is not configured."}
    assert calls == []


def test_configured_reply_may_propose_a_name_and_address(monkeypatch):
    monkeypatch.setenv("PAPERPILOT_MODEL", "configured")

    def transport(prompt):
        assert prompt == "hello"
        return {"reply": "Here.", "name": "Ada", "address": "Via Torino 20, Milano"}

    assert complete("hello", transport) == {
        "reply": "Here.",
        "name": "Ada",
        "address": "Via Torino 20, Milano",
    }


def test_stop_password_and_empty_reply_are_rejected(monkeypatch):
    monkeypatch.setenv("PAPERPILOT_MODEL", "configured")

    def stopped(_prompt):
        return {"reply": "Here.", "stop": "ready"}

    def secret(_prompt):
        return {"reply": "Here.", "password": "x"}

    def empty(_prompt):
        return {"reply": "  "}

    def door(_prompt):
        return {"reply": "Here.", "door": "ANPR"}

    with pytest.raises(ValueError):
        complete("hello", stopped)
    with pytest.raises(ValueError):
        complete("hello", secret)
    with pytest.raises(ValueError):
        complete("hello", empty)
    with pytest.raises(ValueError):
        complete("hello", door)
    with pytest.raises(ValueError):
        complete("  ", lambda _prompt: {"reply": "Here."})


def test_missing_or_failing_transport_is_not_replaced(monkeypatch):
    monkeypatch.setenv("PAPERPILOT_MODEL", "configured")
    with pytest.raises(RuntimeError, match="provider failed"):
        complete("hello")

    def down(_prompt):
        raise RuntimeError("down")

    with pytest.raises(RuntimeError, match="down"):
        complete("hello", down)


def test_unknown_provider_is_rejected(monkeypatch):
    monkeypatch.setenv("PAPERPILOT_MODEL", "remote")
    with pytest.raises(ValueError, match="unknown model provider: remote"):
        complete("hello")
