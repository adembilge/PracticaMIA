"""Reuse one confirmed category without bringing another case's intake into a run."""

from dataclasses import replace
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.agent.candidate_resolution import choose_candidate_step
from app.agent.case_context import read_shared_citizenship
from app.agent.checkpoints import load_checkpoint
from app.agent.contract import SendMessage
from app.agent.run_events import read_run_events
from app.agent.run_requests import accept_message
from app.agent.threads import AgentThreadCase
from app.agent.worker import run_worker_step
from app.cases.intake_model import CaseIntake
from app.cases.model import CaseRecord
from app.knowledge.service_areas import CaseLocation
from app.rules.engine import JURISDICTION
from test_agent_case_selection import _no_routing, _read_question, _resume_case, _run, _select
from test_agent_clarification_context import ASSIGNMENT_REQUIRING_DATE, INPUTS, STATE
from test_private_document_intelligence import FACTS, SCOPE


def _scope(client, owner, case):
    path = f"/api/v1/cases/{case}"
    assert client.patch(path + "/scope", headers=owner, json={"answers": SCOPE}).status_code == 200
    return path


def _intake(client, owner, case, *, facts=FACTS, confirm=True):
    path = _scope(client, owner, case)
    response = client.put(f"/api/v1/conversations/tasks/{case}/intake", headers=owner, json={"facts": facts, "confirm": confirm})
    assert response.status_code == 200, response.text


def _choose(message, state, **overrides):
    assignment = replace(ASSIGNMENT_REQUIRING_DATE, required_circumstances=(
        ("housing_basis", "registered_private_rental"), ("citizenship_class", "italian"),
    ))
    inputs = INPUTS | {
        "case_locations": {"destination": CaseLocation(municipality_id=JURISDICTION, confirmed=True)},
        "assignments": (assignment,),
    }
    return choose_candidate_step(message, state, **(inputs | overrides))


def test_selected_case_run_reuses_citizenship_but_asks_for_its_own_date_and_housing(client, auth_headers):
    factory, context, url, source, target, _ = _run(client, "What about the other application?", bind=True)
    owner = auth_headers("alice")
    _intake(client, owner, source)
    target_path = _scope(client, owner, target)
    _resume_case(factory, context)
    pending, question = _read_question(client, url, owner)
    _, _, reply = _select(client, url, owner, pending, question, target)
    assert reply.status_code == 200
    assert run_worker_step(factory, **context, execute=_no_routing).selected_case.case_id == target

    with factory.begin() as db:
        accepted = accept_message(
            db, thread_id=context["thread_id"], principal=context["principal"], key=context["key"],
            message=SendMessage(client_message_id=uuid4(), language="en", text="Residence change", case_id=target),
        )
    assert accepted.outcome == "accepted"
    context["run_id"] = accepted.run_id
    run_worker_step(factory, **context, execute=lambda *_: STATE)

    def choose(message, state):
        assert message.case_context.case_id == target
        assert message.case_context.user_confirmed_facts is None
        assert message.case_context.document_fields == {}
        assert message.case_context.shared_citizenship_class == "italian"
        return _choose(message, state)

    paused = run_worker_step(factory, **context, execute=choose)
    target_url = f"/api/v1/agent/threads/{context['thread_id']}/runs/{accepted.run_id}"
    _, question = _read_question(client, target_url, owner)
    assert paused.status == "waiting_for_information"
    assert question["missing_fields"] == ["move_in_date", "housing_basis"]
    assert FACTS["move_in_date"] not in question["text"]
    assert client.get(target_url + "/events", headers=auth_headers("bob")).status_code == 404
    intake = client.get(f"/api/v1/conversations/tasks/{target}/intake", headers=owner).json()
    assert not intake["confirmed"] and not intake["facts"]


