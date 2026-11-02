"""Retrieval and the rule stay apart. No database."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from graph import build
from rules import evaluate


def _state(facts, query="address change"):
    return {
        "facts": facts,
        "query": query,
        "procedure": "address change",
        "jurisdiction": "Milano",
        "language": "English",
    }


def test_retrieve_keeps_the_evidence_for_the_milan_filters():
    evidence = {"outcome": "no evidence", "passages": []}
    calls = []

    def search(query, procedure, jurisdiction, language):
        calls.append((query, procedure, jurisdiction, language))
        return evidence

    result = build(search, evaluate).invoke(_state({"language": "English"}, "where do I file"))
    assert calls == [("where do I file", "address change", "Milano", "English")]
    assert result["evidence"] is evidence


def test_evaluate_receives_the_original_facts_when_a_passage_says_ready():
    facts = {"language": "English"}
    seen = []

    def search(query, procedure, jurisdiction, language):
        return {"outcome": "insufficient evidence", "passages": [{"body": "ready"}]}

    def judge(got):
        seen.append(got)
        return {"id": "kept", "decision": "open"}

    result = build(search, judge).invoke(_state(facts))
    assert seen == [facts]
    assert result["facts"] is facts
    assert result["decision"] == {"id": "kept", "decision": "open"}


def test_a_ready_passage_does_not_flip_an_unstated_rule():
    facts = {"language": "English", "deadline": "when"}
    evidence = {
        "outcome": "insufficient evidence",
        "passages": [{"body": "The case is ready.", "review_status": "trusted"}],
    }

    def search(query, procedure, jurisdiction, language):
        return evidence

    result = build(search, evaluate).invoke(_state(facts))
    assert result["decision"] == {"id": "R-09", "decision": "not stated"}
    assert result["evidence"] == evidence


def test_no_evidence_still_decides_from_the_facts():
    facts = {"language": "English"}

    def search(query, procedure, jurisdiction, language):
        return {"outcome": "no evidence", "passages": []}

    result = build(search, evaluate).invoke(_state(facts))
    assert result["evidence"]["outcome"] == "no evidence"
    assert result["decision"] == {"id": "f04", "decision": "unknown", "missing": "f04"}
