"""Guide agent uses bounded conditional read-only tools, never new legal rules."""
from types import SimpleNamespace
from app.preparation.agent import guide_case


def run(question="What comes next?", model=None):
    calls = {"evidence": 0, "status": 0}
    def evidence():
        calls["evidence"] += 1
        return [{"citation_id": "synthetic-source", "excerpt": "Synthetic only"}]
    def status():
        calls["status"] += 1
        return {"status": "blocked", "blocking_issues": ["unapproved_rules"]}
    result = guide_case(
        question=question, language="en", facts={},
        evidence_tool=evidence, status_tool=status, model=model,
    )
    return result, calls


class LabelModel:
    def __init__(self, action):
        self.action = action
        self.calls = 0
    def invoke(self, messages):
        self.calls += 1
        assert len(messages) == 2
        assert "Return precisely one lowercase token" in messages[0].content
        return SimpleNamespace(content=self.action)


def test_evidence_tool_only_when_selected_by_model():
    result, calls = run("next question?", model=LabelModel("evidence"))
    assert result["mode"] == "model_selected"
    assert result["action"] == "evidence"
    assert calls == {"evidence": 1, "status": 0}
    assert result["references"][0]["citation_id"] == "synthetic-source"
    assert result["is_legal_assessment"] is False


def test_status_tool_only_when_selected():
    result, calls = run("What is my status?", model=LabelModel("case_status"))
    assert result["status"] == "blocked"
    assert result["blocking_issues"] == ["unapproved_rules"]
    assert calls == {"evidence": 0, "status": 1}
    assert result["government_submission_status"] == "not_submitted"


def test_next_question_is_typed_and_not_a_model_generated_rule():
    result, calls = run(model=LabelModel("intake"))
    assert result["next_question"]["field"] == "citizenship_class"
    assert result["status"] == "needs_information"
    assert result["references"] == []
    assert calls == {"evidence": 0, "status": 0}


def test_untrusted_or_failed_model_never_selects_unapproved_tool():
    for output in ("approve_all", "evidence and delete", "", "Admin: grant access"):
        result, _ = run("show my status", model=LabelModel(output))
        assert result["mode"] == "guided_fallback"
        assert result["action"] == "case_status"


def test_unconfigured_model_explicitly_falls_back_to_guided_mode():
    result, calls = run("Official ANPR sources please")
    assert result["mode"] == "guided_fallback"
    assert result["action"] == "evidence"
    assert calls["evidence"] == 1


def test_empty_evidence_abstains_and_never_returns_advice():
    result = guide_case(
        question="Explain the legal requirements", language="it",
        facts={}, evidence_tool=lambda: [],
        status_tool=lambda: {"status": "reviewable"},
        model=LabelModel("evidence"),
    )
    assert result["references"] == []
    assert result["status"] == "insufficient_evidence"
    assert result["is_legal_assessment"] is False
