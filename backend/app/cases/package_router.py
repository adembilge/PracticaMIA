"""Authenticated, cache-protected case preparation draft and PDF export.

The source-verified checklist is re-evaluated for both endpoints. Nothing is
written to a database; no model or external portal is contacted. PDF download
requires a supported first-route case and no unresolved uploaded-file review.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.auth.tokens import Principal, get_principal
from app.cases.router import get_case
from app.cases.intake_router import _intake
from app.cases.package_service import build_package_manifest
from app.cases.package_pdf import render_preparation_pdf
from app.database import get_session

router = APIRouter(
    prefix="/api/v1/cases", tags=["preparation-export"],
    dependencies=[Depends(get_principal)],
)

PRIVATE_HEADERS = {"Cache-Control": "private, no-store", "X-Robots-Tag": "noindex"}


def _build(
    case_id: UUID, request: Request, db: Session, principal: Principal
) -> dict:
    case = get_case(db, case_id, principal.subject)
    intake = _intake(db, case_id, principal.subject)
    private_enabled = request.app.state.settings.enable_private_document_api
    return build_package_manifest(
        db, case=case, intake=intake,
        private_documents_enabled=private_enabled,
        vault_key=(request.app.state.private_document_key if private_enabled else None),
    )


@router.get("/{case_id}/package")
def read_package_preview(
    case_id: UUID, request: Request, db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    return JSONResponse(_build(case_id, request, db, principal),
                        headers=PRIVATE_HEADERS)


@router.get("/{case_id}/package/pdf")
def download_package_draft(
    case_id: UUID, request: Request, db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
):
    manifest = _build(case_id, request, db, principal)
    if not manifest["download_allowed"]:
        raise HTTPException(
            status_code=409,
            detail="Resolve confirmed-case or document-review blockers before export",
        )
    pdf = render_preparation_pdf(manifest)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            **PRIVATE_HEADERS,
            "Content-Disposition": 'attachment; filename="practicamia-preparation-draft.pdf"',
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "Referrer-Policy": "no-referrer",
        },
    )
