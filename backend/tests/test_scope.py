"""Status labels match frontend/src/lib/flow.js; not legal eligibility rules."""
import pytest

from app.cases.scope import FIRST_ROUTE_SCOPE_ANSWERS, classify_scope


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        ([], "incomplete"),
        (["yes", "yes"], "incomplete"),
        (["unsure"], "needs_information"),
        (["yes", "no"], "unsupported"),
        (["yes", "yes", "yes", "yes"], "unsupported"),
        (list(FIRST_ROUTE_SCOPE_ANSWERS), "provisionally_in_scope"),
    ],
)
def test_first_route_scope_classification(answers, expected):
    assert classify_scope(answers) == expected


def test_first_route_scope_answers_remain_the_reviewed_contract():
    assert FIRST_ROUTE_SCOPE_ANSWERS == ("yes", "yes", "yes", "no", "yes")
