"""A failure alerts. A body is refused."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from monitor import alert, record


def test_a_failure_alerts_and_a_body_is_refused():
    assert alert("retrieval") == ["alert: retrieval"]
    for bad in ("the user moved house", "/tmp/upload", "password"):
        with pytest.raises(ValueError):
            record(bad)
