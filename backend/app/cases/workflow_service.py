"""One owner-scoped, source-verified journey over existing saved-case stages.

All decisions derive from the authenticated case and current source registry;
no LLM, browser-supplied facts, government API, or unverified document text.
Checklist marks mean "I reviewed this instruction", never completion of a
legal duty. Marks are invisible when signed evidence or facts become stale.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json

from app.cases.package_service import build_package_manifest

STEP_ORDER = ("scope", "intake", "guidance", "checklist", "documents", "package", "handoff")
SIGNED_ACTION_IDS = frozenset({
    "italian_change_anpr_guidance", "italian_change_tari_followup",
    "registered_rental_anpr_fields", "tenant_attachments_reference_only",
    "applicant_only_anpr_handoff",
})
DOCUMENT_BLOCKERS = frozenset({
    "document_needs_extraction", "document_unreadable",
    "document_no_supported_fields", "document_needs_user_confirmation",
    "document_needs_manual_review", "document_conflict",
    "document_comparison_unresolved", "document_needs_confirmed_intake",
    "document_unsupported_category", "document_limit_exceeded",
    "unscanned_document", "unrecognized_document_review",
    "document_review_unavailable",
})


def evidence_fingerprint(case, intake, manifest: dict) -> str | None:
    """Digest of currently validated rule text, specific citations and facts."""
    if (intake is None or intake.confirmed_at is None or
            manifest["reviewed_ruleset"] is None or
            manifest["status"] not in {"reviewable_draft", "blocked"} or
            len(manifest["checklist"]) != 5):
        return None
    if {item["id"] for item in manifest["checklist"]} != SIGNED_ACTION_IDS:
        return None
    snapshot = {
        "scope": case.scope_answers,
        "facts": intake.facts,
        "ruleset": manifest["reviewed_ruleset"],
        "actions": [
            {
                "id": item["id"], "description": item["description"],
                "evidence": [
                    {
                        "citation_id": evidence["citation_id"],
                        "source_version_id": evidence["source_version_id"],
                        "official_url": evidence["official_url"],
                        "reviewed_at": evidence["reviewed_at"],
                        "retrieved_at": evidence["retrieved_at"],
                    }
                    for evidence in item["evidence"]
                ],
            }
            for item in manifest["checklist"]
        ],
    }
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def assemble_workflow(*, case, intake, manifest: dict,
                      private_documents_enabled: bool) -> dict:
    fingerprint = evidence_fingerprint(case, intake, manifest)
    stored = (
        intake.checklist_progress
        if intake is not None and intake.progress_fingerprint == fingerprint and
           fingerprint is not None and isinstance(intake.checklist_progress, dict)
        else {}
    )
    reviewed = {
        item["id"]: stored[item["id"]]
        for item in manifest["checklist"]
        if item["id"] in stored and isinstance(stored[item["id"]], str)
    }
    count = len(reviewed)
    scope_complete = (case.status == "provisionally_in_scope"
                      and case.scope_answers == ["yes", "yes", "yes", "no", "yes"])
    intake_confirmed = bool(intake is not None and intake.confirmed_at)
    checklist_ready = fingerprint is not None
    issues = manifest["outstanding_issues"]
    docs_blocked = any(issue in DOCUMENT_BLOCKERS for issue in issues)
    vault_docs = manifest["documents"]

    if not scope_complete:
        next_action = "answer_scope"
    elif not intake_confirmed:
        next_action = "confirm_intake"
    elif "checklist_outside_first_route" in issues:
        next_action = "consult_official"
    elif not checklist_ready:
        next_action = "review_sources"
    elif count < 5:
        next_action = "review_checklist"
    elif docs_blocked:
        next_action = "resolve_documents"
    elif manifest["download_allowed"]:
        next_action = "download_draft"
    else:
        next_action = "review_package"

    stages = [
        {"id": "scope", "status": (
            "complete" if scope_complete else
            "blocked" if case.status == "unsupported" else "needs_attention"
        )},
        {"id": "intake", "status": (
            "complete" if scope_complete and intake_confirmed else
            "blocked" if not scope_complete and case.status == "unsupported" else
            "needs_attention" if scope_complete else "locked"
        )},
        {"id": "guidance", "status": (
            "informational" if scope_complete else "locked"
        )},
        {"id": "checklist", "status": (
            "reviewed_by_user" if checklist_ready and count == 5 else
            "needs_attention" if checklist_ready else "locked"
        )},
        {"id": "documents", "status": (
            "unavailable" if not private_documents_enabled else
            "needs_attention" if docs_blocked else
            "user_reviewed_unverified" if vault_docs else "optional_unverified"
        )},
        {"id": "package", "status": (
            "draft_available" if manifest["download_allowed"] else "blocked"
        )},
        {"id": "handoff", "status": "user_only_not_submitted"},
    ]
    return {
        "case_reference": case.id[:8],
        "workflow_version": "case-journey-v1",
        "steps": stages,
        "next_action": next_action,
        "scope_status": case.status,
        "intake_confirmed": intake_confirmed,
        "checklist": {
            "status": ("ready_for_user_review" if checklist_ready else "unavailable"),
            "ruleset_version": manifest["reviewed_ruleset"],
            "items": manifest["checklist"],
            "reviewed_items": reviewed,
            "reviewed_count": count,
            "total": len(manifest["checklist"]),
            "fingerprint": fingerprint,
        },
        "package": {
            "status": manifest["status"],
            "download_allowed": manifest["download_allowed"],
            "outstanding_issues": issues,
        },
        "documents": {
            "enabled": private_documents_enabled,
            "reviewed_count": sum(d["review_status"] == "user_reviewed_unverified"
                                  for d in vault_docs),
            "uploaded_count": len(vault_docs),
            "legal_verification": False,
        },
        "official_submission": False,
        "eligibility_evaluated": False,
        "synthetic_only": True,
    }


def build_workflow(db, *, case, intake, private_documents_enabled: bool,
                   vault_key: bytes | None):
    manifest = build_package_manifest(
        db, case=case, intake=intake,
        private_documents_enabled=private_documents_enabled,
        vault_key=vault_key,
    )
    return assemble_workflow(
        case=case, intake=intake, manifest=manifest,
        private_documents_enabled=private_documents_enabled,
    )
