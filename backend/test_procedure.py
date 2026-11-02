"""Reference routing. A missing fact does not pick a procedure."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from procedure import select

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


def test_s01_selects_address_change_before_and_after_the_paper():
    assert select(S01)["procedure"] == "address change"
    assert select(S01)["decision"] == "ready"
    opened = dict(S01)
    del opened["f07"]
    assert select(opened) == {"id": "R-05", "decision": "open", "procedure": "address change"}


def test_s02_selects_address_change_without_the_identity_paper():
    facts = {
        "language": "Italian",
        "f04": "via Savona 12, Milano",
        "f05": "Owner",
        "f07": "read",
        "f09": "agree",
        "age": 17,
    }
    assert select(facts) == {"id": "R-08", "decision": "ready", "procedure": "address change"}


def test_i01_missing_title_paper_stays_on_the_procedure():
    facts = dict(S01)
    facts["f07"] = "missing"
    assert select(facts) == {"id": "R-06", "decision": "not ready", "procedure": "address change"}


def test_i02_disagreement_stays_on_the_procedure():
    facts = dict(S01)
    facts["f09"] = "disagree"
    assert select(facts) == {"id": "R-07", "decision": "not ready", "procedure": "address change"}


def test_a01_asks_once_and_then_names_the_door():
    assert select({"language": "English", "question": "f02"}) == {
        "id": "R-03",
        "decision": "ask once",
        "missing": "f02",
        "procedure": None,
    }
    assert select({"language": "English", "f02": "never registered in Italy"}) == {
        "id": "R-04",
        "decision": "no case",
        "procedure": None,
        "door": "Comune di Milano service for foreigners arriving from abroad",
    }
    assert select({"language": "English", "f02": "registered in another municipality"}) == {
        "id": "R-04",
        "decision": "no case",
        "procedure": None,
        "door": "ANPR",
    }


def test_a02_asks_once_then_rejects_guest_or_another_adult():
    assert select({"language": "English", "question": "f03"}) == {
        "id": "R-03",
        "decision": "ask once",
        "missing": "f03",
        "procedure": None,
    }
    assert select({"language": "English", "f03": "guest"}) == {
        "id": "R-04",
        "decision": "no case",
        "procedure": None,
        "door": "not in this release",
    }
    assert select({"language": "English", "f05": "guest"})["door"] == "not in this release"


def test_u01_names_the_abroad_door():
    result = select({"language": "English", "f02": "never registered in Italy"})
    assert result["procedure"] is None
    assert result["door"] == "Comune di Milano service for foreigners arriving from abroad"


def test_u02_does_not_select_tari_or_a_permit_update():
    result = select(
        {
            "language": "English",
            "f03": "another adult",
            "tari": True,
            "permit": True,
        }
    )
    assert result == {
        "id": "R-04",
        "decision": "no case",
        "procedure": None,
        "door": "ANPR",
    }


def test_u03_other_language_names_no_procedure():
    facts = dict(S01)
    facts["language"] = "Turkish"
    assert select(facts) == {
        "id": "R-01",
        "decision": "no case",
        "procedure": None,
        "door": "English or Italian",
    }


def test_missing_address_does_not_pick_a_procedure():
    assert select({"language": "English", "f05": "Owner"}) == {
        "id": "f04",
        "decision": "unknown",
        "missing": "f04",
        "procedure": None,
    }


def test_contradiction_does_not_pick_a_procedure():
    result = select(
        {
            "language": "English",
            "f03": "Owner, alone",
            "f04": "Via Torino 20, Milano",
            "f05": "named tenant",
        }
    )
    assert result == {"id": "f05", "decision": "unknown", "missing": "f05", "procedure": None}


def test_second_ask_does_not_pick_a_procedure():
    result = select({"language": "English", "question": "f02", "asked": True})
    assert result == {"id": "R-03", "decision": "unknown", "missing": "f02", "procedure": None}


def test_research_question_does_not_name_a_door():
    facts = dict(S01)
    facts["deadline"] = "a question"
    assert select(facts) == {"id": "R-09", "decision": "not stated", "procedure": None}


def test_bare_excluded_door_and_outside_address_invent_nothing():
    assert select({"language": "English", "door": "excluded"}) == {
        "id": "R-02",
        "decision": "no case",
        "procedure": None,
    }
    assert select({"language": "English", "f04": "Via Roma 1, Roma", "f05": "Owner"}) == {
        "id": "R-04",
        "decision": "no case",
        "procedure": None,
    }


def test_permit_no_names_the_questura():
    facts = dict(S01)
    facts["f06"] = "No"
    assert select(facts) == {
        "id": "R-04",
        "decision": "no case",
        "procedure": None,
        "door": "Questura",
    }
