"""Each attack stays off the stop. There is no score."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adversarial import MITIGATION, report, walk

NAMES = (
    "document injection",
    "manipulated webpage",
    "misleading request",
    "tool abuse",
)


def test_the_walk_holds_every_attack():
    rows = walk()
    lines = report(rows)
    assert [name for name, _ok, _seconds in rows] == list(NAMES)
    assert all(ok for _name, ok, _seconds in rows)
    assert "thresholds: none approved" in lines
    assert "failures: none" in lines
    assert "findings: none" in lines
    assert MITIGATION in lines
    assert "critical: none" in lines
    assert "research: unreviewed" in lines
    assert "model: local" in lines
    for name in NAMES:
        assert name + " held" in lines
    assert lines[-1] == "adversarial ok"
