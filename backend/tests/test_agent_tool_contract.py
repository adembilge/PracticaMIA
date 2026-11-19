import pytest
from pydantic import ValidationError

from app.agent.tool_contract import parse_tool_call, tool_result_adapter
from app.rules.engine import JURISDICTION, PROCEDURE


CASE_ID = "11111111-1111-4111-8111-111111111111"
PROPOSAL_ID = "22222222-2222-4222-8222-222222222222"
OPERATION_ID = "33333333-3333-4333-8333-333333333333"
VERSION_ID = "44444444-4444-4444-8444-444444444444"
CITATION_ID = VERSION_ID + ":0001"
SCOPE = {"procedure_id": PROCEDURE, "location_id": JURISDICTION}
CATALOGUE = frozenset({(PROCEDURE, JURISDICTION), ("other_procedure", "IT-TO-TORINO")})
CITATION = {
    "citation_id": CITATION_ID, "passage_id": CITATION_ID, "source_version_id": VERSION_ID,
    "source_id": "fixture-source", "official_url": "https://example.test/fixture",
    "publisher": "Fixture publisher", "reviewed_at": "2026-11-18T00:00:00Z", **SCOPE,
}
PASSAGE = {"citation": CITATION, "source_revision": 1, "section_path": "Fixture", "content": "Synthetic passage"}
PROPOSAL = {
    "proposal_id": PROPOSAL_ID, "case_id": CASE_ID, "field_id": "housing_basis",
    "previous_value": "guest", "proposed_value": "owner", "rationale": "Confirm the housing arrangement",
    "expected_case_revision": 1, "expires_at": "2026-11-19T00:00:00Z",
}


@pytest.mark.parametrize(("tool", "parameters", "output"), [
    ("find_procedure", {"query": "cambio di residenza", "language": "it", "location_id": JURISDICTION}, {
        "candidates": [{"scope": SCOPE, "name": "Synthetic procedure", "authority_ids": ["fixture-authority"],
                        "channels": [{"channel_id": "fixture-channel", "label": "Fixture contact",
                                      "url": "https://example.test/contact", "citation": CITATION}]}],
    }),
    ("find_evidence", {"case_id": CASE_ID, "scope": SCOPE, "query": "residenza"},
     {"status": "evidence_found", "passages": [PASSAGE]}),
    ("open_source_details", {"case_id": CASE_ID, "scope": SCOPE, "citation_id": CITATION_ID},
     {"status": "evidence_found", "passages": [PASSAGE]}),
    ("read_case_context", {"case_id": CASE_ID}, {
        "case_id": CASE_ID, "user_confirmed_facts": {"housing_basis": "guest"},
        "next_action": "review_checklist", "open_review_action_ids": ["fixture-action"],
    }),
    ("propose_case_update", {"case_id": CASE_ID, "expected_case_revision": 1, "rationale": "Please review",
                             "change": {"kind": "set_intake_fact", "facts": {"housing_basis": "owner"}}},
     {"proposal": PROPOSAL}),
    ("apply_approved_update", {"case_id": CASE_ID, "proposal_id": PROPOSAL_ID,
                               "expected_case_revision": 1, "client_operation_id": OPERATION_ID},
     {"case_id": CASE_ID, "proposal_id": PROPOSAL_ID, "operation_id": OPERATION_ID, "case_revision": 2}),
])
def test_tool_request_and_result_round_trip_and_reject_extra_fields(tool, parameters, output):
    args = {"tool": tool, **parameters}
    call = parse_tool_call(args, catalogue_scopes=CATALOGUE)
    assert parse_tool_call(call.model_dump(mode="json", exclude_unset=True), catalogue_scopes=CATALOGUE) == call

    result = tool_result_adapter.validate_python({"tool": tool, **output})
    assert tool_result_adapter.validate_json(result.model_dump_json()) == result
    with pytest.raises(ValidationError, match="extra_forbidden"):
        parse_tool_call({**args, "owner_subject": "invented-owner"}, catalogue_scopes=CATALOGUE)
    with pytest.raises(ValidationError, match="extra_forbidden"):
        tool_result_adapter.validate_python({"tool": tool, **output, "extra": True})


