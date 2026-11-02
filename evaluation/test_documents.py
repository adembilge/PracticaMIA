"""Each type and field is checked. There is no score."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from documents import LIMITS, report, walk

WORDS = (
    "lease",
    "ownership",
    "identity",
    "permit",
    "unknown",
    "ambiguous",
    "image",
    "review",
    "compare",
    "prepare",
)


def test_the_walk_checks_each_type_and_field():
    rows = walk()
    lines = report(rows)
    assert rows
    assert all(ok for _name, ok, _seconds in rows)
    assert "thresholds: none approved" in lines
    assert "failures: none" in lines
    assert lines[-1] == "documents ok"
    for line in LIMITS:
        assert line in lines
    for name, _ok, _seconds in rows:
        assert any(word in name for word in WORDS)
