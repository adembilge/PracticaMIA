"""Reference lists. A missing paper is the one gap."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from checklist import checklist

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

READY = {
    "items": [
        {"id": "f07", "state": "done"},
        {"id": "f08", "state": "done"},
        {"id": "f09", "state": "done"},
    ],
    "missing": None,
}

EMPTY = {"items": [], "missing": None}


def test_s01_ready_list():
    assert checklist(S01) == READY


def test_s02_has_no_identity_row():
    facts = {
        "language": "Italian",
        "f04": "via Savona 12, Milano",
        "f05": "Owner",
        "f07": "read",
        "f09": "agree",
        "age": 17,
    }
    assert checklist(facts) == {
        "items": [
            {"id": "f07", "state": "done"},
            {"id": "f09", "state": "done"},
        ],
        "missing": None,
    }


def test_i01_missing_title_paper_is_the_gap():
    facts = dict(S01)
    facts["f07"] = "missing"
    assert checklist(facts) == {
        "items": [
            {"id": "f07", "state": "missing"},
            {"id": "f08", "state": "done"},
            {"id": "f09", "state": "waiting"},
        ],
        "missing": "f07",
    }
    facts["f07"] = "unreadable"
    assert checklist(facts)["items"][0] == {"id": "f07", "state": "blocked"}
    assert checklist(facts)["missing"] == "f07"


def test_i02_disagreement_blocks_only_the_comparison():
    facts = dict(S01)
    facts["f09"] = "disagree"
    blocked = checklist(facts)
    assert blocked["items"][0] == {"id": "f07", "state": "done"}
    assert blocked["items"][1] == {"id": "f08", "state": "done"}
    assert blocked["items"][2] == {"id": "f09", "state": "blocked"}
    assert blocked["missing"] == "f09"
    facts["named"] = True
    assert checklist(facts) == READY


def test_a01_and_a02_build_no_list():
    assert checklist({"language": "English", "question": "f02"}) == EMPTY
    assert checklist({"language": "English", "question": "f03"}) == EMPTY
    assert checklist({"language": "English", "question": "f02", "asked": True}) == EMPTY


def test_u01_u02_and_u03_build_no_list():
    assert checklist({"language": "English", "f02": "never registered in Italy"}) == EMPTY
    assert checklist({"language": "English", "f03": "another adult", "tari": True}) == EMPTY
    facts = dict(S01)
    facts["language"] = "Turkish"
    assert checklist(facts) == EMPTY


def test_reading_the_title_paper_moves_only_that_row():
    opened = dict(S01)
    opened["f07"] = "missing"
    before = checklist(opened)
    assert before["items"][0] == {"id": "f07", "state": "missing"}
    assert before["items"][1] == {"id": "f08", "state": "done"}
    opened["f07"] = "read"
    after = checklist(opened)
    assert after == READY
    assert after["items"][1] == before["items"][1]


def test_deadline_on_a_ready_story_leaves_the_list():
    facts = dict(S01)
    facts["deadline"] = "a question"
    assert checklist(facts) == READY
