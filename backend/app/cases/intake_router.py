"""Authenticated, persistent residence-change intake with explicit confirmation.

Never accepts full address, names, identifiers, lease files or free-form notes.
The output is NOT a municipal decision and does not invoke the rules engine.
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.tokens import Principal, get_principal
from app.cases.model import CaseRecord
from app.cases.intake_model import CaseIntake
from app.cases.intake_schemas import IntakeUpdate, REQUIRED_FIELDS, describe_intake
from app.database import get_session

router = APIRouter(prefix="/api/v1/cases", tags=["case-intake"],
                   dependencies=[Depends(get_principal)])


def _owned_case(db: Session, case_id: UUID, owner: str, *, lock: bool = False) -> CaseRecord:
    statement = select(CaseRecord).where(
        CaseRecord.id == str(case_id), CaseRecord.owner_subject == owner
    )
    case = db.scalar(statement.with_for_update() if lock else statement)
    if case is None:
        raise HTTPException(404, "Case not found")
    return case


def _intake(db: Session, case_id: UUID, owner: str) -> CaseIntake | None:
    return db.scalar(select(CaseIntake).where(
        CaseIntake.case_id == str(case_id), CaseIntake.owner_subject == owner
    ))


def _state(record: CaseIntake | None) -> dict:
    facts = dict(record.facts) if record else {}
    result = describe_intake(facts, bool(record and record.confirmed_at))
    result["confirmed_at"] = record.confirmed_at.isoformat() if record and record.confirmed_at else None
    result["updated_at"] = record.updated_at.isoformat() if record else None
    return result


@router.get("/{case_id}/intake")
def read_intake(case_id: UUID, db: Session = Depends(get_session),
                principal: Principal = Depends(get_principal)):
    _owned_case(db, case_id, principal.subject)
    return _state(_intake(db, case_id, principal.subject))


@router.put("/{case_id}/intake")
def write_intake(case_id: UUID, payload: IntakeUpdate,
                 db: Session = Depends(get_session),
                 principal: Principal = Depends(get_principal)):
    case = _owned_case(db, case_id, principal.subject, lock=True)
    if case.status != "provisionally_in_scope" or case.scope_answers != [
        "yes", "yes", "yes", "no", "yes"
    ]:
        raise HTTPException(409, "Complete the supported product scope questions first")

    facts = payload.facts.model_dump(exclude_none=True)
    if payload.confirm:
        if any(facts.get(field) in (None, "unknown") for field in REQUIRED_FIELDS):
            raise HTTPException(422, "Confirm all five categorical intake questions first")
    row = _intake(db, case_id, principal.subject)
    if row is None:
        row = CaseIntake(case_id=str(case_id), owner_subject=principal.subject)
        db.add(row)
    if row.facts != facts or (row.confirmed_at is not None and not payload.confirm):
        # A corrected/deselected fact invalidates all previous user review marks.
        # Simply re-confirming unchanged facts preserves review progress.
        row.checklist_progress = {}
        row.progress_fingerprint = None
    row.facts = facts  # replacement semantics prevent stale unconfirmed facts
    row.confirmed_at = datetime.now(timezone.utc) if payload.confirm else None
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _state(row)


@router.delete("/{case_id}/intake", status_code=204)
def erase_intake(case_id: UUID, db: Session = Depends(get_session),
                 principal: Principal = Depends(get_principal)):
    _owned_case(db, case_id, principal.subject, lock=True)
    db.execute(delete(CaseIntake).where(
        CaseIntake.case_id == str(case_id), CaseIntake.owner_subject == principal.subject
    ))
    db.commit()
