"""The walk uses the existing decisions. The model is not called."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import model
from agent import report, walk


def test_the_walk_meets_the_existing_decisions():
    calls = []
    real = model.complete

    def blocked(prompt, transport=None):
        calls.append(prompt)
        return real(prompt, transport)

    model.complete = blocked
    try:
        rows, traces = walk()
        lines = report(rows, traces)
    finally:
        model.complete = real
    assert calls == []
    assert traces == []
    assert "thresholds: none approved" in lines
    assert "failures: none" in lines
    assert "tokens: 0" in lines
    assert "retrieval: p-alpha" in lines
    assert "follow: stable" in lines
    assert "agent ok" in lines
