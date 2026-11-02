"""Each privacy boundary holds. There is no score and no legal review."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from privacy import LEGAL, LIMIT_LINE, REMEDIATION, report, walk

NAMES = (
    "account",
    "authorization",
    "file",
    "session",
    "input",
    "secret",
    "log",
    "deletion",
    "model",
)


def test_the_walk_holds_every_boundary():
    rows = walk()
    lines = report(rows)
    assert [name for name, _ok, _seconds in rows] == list(NAMES)
    assert all(ok for _name, ok, _seconds in rows)
    assert "thresholds: none approved" in lines
    assert "failures: none" in lines
    assert "blocking: none" in lines
    assert REMEDIATION in lines
    assert LIMIT_LINE in lines
    assert LEGAL in lines
    assert "research: unreviewed" in lines
    for name in NAMES:
        assert name + " held" in lines
    assert lines[-1] == "privacy ok"
