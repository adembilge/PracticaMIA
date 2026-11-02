"""Local workflows finish. There is no approved budget and no priced call."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from performance import BUDGET, COST, DB_LIMIT, OPTIMIZATION, USAGE, report, walk

NAMES = ("api", "model", "tool", "document", "database", "load")


def test_the_walk_times_each_workflow():
    rows = walk()
    lines = report(rows)
    assert [name for name, _ok, _seconds in rows] == list(NAMES)
    assert all(ok for _name, ok, _seconds in rows)
    assert all(seconds >= 0 for _name, _ok, seconds in rows)
    assert "thresholds: none approved" in lines
    assert "failures: none" in lines
    assert BUDGET in lines
    assert COST in lines
    assert USAGE in lines
    assert OPTIMIZATION in lines
    assert DB_LIMIT in lines
    assert "research: unreviewed" in lines
    assert "$" not in "\n".join(lines)
    for name in NAMES:
        assert name + " held" in lines
    assert lines[-1] == "performance ok"
