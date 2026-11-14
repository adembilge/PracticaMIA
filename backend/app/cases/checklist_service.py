"""Read-only approved first-route checklist for an authenticated saved case.

No language model, unverified upload, user-supplied rule, eligibility decision,
external submission, or persisted 'completed' status is involved.

The verification key is a PUBLIC key pinned to the already owner-reviewed
November 8 catalog. Its exact value is also committed in
requirements/milan-residence-change/review_public_key_v1.b64.
The existing Preview-specific environment-key gate is unchanged.
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.cases.intake_model import CaseIntake
from app.cases.intake_schemas import IntakeFacts, REQUIRED_FIELDS, SUPPORTED_FACTS
from app.knowledge.search import resolve_approved_passage
from app.rules.approval import has_valid_human_review_signature
from app.rules.catalog import CATALOG_PATH
from app.rules.engine import JURISDICTION, PROCEDURE, evaluate_rules, load_catalog

# Public verification material; not a private signing key.
PINNED_FIRST_ROUTE_PUBLIC_KEY = "IyMHvHtkOTquYpiOx7PMZuTg8IS79+KGKH/PSThJLl0="
PINNED_SOURCE_VERSIONS = {
    "milano-italian-residence-change": (
        "e139e910-3a89-4994-b450-b5107d8db7dd",
        "https://servizicrm.comune.milano.it/centro-supporto/KA-00371/",
        False,
    ),
    "anpr-public-docs-residence-guide": (
        "c89b4c40-4c41-48d5-ad52-be08e9630277",
        "https://public-anpr.github.io/anpr-docs-cittadino/src/docs/guide/guida_compilazione_cambio_residenza.pdf",
        True,
    ),
}

STATUS_ACTIONS = {
    "needs_scope": "Complete the initial scope questions before reviewing requirements.",
    "needs_confirmation": "Complete and explicitly confirm the separate case intake.",
    "outside_first_route": "This example falls outside the supported route. Consult the relevant official service; this is not legal ineligibility.",
    "evidence_unavailable": "Reviewed rules or citations are unavailable. Use the official portals; no checklist can be issued.",
    "ready_for_user_review": "Read each reviewed action and verify current requirements on the official websites. No government submission occurred.",
}


def _state(status: str, *, missing: list[str] | None = None) -> dict:
    return {
        "status": status,
        "next_action": STATUS_ACTIONS[status],
        "missing_fields": missing or [],
        "ruleset_version": None,
        "items": [],
        "required_document_types": [],
        "verified_evidence": status == "ready_for_user_review",
        "first_scenario_only": True,
        "synthetic_only": True,
        "eligibility_evaluated": False,
        "documents_verified": False,
        "government_submitted": False,
    }


@lru_cache(maxsize=1)
def _reviewed_catalog() -> dict:
    catalog = load_catalog(CATALOG_PATH.read_text(encoding="utf-8"))
    if not has_valid_human_review_signature(catalog, PINNED_FIRST_ROUTE_PUBLIC_KEY):
        return {**catalog, "status": "pending_review"}
    return catalog


def _citation_metadata(evidence) -> dict:
    return {
        "citation_id": evidence.citation_id,
        "source_id": evidence.source_id,
        "source_version_id": evidence.source_version_id,
        "institution": evidence.institution,
        "title": evidence.title,
        "official_url": evidence.official_url,
        "reviewed_at": evidence.reviewed_at.isoformat(),
        "retrieved_at": evidence.retrieved_at.isoformat(),
        "archived_reference": PINNED_SOURCE_VERSIONS[evidence.source_id][2],
    }


def build_case_checklist(db: Session, *, case_status: str,
                         scope_answers: list[str],
                         intake: CaseIntake | None) -> dict:
    """Render fresh signed rules against *owner-scoped* persisted intake.

    Only the owning authenticated route may supply these server-side inputs.
    The original scope stage and this intake must both remain confirmed.
    """
    if case_status != "provisionally_in_scope" or scope_answers != [
        "yes", "yes", "yes", "no", "yes"
    ]:
        return _state("needs_scope")
    if intake is None or intake.confirmed_at is None:
        return _state("needs_confirmation")

    try:
        typed = IntakeFacts.model_validate(intake.facts)
        facts = typed.model_dump(exclude_none=True)
    except (ValidationError, TypeError, ValueError):
        return _state("needs_confirmation")

    missing = [
        f for f in REQUIRED_FIELDS if facts.get(f) in (None, "unknown")
    ]
    if missing:
        return _state("needs_confirmation", missing=missing)
    if any(facts[f] != expected for f, expected in SUPPORTED_FACTS.items()):
        return _state("outside_first_route")

    verified: dict[str, object] = {}

    def evidence_is_approved(ref: str) -> bool:
        if ref not in verified:
            verified[ref] = resolve_approved_passage(
                db, citation_id=ref, jurisdiction=JURISDICTION,
                procedure_id=PROCEDURE, language="it"
            )
        passage = verified[ref]
        if passage is None:
            return False
        pinned = PINNED_SOURCE_VERSIONS.get(passage.source_id)
        return bool(
            pinned is not None and passage.source_version_id == pinned[0]
            and passage.official_url == pinned[1]
            and passage.citation_id == ref
        )

    result = evaluate_rules(
        _reviewed_catalog(),
        {key: facts[key] for key in REQUIRED_FIELDS},
        evidence_is_approved,
        demo_only=True,
    )
    if result.decision != "supported":
        # No partial instructions when a signature, rule or citation fails.
        return _state("evidence_unavailable" if result.decision == "blocked"
                      else "outside_first_route")

    items: list[dict] = []
    for rule in result.checklist:
        citations = []
        for ref in rule["evidence_refs"]:
            passage = verified.get(ref)
            if passage is None or not evidence_is_approved(ref):
                return _state("evidence_unavailable")
            citations.append(_citation_metadata(passage))
        items.append({
            "id": rule["rule_id"],
            "description": rule["description"],  # Exact signed text, not LLM output.
            "status": "needs_user",
            "obligation_class": "reviewed_action",
            "evidence": citations,
        })

    if len(items) != 5 or result.required_document_types:
        # Fail closed if reviewed catalog and narrow release expectations drift.
        return _state("evidence_unavailable")

    response = _state("ready_for_user_review")
    response.update({
        "items": items,
        "ruleset_version": result.ruleset_version,
        "required_document_types": [],
    })
    return response
