"""Authenticated, owner-scoped synthetic-demo case routes."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.tokens import Principal, get_principal
from app.cases.model import CaseRecord
from app.cases.schemas import CaseOut, CreateCase, ScopeUpdate
from app.cases.scope import classify_scope
from app.database import get_session

router = APIRouter(
    prefix="/api/v1/cases",
    tags=["demo-cases"],
    dependencies=[Depends(get_principal)],
)


def get_case(db: Session, case_id: UUID, owner: str) -> CaseRecord:
    record = db.scalar(
        select(CaseRecord).where(
            CaseRecord.id == str(case_id),
            CaseRecord.owner_subject == owner,
        )
    )
    if record is None:
        # Do not reveal existence of another user's (or ownerless) case.
        raise HTTPException(status_code=404, detail="Case not found")
    return record


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CreateCase,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    record = CaseRecord(
        id=str(uuid4()),
        procedure=payload.procedure,
        owner_subject=principal.subject,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[CaseOut])
def list_cases(
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    return db.scalars(
        select(CaseRecord)
        .where(CaseRecord.owner_subject == principal.subject)
        .order_by(CaseRecord.created_at.desc(), CaseRecord.id.desc())
        .limit(50)
    ).all()


@router.get("/{case_id}", response_model=CaseOut)
def read_case(
    case_id: UUID,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    return get_case(db, case_id, principal.subject)


@router.patch("/{case_id}/scope", response_model=CaseOut)
def update_scope(
    case_id: UUID,
    payload: ScopeUpdate,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    record = get_case(db, case_id, principal.subject)
    record.scope_answers = list(payload.answers)
    record.status = classify_scope(record.scope_answers)
    record.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(
    case_id: UUID,
    request: Request,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    record = get_case(db, case_id, principal.subject)
    if request.app.state.settings.enable_preparation_api:
        # Explicit cleanup also works in SQLite test fixtures with foreign
        # keys disabled; Postgres additionally enforces ON DELETE CASCADE.
        from app.preparation.models import CaseDocument, CasePreparation
        if request.app.state.settings.enable_agent_history_api:
            # SQLite test fixtures may not enforce FK cascades. Production
            # PostgreSQL also has ON DELETE CASCADE for this scoped table.
            from app.preparation.models import CaseAgentTurn
            db.execute(delete(CaseAgentTurn).where(
                CaseAgentTurn.case_id == str(case_id),
                CaseAgentTurn.owner_subject == principal.subject,
            ))
        db.execute(delete(CaseDocument).where(
            CaseDocument.case_id == str(case_id),
            CaseDocument.owner_subject == principal.subject,
        ))
        db.execute(delete(CasePreparation).where(
            CasePreparation.case_id == str(case_id),
            CasePreparation.owner_subject == principal.subject,
        ))
    db.delete(record)
    db.commit()
