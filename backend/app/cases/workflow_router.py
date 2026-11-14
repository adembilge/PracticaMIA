"""Authenticated unified case view and explicitly user-marked checklist reviews.

Every request rebuilds the signed checklist against current approved sources.
Progress is never used to claim documents, government acceptance or
completion of any legal step.
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.tokens import Principal, get_principal
from app.cases.intake_router import _intake, _owned_case
from app.cases.intake_model import CaseIntake
from app.cases.workflow_service import build_workflow
from app.database import get_session

router = APIRouter(
    prefix="/api/v1/cases", tags=["unified-case-workflow"],
    dependencies=[Depends(get_principal)],
)


class ReviewMark(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    item_id: str = Field(min_length=1, max_length=90)
    reviewed: bool
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


def _state(db, *, case, intake, request):
    settings = request.app.state.settings
    enabled = settings.enable_private_document_api
    return build_workflow(
        db, case=case, intake=intake,
        private_documents_enabled=enabled,
        vault_key=request.app.state.private_document_key if enabled else None,
    )


@router.get("/{case_id}/workflow")
def read_case_workflow(
    case_id: UUID, request: Request,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    case = _owned_case(db, case_id, principal.subject)
    data = _state(
        db, case=case, intake=_intake(db, case_id, principal.subject),
        request=request,
    )
    return JSONResponse(data, headers={"Cache-Control": "private, no-store"})


@router.patch("/{case_id}/workflow/checklist")
def mark_reviewed_checklist_item(
    case_id: UUID, payload: ReviewMark, request: Request,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    # Serialize with intake changes and scope updates. The original case row
    # is locked first in all three paths, preventing stale cross-request marks.
    case = _owned_case(db, case_id, principal.subject, lock=True)
    intake = db.scalar(
        select(CaseIntake).where(
            CaseIntake.case_id == str(case_id),
            CaseIntake.owner_subject == principal.subject,
        ).with_for_update()
    )
    state = _state(db, case=case, intake=intake, request=request)
    checklist = state["checklist"]
    actual = checklist["fingerprint"]
    if (intake is None or actual is None or
            payload.fingerprint != actual or
            payload.item_id not in {i["id"] for i in checklist["items"]}):
        raise HTTPException(
            409, "Checklist changed; reload the saved case and current sources"
        )
    current = (
        intake.checklist_progress
        if intake.progress_fingerprint == actual and
           isinstance(intake.checklist_progress, dict)
        else {}
    )
    updated = dict(current)
    if payload.reviewed:
        updated[payload.item_id] = datetime.now(timezone.utc).isoformat()
    else:
        updated.pop(payload.item_id, None)
    intake.checklist_progress = updated
    intake.progress_fingerprint = actual
    db.commit()
    # Freshly derive progress from the committed, owner-scoped data.
    return JSONResponse(
        _state(db, case=case, intake=intake, request=request),
        headers={"Cache-Control": "private, no-store"},
    )
