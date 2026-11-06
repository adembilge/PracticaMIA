"""Read a versioned ruleset; resolve citations again on every request.

No admin API changes rule status, no LLM can edit this file. Real approval
requires a human-reviewed PR and individually approved source snapshots.
"""
from functools import lru_cache
from pathlib import Path
from os import environ

from sqlalchemy.orm import Session

from app.rules.engine import JURISDICTION, PROCEDURE, evaluate_rules, load_catalog
from app.rules.approval import has_valid_human_review_signature
from app.knowledge.search import resolve_approved_passage

CATALOG_PATH = Path(__file__).with_name("catalog.json")


@lru_cache(maxsize=1)
def current_catalog() -> dict:
    catalog = load_catalog(CATALOG_PATH.read_text(encoding="utf-8"))
    if catalog.get("status") != "active":
        return catalog
    if not has_valid_human_review_signature(
        catalog, environ.get("PREPARATION_RULE_REVIEW_PUBLIC_KEY", ""),
    ):
        # A forged 'approved_by' string or unreviewed file edit cannot
        # activate a mandatory rule. Never log the signature/key.
        return {**catalog, "status": "pending_review"}
    return catalog


def evaluate_case_rules(db: Session, confirmed_facts: dict):
    def evidence_is_approved(citation_id: str) -> bool:
        return resolve_approved_passage(
            db, citation_id=citation_id, jurisdiction=JURISDICTION,
            procedure_id=PROCEDURE, language="it",
        ) is not None
    return evaluate_rules(current_catalog(), confirmed_facts, evidence_is_approved)
