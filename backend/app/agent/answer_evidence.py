"""Revalidate an answer's exact citations against the active registry and case scope."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.catalogue_evidence import catalogue_passage
from app.agent.contract import (
    MAX_ANSWER_EXPLANATION_LENGTH, AnswerResult, Citation, ClaimKind, Language, NextAction, OfficialChannel,
)
from app.auth.tokens import Principal
from app.knowledge.model import KnowledgeSource
from app.knowledge.search import resolve_approved_passage
from app.knowledge.service_areas import CaseLocation, ServiceArea, resolve_service_areas


_ACTION_LABELS = {
    "en": {
        "open_official_channel": "Open the official channel",
        "provide_information": "Provide information",
        "start_new_topic": "Start a new topic",
    },
    "it": {
        "open_official_channel": "Apri il canale ufficiale",
        "provide_information": "Fornisci informazioni",
        "start_new_topic": "Cambia argomento",
    },
}


@dataclass(frozen=True)
class ClaimPassageSupport:
    passage_id: str
    assignment_id: str
    quote: str


@dataclass(frozen=True)
class ReviewedClaimSupport:
    """An active human review of a specific statement and its supporting text."""

    kind: ClaimKind
    language: Language
    statement: str
    passages: tuple[ClaimPassageSupport, ...]
    official_channel: OfficialChannel | None = None


@dataclass(frozen=True)
class AnswerEvidenceScope:
    """Server-provided case facts, reviewed assignments and active claim reviews."""

    procedure_id: str
    case_locations: Mapping[str, CaseLocation]
    confirmed_dates: Mapping[str, date]
    confirmed_circumstances: Mapping[str, str]
    assignments: tuple[ServiceArea, ...]
    claim_reviews: tuple[ReviewedClaimSupport, ...] = ()


# The reader receives the transaction, thread, run, case, and authenticated principal.
AnswerEvidenceScopeReader = Callable[[Session, UUID, UUID, UUID | None, Principal], AnswerEvidenceScope | None]


@dataclass(frozen=True)
class _ApplicablePassage:
    content: str
    assignments: frozenset[str]


def _resolve_applicable_passage(
    db: Session, citation: Citation, scope: AnswerEvidenceScope,
) -> _ApplicablePassage | None:
    if citation.procedure_id != scope.procedure_id:
        return None
    assignment_ids = set()
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
            assignment_ids.add(assignment.assignment_id)
    if not assignment_ids:
        return None

    active = resolve_approved_passage(
        db, citation_id=citation.passage_id, jurisdiction=citation.location_id,
        procedure_id=scope.procedure_id, language=None,
    )
    if active is None or catalogue_passage(active).citation != citation:
        return None
    return _ApplicablePassage(active.content, frozenset(assignment_ids))


def _claim_passage_applies(review: ClaimPassageSupport, passages: Mapping[str, _ApplicablePassage]) -> bool:
    passage = passages.get(review.passage_id)
    return (
        passage is not None and review.assignment_id in passage.assignments
        and bool(review.quote.strip()) and review.quote in passage.content
    )


def _claims_supported(
    result: AnswerResult, reviews: tuple[ReviewedClaimSupport, ...],
    passages: Mapping[str, _ApplicablePassage], language: Language,
) -> bool:
    channel_supported = result.official_channel is None
    for claim in result.claims:
        matches = [
            review for review in reviews
            if review.kind == claim.kind and review.language == language and review.statement == claim.statement
            and {link.passage_id for link in review.passages} == set(claim.evidence_ids)
            and all(_claim_passage_applies(link, passages) for link in review.passages)
        ]
        if not matches:
            return False
        if claim.kind == "channel" and any(review.official_channel == result.official_channel for review in matches):
            channel_supported = True
    return channel_supported


def _render_verified_answer(result: AnswerResult, language: Language) -> AnswerResult:
    explanation = "\n".join(claim.statement for claim in result.claims)
    if len(explanation) > MAX_ANSWER_EXPLANATION_LENGTH:
        explanation = (
            "The verified statements are listed with their citations."
            if language == "en" else "Le affermazioni verificate sono elencate con le relative fonti."
        )
    operation = result.next_action.operation if result.next_action else None
    action = NextAction(label=_ACTION_LABELS[language][operation], operation=operation) if operation else None
    return result.model_copy(update={"explanation": explanation, "next_action": action})


def revalidate_answer_evidence(
    db: Session, result: AnswerResult, *, scope: AnswerEvidenceScope | None, language: Language,
) -> AnswerResult:
    """Check evidence and reviewed claims while holding the registry stable through commit."""
    if not result.citations:
        return result
    support_missing = False
    if scope is not None:
        # Ingestion and review take exclusive locks on these same source rows.
        # Lock in registry order so concurrent readers use a consistent order.
        db.scalars(
            select(KnowledgeSource.id)
            .where(KnowledgeSource.id.in_({citation.source_id for citation in result.citations}))
            .order_by(KnowledgeSource.id)
            .with_for_update(read=True)
        ).all()
        passages = {}
        for citation in result.citations:
            passage = _resolve_applicable_passage(db, citation, scope)
            if passage is None:
                break
            passages[citation.passage_id] = passage
        else:
            if _claims_supported(result, scope.claim_reviews, passages, language):
                if result.verification_status != "verified":
                    return result
                if result.claims:
                    return _render_verified_answer(result, language)
            support_missing = True
    if support_missing:
        explanation = (
            "The available sources do not establish the proposed claims. Review the case details."
            if language == "en" else
            "Le fonti disponibili non confermano le affermazioni proposte. Rivedi i dati della pratica."
        )
    else:
        explanation = (
            "I could not verify that the cited evidence is current and applies to this case. Review the case details."
            if language == "en" else
            "Non ho potuto verificare che le fonti citate siano aggiornate e applicabili alla pratica. Rivedi i dati."
        )
    return AnswerResult(
        explanation=explanation,
        verification_status="insufficient_evidence",
        missing_information=result.missing_information,
        next_action=NextAction(
            label="Review the case details" if language == "en" else "Rivedi i dati della pratica",
            operation="provide_information",
        ),
    )
