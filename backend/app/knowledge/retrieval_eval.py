"""Deterministic retrieval metrics for curated, source-versioned evidence fixtures.

This module evaluates ranked citation IDs. It does not judge legal correctness,
create ground-truth labels, or approve official sources. Positive cases measure
Recall@K and reciprocal rank; negative cases measure safe abstention.
"""
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class QueryScore:
    case_id: str
    expected_count: int
    returned_count: int
    recall_at_k: float | None
    reciprocal_rank: float | None
    correct_abstention: bool | None


@dataclass(frozen=True)
class RetrievalReport:
    positive_cases: int
    negative_cases: int
    recall_at_k: float | None
    mrr_at_k: float | None
    negative_abstention_rate: float | None


def score_query(
    *, case_id: str, expected_citations: set[str],
    returned_citations: Sequence[str], k: int,
) -> QueryScore:
    """Score a fully ranked top-K retrieval result against reviewed labels.

    A positive query with no results scores zero recall and reciprocal rank.
    A negative query with any result fails abstention (no precision inflation).
    """
    if not case_id.strip() or not 1 <= k <= 10:
        raise ValueError("Case ID and a K between 1 and 10 are required")
    if not all(expected_citations) or not all(returned_citations):
        raise ValueError("Citation IDs must be nonempty")
    if len(returned_citations) > k or len(set(returned_citations)) != len(returned_citations):
        raise ValueError("Top-K results must be bounded and unique")

    returned = tuple(returned_citations)
    if not expected_citations:
        return QueryScore(case_id, 0, len(returned), None, None, not returned)

    hits = expected_citations.intersection(returned)
    first = next(
        (index for index, citation in enumerate(returned, start=1)
         if citation in expected_citations), None
    )
    return QueryScore(
        case_id=case_id, expected_count=len(expected_citations),
        returned_count=len(returned),
        recall_at_k=len(hits) / len(expected_citations),
        reciprocal_rank=1.0 / first if first is not None else 0.0,
        correct_abstention=None,
    )


def summarize(scores: Sequence[QueryScore]) -> RetrievalReport:
    """Macro-average across cases, keeping positive and negative cases distinct."""
    if not scores or len({score.case_id for score in scores}) != len(scores):
        raise ValueError("Need a nonempty suite with unique case IDs")
    positive = [score for score in scores if score.expected_count > 0]
    negative = [score for score in scores if score.expected_count == 0]
    return RetrievalReport(
        positive_cases=len(positive), negative_cases=len(negative),
        recall_at_k=(
            sum(score.recall_at_k for score in positive) / len(positive)
            if positive else None
        ),
        mrr_at_k=(
            sum(score.reciprocal_rank for score in positive) / len(positive)
            if positive else None
        ),
        negative_abstention_rate=(
            sum(score.correct_abstention is True for score in negative) / len(negative)
            if negative else None
        ),
    )
