"""Revalidate an answer's exact citations against the active registry and case scope."""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.catalogue_evidence import catalogue_passage
from app.agent.contract import (
    MAX_ANSWER_CITATIONS, MAX_ANSWER_CLAIMS, MAX_ANSWER_EXPLANATION_LENGTH,
    AnswerResult, Citation, ClaimKind, EvidenceLinkedClaim, Language, NextAction, OfficialChannel,
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
    assistance_citations: tuple[Citation, ...] = ()


# The reader receives the transaction, thread, run, case, and authenticated principal.
AnswerEvidenceScopeReader = Callable[[Session, UUID, UUID, UUID | None, Principal], AnswerEvidenceScope | None]


@dataclass(frozen=True)
class _ApplicablePassage:
    citation: Citation
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
    return _ApplicablePassage(citation, active.content, frozenset(assignment_ids))


def _claim_passage_applies(review: ClaimPassageSupport, passages: Mapping[str, _ApplicablePassage]) -> bool:
    passage = passages.get(review.passage_id)
    return (
        passage is not None and review.assignment_id in passage.assignments
        and bool(review.quote.strip()) and review.quote in passage.content
    )


def _valid_reviews(
    reviews: tuple[ReviewedClaimSupport, ...],
    passages: Mapping[str, _ApplicablePassage], language: Language,
) -> list[ReviewedClaimSupport]:
    return [
        review for review in reviews
        if review.language == language and review.passages
        and all(_claim_passage_applies(link, passages) for link in review.passages)
    ]


def _claim_key(kind: ClaimKind, statement: str, evidence_ids: Iterable[str]) -> tuple[ClaimKind, str, frozenset[str]]:
    return kind, statement, frozenset(evidence_ids)


def _review_key(review: ReviewedClaimSupport) -> tuple[ClaimKind, str, frozenset[str]]:
    return _claim_key(review.kind, review.statement, (link.passage_id for link in review.passages))


def _supported_claims(
    claims: list[EvidenceLinkedClaim], reviews: list[ReviewedClaimSupport],
) -> tuple[list[EvidenceLinkedClaim], list[OfficialChannel]]:
    keys = {_review_key(review) for review in reviews}
    kept = [claim for claim in claims if _claim_key(claim.kind, claim.statement, claim.evidence_ids) in keys]
    kept_keys = {_claim_key(claim.kind, claim.statement, claim.evidence_ids) for claim in kept}
    channels = [
        review.official_channel for review in reviews
        if review.kind == "channel" and review.official_channel is not None and _review_key(review) in kept_keys
    ]
    return kept, channels


def _recover_channel(
    claims: list[EvidenceLinkedClaim], reviews: list[ReviewedClaimSupport],
) -> OfficialChannel | None:
    options = [
        review
        for review in reviews
        if review.kind == "channel" and review.official_channel is not None
    ]
    if len({(review.official_channel.label, review.official_channel.url) for review in options}) != 1:
        return None
    used_ids = {passage_id for claim in claims for passage_id in claim.evidence_ids}
    kept_keys = {_claim_key(claim.kind, claim.statement, claim.evidence_ids) for claim in claims}
    for review in options:
        if _review_key(review) in kept_keys:
            return review.official_channel
        evidence_ids = list(dict.fromkeys(link.passage_id for link in review.passages))
        if len(claims) < MAX_ANSWER_CLAIMS and len(used_ids.union(evidence_ids)) <= MAX_ANSWER_CITATIONS:
            claims.append(EvidenceLinkedClaim(kind="channel", statement=review.statement, evidence_ids=evidence_ids))
            return review.official_channel
    return None


def _partial_answer(
    result: AnswerResult, claims: list[EvidenceLinkedClaim], citations: list[Citation],
    channel: OfficialChannel | None, language: Language,
) -> AnswerResult:
    notice, confirmation, details = (
        (
            "Some details could not be verified.",
            "Confirm the remaining information with the responsible authority.",
            "Review the missing case details to check which guidance applies.",
        ) if language == "en" else (
            "Alcuni dettagli non sono stati verificati.",
            "Conferma le informazioni rimanenti con l’ente competente.",
            "Rivedi i dati mancanti della pratica per verificare quali indicazioni si applicano.",
        )
    )
    directions = details if result.missing_information else confirmation
    explanation = "\n".join([notice, *(claim.statement for claim in claims), directions])
    if len(explanation) > MAX_ANSWER_EXPLANATION_LENGTH:
        explanation = f"{notice} {directions}"
    operation = "open_official_channel" if channel and not result.missing_information else "provide_information"
    status = (
        result.verification_status if result.verification_status in {"conflicting_evidence", "unsupported"}
        else "insufficient_evidence"
    )
    return AnswerResult(
        explanation=explanation, verification_status=status,
        claims=claims, citations=citations, official_channel=channel, missing_information=result.missing_information,
        next_action=NextAction(label=_ACTION_LABELS[language][operation], operation=operation),
    )


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


def _lock_sources(db: Session, citations: Iterable[Citation]) -> None:
    # Ingestion and review take exclusive locks on these same rows.
    db.scalars(
        select(KnowledgeSource.id)
        .where(KnowledgeSource.id.in_({citation.source_id for citation in citations}))
        .order_by(KnowledgeSource.id)
        .with_for_update(read=True)
    ).all()


def current_channel_evidence(
    db: Session, result: AnswerResult, *, scope: AnswerEvidenceScope | None, language: Language,
) -> list[str]:
    """Find current evidence for the exact official channel in the saved answer."""
    if scope is None or result.official_channel is None:
        return []
    claims = {_claim_key(claim.kind, claim.statement, claim.evidence_ids) for claim in result.claims
              if claim.kind == "channel"}
    reviews = tuple(
        review for review in scope.claim_reviews
        if review.official_channel == result.official_channel and _review_key(review) in claims
    )
    ids = {link.passage_id for review in reviews for link in review.passages}
    citations = [citation for citation in result.citations if citation.passage_id in ids]
    if not citations:
        return []
    _lock_sources(db, citations)
    passages = {
        citation.passage_id: passage for citation in citations
        if (passage := _resolve_applicable_passage(db, citation, scope)) is not None
    }
    supported = {link.passage_id for review in _valid_reviews(reviews, passages, language) for link in review.passages}
    return [citation.passage_id for citation in citations if citation.passage_id in supported]


def revalidate_answer_evidence(
    db: Session, result: AnswerResult, *, scope: AnswerEvidenceScope | None, language: Language,
) -> AnswerResult:
    """Check evidence and reviewed claims while holding the registry stable through commit."""
    if not result.citations:
        return result
    if scope is None:
        return _partial_answer(result, [], [], None, language)

    _lock_sources(db, (*result.citations, *scope.assistance_citations))
    passages = {
        citation.passage_id: passage for citation in result.citations
        if (passage := _resolve_applicable_passage(db, citation, scope)) is not None
    }
    reviews = _valid_reviews(scope.claim_reviews, passages, language)
    claims, channels = _supported_claims(result.claims, reviews)
    channel = result.official_channel if result.official_channel in channels else None
    if (len(passages) == len(result.citations) and len(claims) == len(result.claims)
            and channel == result.official_channel):
        if result.verification_status != "verified":
            return result
        if claims:
            return _render_verified_answer(result, language)

    if channel is None:
        for citation in scope.assistance_citations:
            if citation.passage_id in passages:
                continue
            passage = _resolve_applicable_passage(db, citation, scope)
            if passage is not None:
                passages[citation.passage_id] = passage
        channel = _recover_channel(claims, _valid_reviews(scope.claim_reviews, passages, language))
    retained_ids = {passage_id for claim in claims for passage_id in claim.evidence_ids}
    citations = [passage.citation for passage_id, passage in passages.items() if passage_id in retained_ids]
    return _partial_answer(result, claims, citations, channel, language)
