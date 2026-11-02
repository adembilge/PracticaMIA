"""The beta stays empty. A person drops the hold."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from beta import load, report


def test_the_empty_file_holds():
    lines = report(load())
    assert lines[-1] == "beta held"


def test_a_person_omits_the_hold():
    lines = report({"people": ["ada"], "feedback": [], "issues": []})
    assert "beta held" not in lines
    with pytest.raises(ValueError):
        report({"people": ["I moved house"], "feedback": [], "issues": []})
