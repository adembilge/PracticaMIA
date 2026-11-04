"""Explicitly opt-in, unauthenticated synthetic-demo endpoints."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.cases.model import CaseRecord
from app.cases.schemas import CaseOut, CreateCase, ScopeUpdate
from app.cases.scope import classify_scope
from app.database import get_session

router = APIRouter(prefix="/api/v1/cases", tags=["demo-cases"])


def get_case(db: Session, case_id: UUID) -> CaseRecord:
    record = db.get(CaseRecord, str(case_id))
    if record is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return record


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
def create_case(payload: CreateCase, db: Session = Depends(get_session)):
    record = CaseRecord(id=str(uuid4()), procedure=payload.procedure)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{case_id}", response_model=CaseOut)
def read_case(case_id: UUID, db: Session = Depends(get_session)):
    return get_case(db, case_id)


@router.patch("/{case_id}/scope", response_model=CaseOut)
def update_scope(case_id: UUID, payload: ScopeUpdate, db: Session = Depends(get_session)):
    record = get_case(db, case_id)
    record.scope_answers = list(payload.answers)
    record.status = classify_scope(record.scope_answers)
    record.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(case_id: UUID, db: Session = Depends(get_session)):
    db.delete(get_case(db, case_id))
    db.commit()
