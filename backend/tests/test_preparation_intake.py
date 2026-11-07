"""The guided intake is a scope filter, never administrative approval."""
from app.preparation.intake import QUESTIONS, scope_intake, validate_scope_facts


def complete():
    return {q["field"]: q["expected"] for q in QUESTIONS}


def test_progresses_one_question_at_a_time_and_handles_unknown():
    facts = {}
    for index, question in enumerate(QUESTIONS):
        state = scope_intake(facts)
        assert state["status"] == "needs_information"
        assert state["answered_count"] == index
        assert state["next_question"]["field"] == question["field"]
        assert state["is_legal_assessment"] is False
        facts[question["field"]] = "unknown"
        assert scope_intake(facts)["next_question"]["field"] == question["field"]
        facts[question["field"]] = question["expected"]
    result = scope_intake(facts)
    assert result["status"] == "candidate_scope_complete"
    assert result["next_question"] is None
    assert result["is_legal_assessment"] is False


def test_each_nonmatching_category_is_only_outside_proposed_product_scope():
    for question in QUESTIONS:
        for option in question["options"]:
            if option["value"] in ("unknown", question["expected"]):
                continue
            facts = complete()
            facts[question["field"]] = option["value"]
            state = scope_intake(facts)
            assert state["status"] == "outside_first_candidate"
            assert state["excluded_by"] == question["field"]
            assert state["is_legal_assessment"] is False


def test_invalid_choices_are_rejected_not_interpreted_as_ineligibility():
    for question in QUESTIONS:
        for invalid in ("", "admin", 1, True, None, ["italian"]):
            facts = complete()
            facts[question["field"]] = invalid
            if invalid == "":
                assert scope_intake(facts)["status"] == "needs_information"
            else:
                assert scope_intake(facts)["status"] == "invalid_input"
            assert not validate_scope_facts(facts)
    assert validate_scope_facts(complete())
    assert validate_scope_facts({"housing_arrangement": "fictional_rental"})


def test_question_payloads_have_translations_without_unreviewed_legal_rules():
    for question in QUESTIONS:
        assert question["label_it"] and question["label_en"]
        assert len(question["options"]) >= 2
        for option in question["options"]:
            assert option["label_it"] and option["label_en"]
            assert option["value"]
    assert not any("required_document_types" in question for question in QUESTIONS)