@pytest.mark.parametrize("scenario", [
    "archived-source", "draft-source", "unlinked-source", "foreign-source", "conflicting-sources",
    "archived-target", "target-draft", "target-other-household", "other-procedure",
])
def test_shared_citizenship_requires_current_confirmation_and_equal_owner_scope(client, auth_headers, scenario):
    factory, context, _, target, source, other = _run(client, "Residence change", bind=True)
    owner = auth_headers("alice")
    _scope(client, owner, target)
    _intake(client, owner, source, confirm=scenario != "draft-source")
    if scenario == "conflicting-sources":
        _intake(client, owner, other, facts=FACTS | {"citizenship_class": "non_italian"})
    if scenario in ("target-draft", "target-other-household"):
        facts = {"citizenship_class": "non_italian"} if scenario == "target-draft" else {
            "household_scope": "joining_household",
        }
        _intake(client, owner, target, facts=facts, confirm=False)

    with factory.begin() as db:
        if scenario == "archived-source":
            db.get(CaseRecord, str(source)).archived_at = datetime.now(timezone.utc)
        if scenario == "archived-target":
            db.get(CaseRecord, str(target)).archived_at = datetime.now(timezone.utc)
        if scenario == "unlinked-source":
            db.delete(db.get(AgentThreadCase, (str(context["thread_id"]), str(source))))
        if scenario == "foreign-source":
            db.get(CaseRecord, str(source)).owner_subject = "bob"
            db.get(CaseIntake, str(source)).owner_subject = "bob"
        if scenario == "other-procedure":
            db.get(CaseRecord, str(target)).procedure = "other-procedure"
        db.flush()
        assert read_shared_citizenship(
            db, thread_id=context["thread_id"], case_id=target, principal=context["principal"],
        ) is None


def test_worker_discards_routing_if_a_confirmed_source_is_archived_during_computation(client, auth_headers):
    factory, context, _, target, source, _ = _run(client, "Residence change", bind=True)
    owner = auth_headers("alice")
    _scope(client, owner, target)
    _intake(client, owner, source)
    started = run_worker_step(factory, **context, execute=lambda *_: STATE)

    def archive_source(message, state):
        assert message.case_context.shared_citizenship_class == "italian"
        result = _choose(message, state)
        changed = client.patch(f"/api/v1/cases/{source}/archive", headers=owner, json={"archived": True})
        assert changed.status_code == 200
        return result

    assert run_worker_step(factory, **context, execute=archive_source) is None
    with factory.begin() as db:
        last = load_checkpoint(db, **context)
        assert last.event_seq == started.last_event_seq
    paused = run_worker_step(factory, **context, execute=_choose)
    with factory.begin() as db:
        [event] = read_run_events(db, **context, after_seq=paused.last_event_seq - 1).events
    assert set(event.question.missing_fields) == {"move_in_date", "housing_basis", "citizenship_class"}


def test_conflicting_current_statement_requires_a_bound_citizenship_reply(client, auth_headers):
    factory, context, url, target, source, _ = _run(client, "I am not an Italian citizen.", bind=True)
    owner = auth_headers("alice")
    target_path = _scope(client, owner, target)
    _intake(client, owner, source)
    run_worker_step(factory, **context, execute=lambda *_: STATE)

    def choose(message, state):
        return _choose(message, state, confirmed_dates={"move_in_date": date(2026, 2, 1)},
                       confirmed_circumstances={"housing_basis": "registered_private_rental"})

    run_worker_step(factory, **context, execute=choose)
    pending, question = _read_question(client, url, owner)
    assert question["missing_fields"] == ["citizenship_class"]
    assert "conflicting information" in question["text"]
    reply = client.post(f"{url}/questions/{question['question_id']}/reply", headers=owner, json={
        "client_reply_id": str(uuid4()), "expected_run_revision": pending["run_revision"], "text": "Italian",
    })
    assert reply.status_code == 200
    resumed = run_worker_step(factory, **context, execute=choose)
    assert resumed.status == "running"
    with factory.begin() as db:
        last = load_checkpoint(db, **context)
    assert last.state.next_node == "find_evidence"
    assert last.state.routing_corrections.citizenship_class == "italian"
    assert client.get(f"/api/v1/conversations/tasks/{target}/intake", headers=owner).json()["facts"] == {}
