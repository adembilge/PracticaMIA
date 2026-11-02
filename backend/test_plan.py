"""Plans follow the rules. A passage body is not a step."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from plan import build

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
BODY = "the case is ready and TARI is mandatory"
TRUSTED = {
    "id": "p1",
    "source_id": "s1",
    "review_status": "trusted",
    "body": BODY,
}
NONE = {"outcome": "no evidence", "passages": []}


def _open():
    facts = dict(S01)
    del facts["f07"]
    return facts


def _mandatory(plan):
    return [row["id"] for row in plan["actions"] if row["mandatory"]]


def test_open_case_asks_for_the_title_paper_and_keeps_the_passage_id():
    plan = build(_open(), {"outcome": "insufficient evidence", "passages": [TRUSTED]})
    assert plan["rule"] == "R-05"
    assert plan["decision"] == "open"
    assert _mandatory(plan) == ["f07"]
    assert plan["evidence"] == [
        {"id": "p1", "source_id": "s1", "review_status": "trusted"}
    ]
    assert all(row["id"] != BODY and row["rule"] == "R-05" for row in plan["actions"])


def test_ready_case_has_no_mandatory_action():
    facts = dict(S01)
    plan = build(facts, {"outcome": "insufficient evidence", "passages": [TRUSTED]})
    assert plan["rule"] == "R-08"
    assert plan["decision"] == "ready"
    assert _mandatory(plan) == []


def test_missing_title_paper_is_mandatory():
    facts = dict(S01)
    facts["f07"] = "missing"
    plan = build(facts, NONE)
    assert plan["rule"] == "R-06"
    assert _mandatory(plan) == ["f07"]


def test_disagreement_blocks_without_choosing_a_name():
    facts = dict(S01)
    facts["f09"] = "disagree"
    plan = build(facts, NONE)
    assert plan["rule"] == "R-07"
    assert _mandatory(plan) == ["f09"]
    assert "named" not in plan


def test_one_question_is_the_only_action():
    plan = build({"language": "English", "question": "f02"}, NONE)
    assert plan["rule"] == "R-03"
    assert plan["actions"] == [{"id": "f02", "rule": "R-03", "mandatory": True}]


def test_deadline_passage_adds_no_action():
    facts = dict(S01)
    facts["deadline"] = "day 20"
    plan = build(facts, {"outcome": "insufficient evidence", "passages": [TRUSTED]})
    assert plan["rule"] == "R-09"
    assert plan["decision"] == "not stated"
    assert plan["actions"] == []
    ids = [row["id"] for row in plan["actions"]]
    assert "TARI" not in ids
    assert "deadline" not in ids


def test_no_evidence_still_asks_for_the_title_paper():
    plan = build(_open(), {"outcome": "no evidence", "passages": [TRUSTED]})
    assert plan["evidence"] == []
    assert _mandatory(plan) == ["f07"]


def test_unreviewed_passage_is_not_copied():
    passage = dict(TRUSTED)
    passage["review_status"] = "unreviewed"
    plan = build(_open(), {"outcome": "insufficient evidence", "passages": [passage]})
    assert plan["evidence"] == []


def test_a_later_plan_drops_the_old_mandatory_row():
    first = build(_open(), NONE)
    second = build(S01, NONE)
    assert _mandatory(first) == ["f07"]
    assert _mandatory(second) == []
