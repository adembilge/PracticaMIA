"""The release decision stays held. There is no go."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from release import report


def test_the_walk_holds_and_does_not_go():
    lines = report()
    assert "go" not in lines
    assert lines[-1] == "decision: held"
