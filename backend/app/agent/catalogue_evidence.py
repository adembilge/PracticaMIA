"""Internal Phase 4 adapter for the existing approved Milan passage catalogue."""

from dataclasses import dataclass
from datetime import timezone
import re
from typing import Literal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.agent.contract import Citation
from app.agent.threads import AgentThread, AgentThreadCase
from app.auth.tokens import Principal
from app.cases.intake_model import CaseIntake
from app.cases.intake_schemas import IntakeFacts, describe_intake
from app.cases.model import CaseRecord
from app.cases.scope import DEMO_ANSWERS, classify_scope
from app.knowledge.entity_matching import normalize_name
from app.knowledge.search import (
    EvidencePassage, normalize_query, resolve_approved_passage, search_approved_passages,
)
from app.rules.engine import JURISDICTION, PROCEDURE

_RESIDENCE_TERMS = re.compile(r"\b(?:residenza|registered residence|registered address)\b")
_DOMICILE_TERMS = re.compile(r"\b(?:domicilio|domicile)\b")
_ADDRESS_CHANGE_TERMS = re.compile(
    r"\b(?:change of address|chang(?:e|ed|ing) (?:my|the|a) address|"
    r"(?:report|register) (?:my|the|a) new address|"
    r"cambio (?:di )?indirizzo|(?:cambio|cambiare) il (?:mio )?indirizzo|"
    r"(?:comunicar|registrar)e il nuovo indirizzo)\b"
)
_ANPR_TERMS = re.compile(r"\b(?:anpr|a n p r)\b")


def _milan_search_hint(query: str) -> str:
    """Build one lexical fallback. Its terms narrow retrieval inside case scope."""
    key = normalize_name(query)
    terms = []
    if _DOMICILE_TERMS.search(key):
        terms.append("domicilio")
        if _RESIDENCE_TERMS.search(key):
            terms.append("residenza")
    elif _ADDRESS_CHANGE_TERMS.search(key):
        terms.extend(("cambio", "residenza"))
    elif _RESIDENCE_TERMS.search(key):
        terms.append("residenza")
    if _ANPR_TERMS.search(key):
        terms.append("anpr")
    return " ".join(terms)


@dataclass(frozen=True)
class CataloguePassage:
    citation: Citation
    section_path: str
    content: str


@dataclass(frozen=True)
class CatalogueEvidence:
    status: Literal[
        "evidence_found", "insufficient_evidence", "needs_information", "unsupported_scope",
        "case_unavailable",
    ]
    passages: tuple[CataloguePassage, ...] = ()
    missing_fields: tuple[str, ...] = ()


def _case_evidence_gap(
    db: Session, thread_id: UUID, case_id: UUID, principal: Principal,
) -> CatalogueEvidence | None:
    # Fetch the case link, ownership, scope and intake together so they describe one database
    # snapshot. Select columns directly to avoid reusing cached ORM instances.
    context = db.execute(
        select(
            CaseRecord.procedure, CaseRecord.status, CaseRecord.scope_answers,
            CaseIntake.facts, CaseIntake.confirmed_at,
        )
        .join(AgentThreadCase, AgentThreadCase.case_id == CaseRecord.id)
        .join(AgentThread, AgentThread.id == AgentThreadCase.thread_id)
        .outerjoin(CaseIntake, and_(
            CaseIntake.case_id == CaseRecord.id,
            CaseIntake.owner_subject == CaseRecord.owner_subject,
        ))
        .where(
            AgentThread.id == str(thread_id),
            AgentThread.owner_subject == principal.subject,
            CaseRecord.id == str(case_id),
            CaseRecord.owner_subject == principal.subject,
        )
    ).one_or_none()
    if context is None:
        return CatalogueEvidence(status="case_unavailable")

    procedure, status, scope_answers, facts, confirmed_at = context
    if procedure != PROCEDURE or status == "unsupported":
        return CatalogueEvidence(status="unsupported_scope")
    if not isinstance(scope_answers, list):
        return CatalogueEvidence(status="needs_information", missing_fields=("scope_answers",))
    if classify_scope(scope_answers) == "unsupported":
        return CatalogueEvidence(status="unsupported_scope")
    if status != "provisionally_in_scope" or tuple(scope_answers) != DEMO_ANSWERS:
        return CatalogueEvidence(status="needs_information", missing_fields=("scope_answers",))

    if confirmed_at is None:
        return CatalogueEvidence(status="needs_information", missing_fields=("intake_confirmation",))
    try:
        typed_facts = IntakeFacts.model_validate(facts).model_dump(exclude_none=True)
    except ValidationError:
        return CatalogueEvidence(status="needs_information", missing_fields=("intake_confirmation",))
    intake = describe_intake(typed_facts, confirmed=True)
    if intake["outside_first_scenario"]:
        return CatalogueEvidence(status="unsupported_scope")
    if not intake["first_scenario_match"]:
        return CatalogueEvidence(status="needs_information", missing_fields=tuple(intake["missing_fields"]))
    return None


def _catalogue_passage(passage: EvidencePassage) -> CataloguePassage:
    # All review writes record UTC. SQLite drops the offset on timestamp reads.
    reviewed_at = passage.reviewed_at
    if reviewed_at.tzinfo is None:
        reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
    return CataloguePassage(
        citation=Citation(
            citation_id=passage.citation_id,
            passage_id=passage.passage_id,
            source_id=passage.source_id,
            source_version_id=passage.source_version_id,
            official_url=passage.official_url,
            publisher=passage.institution,
            reviewed_at=reviewed_at,
            procedure_id=passage.procedure_id,
            location_id=passage.jurisdiction,
        ),
        section_path=passage.section_path,
        content=passage.content,
    )


def find_catalogue_evidence(
    db: Session, *, thread_id: UUID, case_id: UUID, principal: Principal, query: str, limit: int = 5,
) -> CatalogueEvidence:
    """Read Italian excerpts using the owning case's confirmed scope."""
    if gap := _case_evidence_gap(db, thread_id, case_id, principal):
        return gap
    search_scope = {
        "jurisdiction": JURISDICTION, "procedure_id": PROCEDURE, "language": "it", "limit": limit,
    }
    rows = search_approved_passages(db, query=query, **search_scope)
    if not rows and (hint := _milan_search_hint(query)) and hint != normalize_query(query)[0]:
        rows = search_approved_passages(db, query=hint, **search_scope)
    return CatalogueEvidence(
        status="evidence_found" if rows else "insufficient_evidence",
        passages=tuple(_catalogue_passage(row) for row in rows),
    )


def resolve_catalogue_evidence(
    db: Session, *, thread_id: UUID, case_id: UUID, principal: Principal, citation_id: str,
) -> CatalogueEvidence:
    """Recheck an exact citation at use time with the current approval gates."""
    if gap := _case_evidence_gap(db, thread_id, case_id, principal):
        return gap
    row = resolve_approved_passage(
        db, citation_id=citation_id, jurisdiction=JURISDICTION,
        procedure_id=PROCEDURE, language="it",
    )
    if row is None:
        return CatalogueEvidence(status="insufficient_evidence")
    return CatalogueEvidence(status="evidence_found", passages=(_catalogue_passage(row),))