def test_only_known_catalogue_location_and_procedure_location_pairs_are_accepted():
    find = {"tool": "find_procedure", "query": "residenza", "language": "it"}
    assert parse_tool_call(find, catalogue_scopes=frozenset()).location_id is None
    with pytest.raises(ValueError, match="Unknown catalogue location"):
        parse_tool_call({**find, "location_id": "IT-XX-UNKNOWN"}, catalogue_scopes=CATALOGUE)

    calls = (
        {"tool": "find_evidence", "case_id": CASE_ID, "query": "residenza"},
        {"tool": "open_source_details", "case_id": CASE_ID, "citation_id": CITATION_ID},
    )
    for call in calls:
        for scope in ({**SCOPE, "procedure_id": "invented"}, {**SCOPE, "location_id": "IT-TO-TORINO"}):
            with pytest.raises(ValueError, match="Unknown procedure and location combination"):
                parse_tool_call({**call, "scope": scope}, catalogue_scopes=CATALOGUE)
        with pytest.raises(ValidationError, match="extra_forbidden"):
            parse_tool_call({**call, "scope": {**SCOPE, "source_id": "invented"}}, catalogue_scopes=CATALOGUE)


def test_limits_passage_ids_and_case_changes_are_validated_at_the_boundary():
    find = {"tool": "find_evidence", "case_id": CASE_ID, "query": "residenza", "scope": SCOPE}
    for override in ({"limit": "5"}, {"limit": 11}, {"query": "@!"}, {"query": "a " * 13}):
        with pytest.raises(ValidationError):
            parse_tool_call({**find, **override}, catalogue_scopes=CATALOGUE)
    with pytest.raises(ValidationError):
        parse_tool_call({
            "tool": "open_source_details", "case_id": CASE_ID, "scope": SCOPE, "citation_id": "unbound-passage",
        }, catalogue_scopes=CATALOGUE)
    with pytest.raises(ValidationError):
        parse_tool_call({"tool": "submit_application"}, catalogue_scopes=CATALOGUE)

    propose = {"tool": "propose_case_update", "case_id": CASE_ID, "expected_case_revision": 1, "rationale": "Review"}
    mark = {"kind": "mark_checklist_item", "item_id": "fixture-action", "reviewed": True}
    assert parse_tool_call({**propose, "change": mark}, catalogue_scopes=CATALOGUE).change.reviewed is True
    for change in (
        {**mark, "reviewed": 1},
        {"kind": "set_intake_fact", "facts": {"unknown_field": True}},
        {"kind": "set_intake_fact", "facts": {"housing_basis": "owner", "move_in_date": "2026-11-18"}},
        {"kind": "set_intake_fact", "facts": {"move_in_date": "2026-02-30"}},
        {"kind": "set_intake_fact", "facts": {"housing_basis": None}},
    ):
        with pytest.raises(ValidationError):
            parse_tool_call({**propose, "change": change}, catalogue_scopes=CATALOGUE)


def test_tool_outputs_preserve_exact_source_scope_and_reject_inconsistent_results():
    channel = {"channel_id": "fixture", "label": "Fixture", "url": "https://example.test/contact",
               "citation": {**CITATION, "location_id": "IT-TO-TORINO"}}
    with pytest.raises(ValidationError, match="Channel evidence must match"):
        tool_result_adapter.validate_python({"tool": "find_procedure", "candidates": [
            {"scope": SCOPE, "name": "Synthetic procedure", "channels": [channel]},
        ]})
    with pytest.raises(ValidationError):
        tool_result_adapter.validate_python({"tool": "open_source_details", "status": "evidence_found",
                                             "passages": [PASSAGE, PASSAGE]})
    with pytest.raises(ValidationError, match="Only a successful evidence result"):
        tool_result_adapter.validate_python({"tool": "find_evidence", "status": "insufficient_evidence",
                                             "passages": [PASSAGE]})
    with pytest.raises(ValidationError, match="Only an information gap"):
        tool_result_adapter.validate_python({"tool": "find_evidence", "status": "needs_information"})
