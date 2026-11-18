"""Read the confirmed intake and current review actions for a linked case."""

from dataclasses import dataclass, field
from typing import Literal, get_args
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.agent.document_context import DocumentFieldStatus, read_document_field_statuses
from app.agent.threads import AgentThread, AgentThreadCase
from app.auth.tokens import Principal
from app.cases.intake_model import CaseIntake
from app.cases.intake_schemas import IntakeFacts, describe_intake
from app.cases.model import CaseRecord
from app.cases.scope import DEMO_ANSWERS
from app.cases.workflow_service import build_workflow
from app.config import Settings
from app.rules.engine import PROCEDURE

CaseNextAction = Literal[
    "answer_scope", "confirm_intake", "consult_official", "review_sources", "review_checklist",
]


@dataclass(frozen=True)
class WorkerCaseContext:
    case_id: UUID
    user_confirmed_facts: IntakeFacts | None
    next_action: CaseNextAction | None
    open_review_action_ids: tuple[str, ...]
    document_fields: dict[str, DocumentFieldStatus] = field(default_factory=dict)


def _confirmed_facts(case: CaseRecord, intake: CaseIntake | None) -> IntakeFacts | None:
    if (
        intake is None or intake.confirmed_at is None or case.status != "provisionally_in_scope"
        or case.scope_answers != list(DEMO_ANSWERS)
    ):
        return None
    try:
        facts = IntakeFacts.model_validate(intake.facts)
    except ValidationError:
        return None
    missing = describe_intake(facts.model_dump(exclude_none=True), confirmed=True)["missing_fields"]
    return facts if not missing else None


def read_worker_case_context(
    db: Session, *, thread_id: UUID, case_id: UUID, principal: Principal,
    document_settings: Settings | None = None,
) -> WorkerCaseContext | None:
    """Project case state after checking ownership of both sides of the link."""
    row = db.execute(
        select(CaseRecord, CaseIntake)
        .join(AgentThreadCase, AgentThreadCase.case_id == CaseRecord.id)
        .join(AgentThread, AgentThread.id == AgentThreadCase.thread_id)
        .outerjoin(CaseIntake, and_(
            CaseIntake.case_id == CaseRecord.id,
            CaseIntake.owner_subject == CaseRecord.owner_subject,
        ))
        .where(
            AgentThread.id == str(thread_id), AgentThread.owner_subject == principal.subject,
            CaseRecord.id == str(case_id), CaseRecord.owner_subject == principal.subject,
        )
        .execution_options(populate_existing=True)
    ).one_or_none()
    if row is None:
        return None

    case, intake = row
    if case.procedure != PROCEDURE:
        return WorkerCaseContext(case_id, None, None, ())

    facts = _confirmed_facts(case, intake)
    workflow = build_workflow(
        db, case=case, intake=intake if facts is not None else None,
        private_documents_enabled=False, vault_key=None,
    )
    checklist = workflow["checklist"]
    return WorkerCaseContext(
        case_id=case_id,
        user_confirmed_facts=facts,
        next_action=workflow["next_action"] if workflow["next_action"] in get_args(CaseNextAction) else None,
        open_review_action_ids=tuple(
            item["id"] for item in checklist["items"] if item["id"] not in checklist["reviewed_items"]
        ),
        document_fields=read_document_field_statuses(
            db, case_id=case.id, owner=case.owner_subject, facts=facts, settings=document_settings,
        ),
    )
