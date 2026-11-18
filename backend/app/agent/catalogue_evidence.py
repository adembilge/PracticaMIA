"""Internal Phase 4 adapter for the existing approved Milan passage catalogue."""

from dataclasses import dataclass
from datetime import timezone
from typing import Literal

from sqlalchemy.orm import Session

from app.agent.contract import Citation
from app.knowledge.search import (
    EvidencePassage, resolve_approved_passage, search_approved_passages,
)
from app.rules.engine import JURISDICTION, PROCEDURE

ScopeField = Literal["procedure_id", "jurisdiction"]


@dataclass(frozen=True)
class EvidenceScope:
    """Procedure and location supplied by authorized, confirmed case context."""

    procedure_id: str | None
    jurisdiction: str | None


@dataclass(frozen=True)
class CataloguePassage:
    citation: Citation
    section_path: str
    content: str


@dataclass(frozen=True)
class CatalogueEvidence:
    status: Literal[
        "evidence_found", "insufficient_evidence", "needs_information", "unsupported_scope",
    ]
    passages: tuple[CataloguePassage, ...] = ()
    missing_fields: tuple[ScopeField, ...] = ()


def _scope_gap(scope: EvidenceScope) -> CatalogueEvidence | None:
    if (
        scope.procedure_id not in (None, PROCEDURE)
        or scope.jurisdiction not in (None, JURISDICTION)
    ):
        return CatalogueEvidence(status="unsupported_scope")
    missing: list[ScopeField] = []
    if scope.procedure_id is None:
        missing.append("procedure_id")
    if scope.jurisdiction is None:
        missing.append("jurisdiction")
    if missing:
        return CatalogueEvidence(status="needs_information", missing_fields=tuple(missing))
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
    db: Session, *, scope: EvidenceScope, query: str, limit: int = 5,
) -> CatalogueEvidence:
    """Find Italian excerpts for the current Milan route without inferring scope."""
    if gap := _scope_gap(scope):
        return gap
    rows = search_approved_passages(
        db, query=query, jurisdiction=JURISDICTION, procedure_id=PROCEDURE,
        language="it", limit=limit,
    )
    return CatalogueEvidence(
        status="evidence_found" if rows else "insufficient_evidence",
        passages=tuple(_catalogue_passage(row) for row in rows),
    )


def resolve_catalogue_evidence(
    db: Session, *, scope: EvidenceScope, citation_id: str,
) -> CatalogueEvidence:
    """Recheck an exact citation at use time with the current approval gates."""
    if gap := _scope_gap(scope):
        return gap
    row = resolve_approved_passage(
        db, citation_id=citation_id, jurisdiction=JURISDICTION,
        procedure_id=PROCEDURE, language="it",
    )
    if row is None:
        return CatalogueEvidence(status="insufficient_evidence")
    return CatalogueEvidence(status="evidence_found", passages=(_catalogue_passage(row),))
