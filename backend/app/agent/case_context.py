"""Read the confirmed intake and current review actions for a linked case."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, get_args
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.agent.contract import DocumentFieldStatus
from app.agent.document_context import read_document_field_statuses
from app.agent.proposal_freshness import case_proposal_fingerprint, case_snapshot_query
from app.agent.threads import AgentThread, AgentThreadCase, active_case_links
from app.auth.tokens import Principal
from app.cases.intake_model import CaseIntake
from app.cases.intake_schemas import IntakeFacts, KnownCitizenship, describe_intake
from app.cases.model import CaseRecord
from app.cases.scope import FIRST_ROUTE_SCOPE_ANSWERS
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
    proposal_case_fingerprint: str | None = None
    checklist_evidence_ids: dict[str, tuple[str, ...]] = field(default_factory=dict)
    shared_citizenship_class: KnownCitizenship | None = None
    intake_confirmed_at: datetime | None = None

    @property
    def matches_first_milan_route(self) -> bool:
        return self.user_confirmed_facts is not None and describe_intake(
            self.user_confirmed_facts.model_dump(exclude_none=True), confirmed=True,
        )["first_scenario_match"]


def _confirmed_facts(case: CaseRecord, intake: CaseIntake | None) -> IntakeFacts | None:
    if (
        intake is None or intake.confirmed_at is None or case.archived_at is not None
        or case.status != "provisionally_in_scope"
        or case.scope_answers != list(FIRST_ROUTE_SCOPE_ANSWERS)
    ):
        return None
    try:
        facts = IntakeFacts.model_validate(intake.facts)
    except ValidationError:
        return None
    missing = describe_intake(facts.model_dump(exclude_none=True), confirmed=True)["missing_fields"]
    return facts if not missing else None


def read_shared_citizenship(
    db: Session, *, thread_id: UUID, case_id: UUID, principal: Principal,
) -> KnownCitizenship | None:
    """Read the agreed citizenship category from confirmed, individual cases in this thread."""
    target_id = str(case_id)
    rows = db.execute(
        active_case_links(thread_id, principal).outerjoin(CaseIntake, and_(
            CaseIntake.case_id == CaseRecord.id, CaseIntake.owner_subject == CaseRecord.owner_subject,
        )).add_columns(CaseIntake).where(
            CaseRecord.procedure == PROCEDURE,
            CaseRecord.status == "provisionally_in_scope",
            or_(CaseRecord.id == target_id, CaseIntake.confirmed_at.is_not(None)),
        )
    )
    target_allows_reuse = False
    shared = None
    for case, intake in rows:
        if case.id == target_id:
            if case.scope_answers != list(FIRST_ROUTE_SCOPE_ANSWERS):
                return None
            try:
                draft = IntakeFacts.model_validate(intake.facts) if intake is not None else IntakeFacts()
            except ValidationError:
                return None
            if draft.citizenship_class is not None or draft.household_scope not in (
                None, "individual_no_aggregation",
            ):
                return None
            target_allows_reuse = True
            continue
        facts = _confirmed_facts(case, intake)
        if facts is None or facts.household_scope != "individual_no_aggregation":
            continue
        citizenship = facts.citizenship_class
        if citizenship in ("italian", "non_italian"):
            if shared is not None and citizenship != shared:
                return None
            shared = citizenship
    return shared if target_allows_reuse else None


def read_worker_case_context(
    db: Session, *, thread_id: UUID, case_id: UUID, principal: Principal,
    document_settings: Settings | None = None,
    lock_case: bool = False,
) -> WorkerCaseContext | None:
    """Project case state after checking ownership of both sides of the link."""
    query = (
        case_snapshot_query(str(case_id), principal.subject)
        .join(AgentThreadCase, AgentThreadCase.case_id == CaseRecord.id)
        .join(AgentThread, AgentThread.id == AgentThreadCase.thread_id)
        .where(
            AgentThread.id == str(thread_id), AgentThread.owner_subject == principal.subject,
        )
    )
    if lock_case:
        # Take the intake snapshot in a new statement after any concurrent writer commits.
        locked_id = db.scalar(query.with_only_columns(CaseRecord.id).with_for_update(read=True, of=CaseRecord))
        if locked_id is None:
            return None
    row = db.execute(query).one_or_none()
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
        intake_confirmed_at=intake.confirmed_at if facts is not None and intake is not None else None,
        next_action=workflow["next_action"] if workflow["next_action"] in get_args(CaseNextAction) else None,
        open_review_action_ids=tuple(
            item["id"] for item in checklist["items"] if item["id"] not in checklist["reviewed_items"]
        ),
        document_fields=read_document_field_statuses(
            db, case_id=case.id, owner=case.owner_subject, facts=facts, settings=document_settings,
        ),
        proposal_case_fingerprint=case_proposal_fingerprint(case, intake),
        checklist_evidence_ids={
            item["id"]: tuple(ref["citation_id"] for ref in item["evidence"])
            for item in checklist["items"] if checklist["fingerprint"] is not None
        },
    )
