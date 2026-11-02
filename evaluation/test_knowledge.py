"""The summary names a failure and does not invent a threshold."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from knowledge import summarize


def test_passing_summary_ends_in_knowledge_ok():
    lines = summarize(
        [
            ("rag", True, 0.1),
            ("rules", True, 0.2),
            ("retrieval", True, 1.5),
        ]
    )
    assert lines == [
        "rag ok 0.100",
        "rules ok 0.200",
        "retrieval ok 1.500",
        "thresholds: none approved",
        "failures: none",
        "knowledge ok",
    ]


def test_failed_row_omits_knowledge_ok():
    lines = summarize(
        [
            ("rag", True, 0.1),
            ("rules", False, 0.2),
        ]
    )
    assert lines[-1] == "failures: rules"
    assert "thresholds: none approved" in lines
    assert "knowledge ok" not in lines
