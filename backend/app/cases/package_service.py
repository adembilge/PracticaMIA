"""Read-only, on-demand preparation dossier for the first reviewed Milan case.

A dossier is not an official application, government submission or declaration
of eligibility. No AI, file bytes, OCR pages, names or addresses are used.

The verified checklist is rebuilt on every request from current source approvals.
User-confirmed categorical facts are kept distinct from signed source-backed
actions and from document-review comparisons.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cases.checklist_service import build_case_checklist
from app.cases.intake_model import CaseIntake
from app.cases.intake_schemas import IntakeFacts, REQUIRED_FIELDS
from app.cases.model import CaseRecord
from app.private_documents.model import PrivateCaseDocument

ANPR_PORTAL = "https://www.anagrafenazionale.interno.it/"
MUNICIPAL_SERVICE = "https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza"

FACT_LABELS = {
    "citizenship_class": "Citizenship category",
    "registration_context": "Previously registered residence",
    "destination_municipality": "Destination municipality",
    "household_scope": "Household arrangement",
    "housing_basis": "Housing basis",
    "move_in_date": "Move-in date (user-entered; not validated against official records)",
}
DOCUMENT_STATUS = frozenset({
    "needs_extraction", "unreadable", "no_supported_fields", "needs_user_confirmation",
    "needs_manual_review", "conflict", "needs_confirmed_intake",
    "user_reviewed_unverified", "unsupported_category",
})


def build_package_manifest(
    db: Session, *, case: CaseRecord, intake: CaseIntake | None,
    private_documents_enabled: bool, vault_key: bytes | None = None,
) -> dict:
    """Only pass owner-filtered case and intake returned by authenticated route."""
    checklist = build_case_checklist(
        db, case_status=case.status, scope_answers=case.scope_answers,
        intake=intake,
    )
    now = datetime.now(timezone.utc)
    issues: list[str] = []
    facts: list[dict] = []
    documents: list[dict] = []

    if checklist["status"] != "ready_for_user_review":
        issues.append("checklist_" + checklist["status"])
    else:
        # This catalog requires explicit user confirmation of all five facts.
        # The reviewed rule evaluator already checked those values.
        if intake is None or intake.confirmed_at is None:
            issues.append("intake_not_confirmed")
        else:
            try:
                typed = IntakeFacts.model_validate(intake.facts)
                values = typed.model_dump(exclude_none=True)
                facts = [
                    {"field": field, "label": FACT_LABELS[field],
                     "value": values[field], "provenance": "user_confirmed"}
                    for field in (*REQUIRED_FIELDS, "move_in_date") if field in values
                ]
            except Exception:
                issues.append("intake_data_invalid")

    if checklist["status"] == "ready_for_user_review":
        if not private_documents_enabled:
            # The production private vault is gated; never misrepresent
            # a disabled service as proof the user has no missing documents.
            issues.append("private_document_processing_not_enabled")
        else:
            if vault_key is None or len(vault_key) != 32:
                issues.append("document_review_unavailable")
            else:
                from app.private_documents.intelligence_router import _read_metadata
                from app.private_documents.intelligence import compare_review

                rows = db.scalars(select(PrivateCaseDocument).where(
                    PrivateCaseDocument.case_id == case.id,
                    PrivateCaseDocument.owner_subject == case.owner_subject,
                    PrivateCaseDocument.expires_at > now,
                ).order_by(PrivateCaseDocument.uploaded_at.asc()).limit(6)).all()
                if len(rows) > 5:
                    issues.append("document_limit_exceeded")
                for i, doc in enumerate(rows, 1):
                    if not doc.consented_at or not doc.scanned_at:
                        issues.append("unscanned_document")
                        continue
                    review = _read_metadata(doc, vault_key)
                    comparison = compare_review(
                        review, intake_facts=intake.facts if intake else None,
                        intake_confirmed=bool(intake and intake.confirmed_at),
                        document_id=doc.id,
                    )
                    status = ("unsupported_category"
                              if doc.category != "housing_document"
                              else comparison["status"])
                    if status not in DOCUMENT_STATUS:
                        issues.append("unrecognized_document_review")
                        continue
                    # No file names, raw page text, document ID, digest, address
                    # or unverified source snippets are exported.
                    documents.append({
                        "number": i, "category": doc.category,
                        "review_status": status,
                        "comparisons": [
                            {"field": c["field_name"],
                             "result": c["comparison"]}
                            for c in comparison["comparisons"]
                            if c["field_name"] in {"housing_basis", "move_in_date"}
                            and c["comparison"] in {
                                "match", "conflict", "no_confirmed_case_fact"
                            }
                        ],
                    })
                    if status != "user_reviewed_unverified":
                        issues.append("document_" + status)
                if not rows:
                    issues.append("no_documents_reviewed")

    # A preparation DRAFT can be created with no documents, but any uploaded
    # incomplete/conflicting review blocks even its export. Neither case means
    # a legally complete application.
    actionable = checklist["status"] == "ready_for_user_review"
    document_blockers = [
        issue for issue in issues if issue.startswith("document_")
        and issue != "document_review_unavailable"
    ]
    allowed = (actionable and bool(facts) and not document_blockers
               and "intake_data_invalid" not in issues
               and "document_limit_exceeded" not in issues
               and "unscanned_document" not in issues)
    # 'no_documents_reviewed' is an explicit warning, not a blocker for
    # a labeled draft with unverified document requirements.
    if "no_documents_reviewed" in issues and not any(
        x.startswith("document_") for x in issues
    ):
        allowed = actionable and bool(facts)

    return {
        "status": ("reviewable_draft" if allowed else "blocked"),
        "download_allowed": allowed,
        "case_reference": case.id[:8],
        "procedure_id": "milan_residence_change",
        "jurisdiction": "IT-MI-MILANO",
        "generated_at": now.isoformat(),
        "reviewed_ruleset": checklist["ruleset_version"],
        "confirmed_facts": facts if actionable else [],
        "checklist": checklist["items"] if actionable else [],
        "documents": documents,
        "outstanding_issues": sorted(set(issues)),
        "official_handoff": {
            "anpr_portal": ANPR_PORTAL,
            "milan_service": MUNICIPAL_SERVICE,
            "instruction": (
                "Verify current requirements on official services. "
                "You must submit personally; PracticaMIA does not submit."
            ),
        },
        "document_requirements_verified": False,
        "eligibility_evaluated": False,
        "documents_legally_verified": False,
        "official_submission": False,
        "official_acceptance": False,
        "draft_only": True,
        "synthetic_only": True,
    }
