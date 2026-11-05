"""Unit tests for ranking metrics; independent of live LLMs and networks."""
import pytest

from app.knowledge.retrieval_eval import score_query, summarize


def test_positive_case_recall_and_first_relevant_rank():
    result = score_query(
        case_id="ranked", expected_citations={"a", "b"},
        returned_citations=["unrelated", "b", "a"], k=3,
    )
    assert result.recall_at_k == 1.0
    assert result.reciprocal_rank == 0.5
    assert result.correct_abstention is None


def test_partial_recall_and_complete_miss():
    partial = score_query(
        case_id="partial", expected_citations={"a", "b"},
        returned_citations=["b"], k=2,
    )
    missed = score_query(
        case_id="missed", expected_citations={"a"},
        returned_citations=[], k=5,
    )
    assert partial.recall_at_k == 0.5
    assert partial.reciprocal_rank == 1.0
    assert missed.recall_at_k == 0.0
    assert missed.reciprocal_rank == 0.0


def test_negative_cases_measure_abstention_separately():
    clean = score_query(
        case_id="abstain", expected_citations=set(),
        returned_citations=[], k=5,
    )
    leaked = score_query(
        case_id="unexpected", expected_citations=set(),
        returned_citations=["irrelevant"], k=5,
    )
    report = summarize([clean, leaked])
    assert clean.correct_abstention is True
    assert leaked.correct_abstention is False
    assert report.positive_cases == 0
    assert report.negative_cases == 2
    assert report.recall_at_k is None
    assert report.mrr_at_k is None
    assert report.negative_abstention_rate == 0.5


def test_report_averages_cases_not_raw_hits():
    report = summarize([
        score_query(case_id="one", expected_citations={"a"},
                    returned_citations=["a"], k=2),
        score_query(case_id="two", expected_citations={"b"},
                    returned_citations=[], k=2),
        score_query(case_id="none", expected_citations=set(),
                    returned_citations=[], k=2),
    ])
    assert report.positive_cases == 2
    assert report.negative_cases == 1
    assert report.recall_at_k == 0.5
    assert report.mrr_at_k == 0.5
    assert report.negative_abstention_rate == 1.0


@pytest.mark.parametrize("bad", [
    {"case_id": "", "expected_citations": {"a"}, "returned_citations": [], "k": 1},
    {"case_id": "bad-k", "expected_citations": {"a"}, "returned_citations": [], "k": 11},
    {"case_id": "duplicates", "expected_citations": {"a"},
     "returned_citations": ["a", "a"], "k": 2},
    {"case_id": "overflow", "expected_citations": {"a"},
     "returned_citations": ["a", "b"], "k": 1},
])
def test_malformed_eval_data_fails(bad):
    with pytest.raises(ValueError):
        score_query(**bad)


def test_empty_and_duplicate_suite_rejected():
    item = score_query(
        case_id="same", expected_citations={"a"},
        returned_citations=["a"], k=1,
    )
    with pytest.raises(ValueError):
        summarize([])
    with pytest.raises(ValueError):
        summarize([item, item])
