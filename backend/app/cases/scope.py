"""First-route scope classification; NOT government eligibility decisions."""

FIRST_ROUTE_SCOPE_ANSWERS = ("yes", "yes", "yes", "no", "yes")


def classify_scope(answers: list[str]) -> str:
    """Mirror frontend/src/lib/flow.js, including prefix/uncertain behavior."""
    for index, expected in enumerate(FIRST_ROUTE_SCOPE_ANSWERS):
        if index >= len(answers):
            return "incomplete"
        if answers[index] == "unsure":
            return "needs_information"
        if answers[index] != expected:
            return "unsupported"
    return "provisionally_in_scope"
