"""Exercise the disabled document and form boundary with owned synthetic cases."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.agent.checkpoints import CheckpointState
from app.agent.tool_access import ToolAccessDenied
from app.agent.tool_contract import parse_tool_call, tool_result_adapter
from app.agent.tool_execution import ToolCapabilityUnavailable, ToolExecutionDenied, check_tool_execution
from app.agent.worker import run_worker_step
from app.rules.engine import JURISDICTION, PROCEDURE
from test_agent_run_requests import ALICE, BOB, KEY
from test_agent_tool_access import tool_run  # noqa: F401 - shared owned-run fixture


SCOPES = frozenset({(PROCEDURE, JURISDICTION)})


def _calls(case_id):
    return (
        {"tool": "read_document_evidence", "case_id": case_id, "document_id": uuid4(), "field_ids": ["move_in_date"]},
        {"tool": "find_applicable_form", "case_id": case_id,
         "scope": {"procedure_id": PROCEDURE, "location_id": JURISDICTION}},
        {"tool": "prepare_form_draft", "case_id": case_id, "form_version_id": uuid4(),
         "mapping_version_id": uuid4(), "expected_case_revision": 2},
    )


def test_extension_calls_require_bounded_identifiers_and_known_form_scope():
    document, form, draft = _calls(uuid4())
    for payload in (document, form, draft):
        parsed = parse_tool_call(payload, catalogue_scopes=SCOPES)
        assert parsed.tool == payload["tool"]
        with pytest.raises(ValidationError, match="extra_forbidden"):
            parse_tool_call({**payload, "enabled": True}, catalogue_scopes=SCOPES)

    for fields in ([], ["move_in_date"] * 2, [f"field_{i}" for i in range(13)], ["raw document content"]):
        with pytest.raises(ValidationError):
            parse_tool_call({**document, "field_ids": fields}, catalogue_scopes=SCOPES)
    with pytest.raises(ValueError, match="Unknown procedure and location combination"):
        parse_tool_call(form, catalogue_scopes=frozenset())
    with pytest.raises(ValidationError):
        parse_tool_call({**draft, "form_version_id": "latest"}, catalogue_scopes=SCOPES)
    with pytest.raises(ValidationError):
        parse_tool_call({**draft, "expected_case_revision": "2"}, catalogue_scopes=SCOPES)


def test_owned_extension_calls_have_an_unavailable_result_and_no_completion_payload(client, tool_run):
    scope, _, case_id, other_owned_case, _ = tool_run
    factory = client.app.state.session_factory
    calls = [parse_tool_call(payload, catalogue_scopes=SCOPES) for payload in _calls(case_id)]
    with factory() as db, pytest.raises(ToolExecutionDenied, match="require a running run"):
        check_tool_execution(db, **scope, principal=ALICE, call=calls[0])

    assert run_worker_step(
        factory, **scope, principal=ALICE, key=KEY,
        execute=lambda *_: CheckpointState(next_node="choose_next_step"),
    ).status == "running"
    with factory() as db:
        for call in calls:
            with pytest.raises(ToolAccessDenied, match="Tool scope unavailable"):
                check_tool_execution(db, **scope, principal=BOB, call=call)
            with pytest.raises(ToolAccessDenied, match="Tool scope unavailable"):
                check_tool_execution(db, **scope, principal=ALICE, call=call.model_copy(
                    update={"case_id": other_owned_case},
                ))
            with pytest.raises(ToolCapabilityUnavailable) as refused:
                check_tool_execution(db, **scope, principal=ALICE, call=call)
            expected = {"tool": call.tool, "status": "unavailable", "reason": "capability_disabled"}
            assert refused.value.result.model_dump() == expected
            assert tool_result_adapter.validate_python(expected) == refused.value.result
            for fabricated in (
                {"status": "completed"}, {"status": "draft_ready"}, {"draft_id": str(uuid4())},
                {"evidence": [{"field_id": "move_in_date", "text": "synthetic content"}]},
                {"operation_id": str(uuid4())}, {"submitted": True},
            ):
                with pytest.raises(ValidationError):
                    tool_result_adapter.validate_python({**expected, **fabricated})
