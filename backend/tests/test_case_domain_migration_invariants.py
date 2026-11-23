"""Guard the live case-bound persistence graph during task-domain migration."""

from app.agent.case_operations import AgentCaseOperation
from app.agent.checkpoints import AgentRunCheckpoint, _checkpoint_aad
from app.agent.run_events import AgentRunEvent, _event_aad
from app.agent.run_requests import AgentRunRequest, _associated_data
from app.agent.threads import AgentThreadCase
from app.auth.tokens import Principal
from app.cases.intake_model import CaseIntake
from app.preparation.crypto import associated_data as preparation_aad
from app.preparation.models import CaseAgentTurn, CaseDocument, CasePreparation
from app.private_documents.model import PrivateCaseDocument
from app.private_documents.security import _aad as private_document_aad


def _run(case_id: str) -> AgentRunRequest:
    return AgentRunRequest(
        id="run-id",
        thread_id="thread-id",
        case_id=case_id,
        client_message_id="message-id",
        accepted_revision=7,
    )


def test_live_domain_records_still_reference_the_case_table():
    models = (
        CaseIntake,
        AgentThreadCase,
        AgentCaseOperation,
        PrivateCaseDocument,
        CasePreparation,
        CaseDocument,
        CaseAgentTurn,
    )
    for model in models:
        targets = {
            foreign_key.target_fullname
            for column in model.__table__.columns
            for foreign_key in column.foreign_keys
        }
        assert "cases.id" in targets, model.__name__


def test_run_acceptance_keeps_its_composite_thread_case_link():
    constraint = next(
        constraint
        for constraint in AgentRunRequest.__table__.foreign_key_constraints
        if constraint.name == "fk_agent_runs_linked_case"
    )
    assert [element.parent.name for element in constraint.elements] == [
        "thread_id",
        "case_id",
    ]
    assert [element.target_fullname for element in constraint.elements] == [
        "agent_thread_cases.thread_id",
        "agent_thread_cases.case_id",
    ]


def test_run_events_checkpoints_and_operation_receipts_remain_run_bound():
    for model in (AgentRunEvent, AgentRunCheckpoint):
        targets = {
            foreign_key.target_fullname
            for column in model.__table__.columns
            for foreign_key in column.foreign_keys
        }
        assert "agent_run_requests.id" in targets

    operation_targets = {
        foreign_key.target_fullname
        for column in AgentCaseOperation.__table__.columns
        for foreign_key in column.foreign_keys
    }
    assert {"agent_run_requests.id", "cases.id"} <= operation_targets


def test_case_reparenting_changes_every_case_bound_encryption_context():
    owner = Principal("alice")
    run = _run("case-a")

    assert _associated_data(run, owner.subject) != _associated_data(_run("case-b"), owner.subject)
    assert _event_aad(run, 3, owner) != _event_aad(_run("case-b"), 3, owner)
    assert _checkpoint_aad(run, owner, revision=2, event_seq=3) != _checkpoint_aad(
        _run("case-b"), owner, revision=2, event_seq=3,
    )

    assert private_document_aad("case-a", "alice", "doc-1") != private_document_aad(
        "case-b", "alice", "doc-1",
    )
    assert preparation_aad("case-a", "alice", "doc-1") != preparation_aad(
        "case-b", "alice", "doc-1",
    )


def test_private_document_encryption_context_binds_owner_and_document_identity():
    base = private_document_aad("case-a", "alice", "doc-1")
    assert base != private_document_aad("case-a", "bob", "doc-1")
    assert base != private_document_aad("case-a", "alice", "doc-2")

    preparation_base = preparation_aad("case-a", "alice", "doc-1")
    assert preparation_base != preparation_aad("case-a", "bob", "doc-1")
    assert preparation_base != preparation_aad("case-a", "alice", "doc-2")


def _primary_key_columns(model):
    return tuple(column.name for column in model.__table__.primary_key.columns)


def _foreign_key_actions(model):
    actions = {}
    for constraint in model.__table__.foreign_key_constraints:
        for element in constraint.elements:
            actions[element.target_fullname] = constraint.ondelete or element.ondelete
    return actions


def test_current_record_cardinality_is_explicit_before_domain_rename():
    from app.agent.threads import AgentThread
    from app.cases.model import CaseRecord

    # One-to-zero-or-one records: the parent identifier is also the child PK.
    assert _primary_key_columns(CaseIntake) == ("case_id",)
    assert _primary_key_columns(CasePreparation) == ("case_id",)

    # One-to-many records: each dependent has an independent stable identity.
    for model in (PrivateCaseDocument, CaseDocument, CaseAgentTurn):
        assert _primary_key_columns(model) == ("id",)
        assert "case_id" not in _primary_key_columns(model)

    # Thread/task association is many-to-many; run rows retain their own identity.
    assert _primary_key_columns(AgentThreadCase) == ("thread_id", "case_id")
    assert _primary_key_columns(AgentRunRequest) == ("id",)
    assert _primary_key_columns(AgentThread) == ("id",)
    assert _primary_key_columns(CaseRecord) == ("id",)


def test_current_cascade_edges_are_explicit_before_domain_rename():
    expected = {
        CaseIntake: {"cases.id": "CASCADE"},
        AgentThreadCase: {
            "agent_threads.id": "CASCADE",
            "cases.id": "CASCADE",
        },
        AgentRunRequest: {
            "agent_threads.id": "CASCADE",
            "agent_thread_cases.thread_id": "CASCADE",
            "agent_thread_cases.case_id": "CASCADE",
        },
        AgentRunEvent: {"agent_run_requests.id": "CASCADE"},
        AgentRunCheckpoint: {"agent_run_requests.id": "CASCADE"},
        AgentCaseOperation: {
            "agent_run_requests.id": "CASCADE",
            "cases.id": "CASCADE",
        },
        PrivateCaseDocument: {"cases.id": "CASCADE"},
        CasePreparation: {"cases.id": "CASCADE"},
        CaseDocument: {"cases.id": "CASCADE"},
        CaseAgentTurn: {"cases.id": "CASCADE"},
    }
    for model, actions in expected.items():
        assert _foreign_key_actions(model) == actions, model.__name__

