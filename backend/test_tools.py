"""Tool contracts. A caller cannot skip approval or open another case."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from checklist import checklist
from tools import invoke

S01 = {
    "language": "English",
    "f02": "Yes",
    "f04": "Via Torino 20, Milano",
    "f05": "named tenant",
    "non_eu": True,
    "f06": "Yes",
    "f07": "read",
    "f08": "read",
    "f09": "agree",
}
SEARCH = {
    "query": "address",
    "procedure_id": "address change",
    "jurisdiction": "Milano",
    "language": "English",
}


def test_search_calls_the_injected_finder_with_the_four_filters():
    seen = []

    def search(query, procedure, jurisdiction, language):
        seen.append((query, procedure, jurisdiction, language))
        return {"outcome": "insufficient evidence", "passages": [{"id": "p1"}]}

    got = invoke("search_official_knowledge", SEARCH, caller="ada", search=search)
    assert seen == [("address", "address change", "Milano", "English")]
    assert got["tool"] == "search_official_knowledge"
    assert got["passages"] == [{"id": "p1"}]


def test_tari_returns_no_evidence_and_does_not_ask_for_unreviewed_rows():
    seen = []

    def search(*args, **kwargs):
        seen.append((args, kwargs))
        return {"outcome": "conflicting evidence", "passages": [{"review_status": "unreviewed"}]}

    payload = dict(SEARCH)
    payload["procedure_id"] = "TARI"
    got = invoke("search_official_knowledge", payload, caller="ada", search=search)
    assert seen == []
    assert got["outcome"] == "no evidence"
    assert got["passages"] == []


def test_evidence_keeps_a_trusted_passage_and_drops_the_rest():
    def evidence(source_id, passage_id):
        if passage_id == "missing":
            return None
        if passage_id == "mismatch":
            return {"id": "mismatch", "source_id": "other", "review_status": "trusted"}
        if passage_id == "unreviewed":
            return {"id": "unreviewed", "source_id": source_id, "review_status": "unreviewed"}
        return {"id": passage_id, "source_id": source_id, "review_status": "trusted", "body": "text"}

    kept = invoke(
        "get_source_evidence",
        {"source_id": "src", "passage_id": "p1"},
        caller="ada",
        evidence=evidence,
    )
    assert kept["passage"]["review_status"] == "trusted"
    assert kept["passage"]["source_id"] == "src"
    for passage_id in ("missing", "mismatch", "unreviewed"):
        got = invoke(
            "get_source_evidence",
            {"source_id": "src", "passage_id": passage_id},
            caller="ada",
            evidence=evidence,
        )
        assert got["outcome"] == "no evidence"
        assert got["passages"] == []


def test_find_procedure_returns_address_change_for_s01():
    got = invoke("find_procedure", {"user_context": S01}, caller="ada")
    assert got["tool"] == "find_procedure"
    assert got["procedure"] == "address change"


def test_evaluate_stays_not_stated_when_a_passage_says_ready():
    got = invoke(
        "evaluate_requirements",
        {
            "procedure_id": "address change",
            "user_context": {"language": "English", "deadline": "when", "body": "ready"},
        },
        caller="ada",
    )
    assert got["id"] == "R-09"
    assert got["decision"] == "not stated"


def test_checklist_is_limited_to_the_caller():
    cases = {"c1": {"person_id": "ada", "facts": S01}}
    own = invoke("generate_checklist", {"case_id": "c1"}, caller="ada", cases=cases)
    other = invoke("generate_checklist", {"case_id": "c1"}, caller="bea", cases=cases)
    assert own["items"] == checklist(S01)["items"]
    assert own["missing"] == checklist(S01)["missing"]
    assert other["items"] == []
    assert other["missing"] is None


def test_unknown_tool_and_review_status_are_rejected():
    with pytest.raises(ValueError):
        invoke("drop_table", {})
    payload = dict(SEARCH)
    payload["review_status"] = "unreviewed"
    with pytest.raises(ValueError):
        invoke("search_official_knowledge", payload, caller="ada")
