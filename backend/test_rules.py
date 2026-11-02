"""Reference scenarios. A missing fact is not a no."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rules import evaluate

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


def test_s01_ready_and_open_before_the_paper():
    assert evaluate(S01) == {"id": "R-08", "decision": "ready"}
    opened = dict(S01)
    del opened["f07"]
    assert evaluate(opened) == {"id": "R-05", "decision": "open"}
    unread = dict(S01)
    unread["f08"] = "unreadable"
    assert evaluate(unread) == {"id": "f08", "decision": "not ready"}


def test_s02_ready_without_identity_paper():
    facts = {
        "language": "Italian",
        "f04": "via Savona 12, Milano",
        "f05": "Owner",
        "f07": "read",
        "f09": "agree",
        "age": 17,
    }
    assert evaluate(facts) == {"id": "R-08", "decision": "ready"}


def test_i01_missing_title_paper():
    facts = dict(S01)
    facts["f07"] = "missing"
    assert evaluate(facts) == {"id": "R-06", "decision": "not ready"}
    facts["f07"] = "failed"
    assert evaluate(facts) == {"id": "R-06", "decision": "not ready"}


def test_i02_disagreement_is_not_a_guess():
    facts = dict(S01)
    facts["f09"] = "disagree"
    assert evaluate(facts) == {"id": "R-07", "decision": "not ready"}
    facts["named"] = True
    assert evaluate(facts) == {"id": "R-08", "decision": "ready"}
    unnamed = dict(S01)
    del unnamed["f09"]
    assert evaluate(unnamed) == {"id": "f09", "decision": "unknown", "missing": "f09"}


def test_a01_asks_once():
    assert evaluate({"language": "English", "question": "f02"}) == {
        "id": "R-03",
        "decision": "ask once",
        "missing": "f02",
    }
    assert evaluate({"language": "English", "f02": "never registered in Italy"}) == {
        "id": "R-04",
        "decision": "no case",
    }


def test_a02_asks_once_then_excludes_a_guest():
    assert evaluate({"language": "English", "question": "f03"}) == {
        "id": "R-03",
        "decision": "ask once",
        "missing": "f03",
    }
    assert evaluate({"language": "English", "f03": "guest"}) == {
        "id": "R-04",
        "decision": "no case",
    }


def test_u01_excluded_door():
    assert evaluate({"language": "English", "door": "excluded"}) == {
        "id": "R-02",
        "decision": "no case",
    }


def test_u02_another_adult():
    assert evaluate({"language": "English", "f03": "another adult"}) == {
        "id": "R-04",
        "decision": "no case",
    }


def test_u03_other_language_ignores_the_story():
    facts = dict(S01)
    facts["language"] = "Turkish"
    assert evaluate(facts) == {"id": "R-01", "decision": "no case"}


def test_research_question_is_not_stated():
    facts = dict(S01)
    facts["deadline"] = "a question"
    assert evaluate(facts) == {"id": "R-09", "decision": "not stated"}


def test_missing_address_is_unknown():
    assert evaluate({"language": "English", "f05": "Owner"}) == {
        "id": "f04",
        "decision": "unknown",
        "missing": "f04",
    }
    assert evaluate({"language": "English", "f04": "Via Roma 1, Roma", "f05": "Owner"}) == {
        "id": "R-04",
        "decision": "no case",
    }


def test_contradiction_does_not_pick_a_title():
    result = evaluate(
        {
            "language": "English",
            "f03": "Owner, alone",
            "f04": "Via Torino 20, Milano",
            "f05": "named tenant",
        }
    )
    assert result == {"id": "f05", "decision": "unknown", "missing": "f05"}


def test_second_ask_is_refused():
    result = evaluate({"language": "English", "question": "f02", "asked": True})
    assert result == {"id": "R-03", "decision": "unknown", "missing": "f02"}


def test_permit_no_excludes():
    facts = dict(S01)
    facts["f06"] = "No"
    del facts["f07"]
    assert evaluate(facts) == {"id": "R-04", "decision": "no case"}
