"""Revalidate an answer's exact citations against the active registry and case scope."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.catalogue_evidence import catalogue_passage
from app.agent.contract import AnswerResult, Citation, Language, NextAction
from app.auth.tokens import Principal
from app.knowledge.model import KnowledgeSource
from app.knowledge.search import resolve_approved_passage
from app.knowledge.service_areas import CaseLocation, ServiceArea, resolve_service_areas


@dataclass(frozen=True)
class AnswerEvidenceScope:
    """Server-provided procedure, confirmed case facts, and reviewed passage assignments."""

    procedure_id: str
    case_locations: Mapping[str, CaseLocation]
    confirmed_dates: Mapping[str, date]
    confirmed_circumstances: Mapping[str, str]
    assignments: tuple[ServiceArea, ...]


# The reader receives the transaction, thread, run, case, and authenticated principal.
AnswerEvidenceScopeReader = Callable[[Session, UUID, UUID, UUID | None, Principal], AnswerEvidenceScope | None]


def _citation_applies(db: Session, citation: Citation, scope: AnswerEvidenceScope) -> bool:
    if citation.procedure_id != scope.procedure_id:
        return False
    for assignment in scope.assignments:
        if assignment.evidence_ref != citation.passage_id or citation.location_id not in assignment.unit_ids:
            continue
        # A passage scoped to one city cannot borrow another city's confirmed location
        # from an assignment covering both. Period and circumstance checks use the same resolver as routing.
        narrowed = replace(assignment, unit_ids=(citation.location_id,))
        if resolve_service_areas(
            scope.procedure_id, scope.case_locations, (narrowed,),
            trusted_passage_ids=frozenset({citation.passage_id}),
            confirmed_dates=scope.confirmed_dates, confirmed_circumstances=scope.confirmed_circumstances,
        ).status == "supported":
            break
    else:
        return False

    active = resolve_approved_passage(
        db, citation_id=citation.passage_id, jurisdiction=citation.location_id,
        procedure_id=scope.procedure_id, language=None,
    )
    return active is not None and catalogue_passage(active).citation == citation


def revalidate_answer_evidence(
    db: Session, result: AnswerResult, *, scope: AnswerEvidenceScope | None, language: Language,
) -> AnswerResult:
    """Check every citation and hold the registry stable through the caller's commit."""
    if not result.citations:
        return result
    if scope is not None:
        # Ingestion and review take exclusive locks on these same source rows.
        # Lock in registry order so concurrent readers use a consistent order.
        db.scalars(
            select(KnowledgeSource.id)
            .where(KnowledgeSource.id.in_({citation.source_id for citation in result.citations}))
            .order_by(KnowledgeSource.id)
            .with_for_update(read=True)
        ).all()
        if all(_citation_applies(db, citation, scope) for citation in result.citations):
            return result
    return AnswerResult(
        explanation=(
            "I could not verify that the cited evidence is current and applies to this case. Review the case details."
            if language == "en" else
            "Non ho potuto verificare che le fonti citate siano aggiornate e applicabili alla pratica. Rivedi i dati."
        ),
        verification_status="insufficient_evidence",
        missing_information=result.missing_information,
        next_action=NextAction(
            label="Review the case details" if language == "en" else "Rivedi i dati della pratica",
            operation="provide_information",
        ),
    )
