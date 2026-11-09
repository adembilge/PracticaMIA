"""Authenticated read-only checklist. No private fields or document bytes returned."""
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth.tokens import Principal, get_principal
from app.cases.intake_router import _intake
from app.cases.router import get_case
from app.cases.checklist_service import build_case_checklist
from app.database import get_session

router = APIRouter(prefix="/api/v1/cases", tags=["reviewed-checklist"],
                   dependencies=[Depends(get_principal)])


@router.get("/{case_id}/checklist")
def get_reviewed_case_checklist(
    case_id: UUID,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    case = get_case(db, case_id, principal.subject)
    intake = _intake(db, case_id, principal.subject)
    result = build_case_checklist(
        db, case_status=case.status, scope_answers=case.scope_answers,
        intake=intake,
    )
    return JSONResponse(result, headers={"Cache-Control": "private, no-store"})
