"""Status labels match frontend/src/lib/flow.js; not legal eligibility rules."""
import pytest

from app.cases.scope import classify_scope


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        ([], "incomplete"),
        (["yes", "yes"], "incomplete"),
        (["unsure"], "needs_information"),
        (["yes", "no"], "unsupported"),
        (["yes", "yes", "yes", "yes"], "unsupported"),
        (["yes", "yes", "yes", "no", "yes"], "provisionally_in_scope"),
    ],
)
def test_demo_scope_classification(answers, expected):
    assert classify_scope(answers) == expected
