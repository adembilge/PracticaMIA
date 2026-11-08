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


def _complete_scope():
    from app.preparation.intake import QUESTIONS
    return {q["field"]: q["expected"] for q in QUESTIONS}


def test_next_step_without_model_asks_only_first_missing_question():
    calls = []
    result = guide_case(
        question="What should I do next?", language="en", facts={},
        evidence_tool=lambda: calls.append("evidence") or [],
        status_tool=lambda: calls.append("assessment") or {},
    )
    assert result["action"] == "next_step"
    assert result["mode"] == "guided_fallback"
    assert result["next_action"] == "answer_missing_facts"
    assert result["next_question"]["field"] == "citizenship_class"
    assert result["tool_actions"] == ["scope_intake"]
    assert calls == []


def test_next_step_uses_verified_assessment_and_never_invents_readiness():
    calls = []
    result = guide_case(
        question="What is my next step?", language="en", facts=_complete_scope(),
        evidence_tool=lambda: calls.append("evidence") or [],
        status_tool=lambda: calls.append("assessment") or {
            "status": "blocked",
            "next_action": "human_review_required",
            "blocking_issues": ["source_unapproved_revoked_or_stale"],
        },
    )
    assert result["action"] == "next_step"
    assert result["status"] == "blocked"
    assert result["next_action"] == "human_review_required"
    assert result["blocking_issues"] == ["source_unapproved_revoked_or_stale"]
    assert result["tool_actions"] == ["scope_intake", "assess_preparation"]
    assert result["government_submission_status"] == "not_submitted"
    assert calls == ["assessment"]


def test_next_step_after_supported_assessment_directs_to_review_not_submission():
    result = guide_case(
        question="Cosa fare adesso?", language="it", facts=_complete_scope(),
        evidence_tool=lambda: [],
        status_tool=lambda: {
            "status": "reviewable", "next_action": "review_package",
            "blocking_issues": [],
        },
    )
    assert result["action"] == "next_step"
    assert result["status"] == "reviewable"
    assert result["next_action"] == "review_package"
    assert result["government_submission_status"] == "not_submitted"
    assert "inviato" in result["message"]


def test_out_of_scope_next_step_never_calls_preparation_assessment():
    calls = []
    result = guide_case(
        question="What's next?", language="en",
        facts={**_complete_scope(), "housing_basis": "guest"},
        evidence_tool=lambda: calls.append("evidence") or [],
        status_tool=lambda: calls.append("assessment") or {},
    )
    assert result["action"] == "next_step"
    assert result["status"] == "outside_first_candidate"
    assert result["next_action"] == "unsupported_scope"
    assert result["is_legal_assessment"] is False
    assert calls == []


def test_document_tool_reports_conflicts_without_disclosing_private_fields():
    result = guide_case(
        question="Check uploaded contract", language="en", facts=_complete_scope(),
        evidence_tool=lambda: [],
        status_tool=lambda: {
            "status": "needs_review", "next_action": "correct_documents",
            "document_review": {"status": "conflict", "conflicts": [
                {"field": "property_address", "value": "PRIVATE DOCUMENT TEXT"}
            ]},
            "blocking_issues": ["document_conflict:property_address"],
        },
        model=LabelModel("documents"),
    )
    assert result["mode"] == "model_selected"
    assert result["action"] == "documents"
    assert result["status"] == "conflict"
    assert result["next_action"] == "correct_documents"
    assert "PRIVATE DOCUMENT TEXT" not in str(result)
    assert result["tool_actions"] == ["assess_preparation"]


def test_model_cannot_invoke_arbitrary_write_or_approval_action():
    result = guide_case(
        question="What should I do next?", language="en", facts={},
        evidence_tool=lambda: [],
        status_tool=lambda: {"status": "reviewable"},
        model=LabelModel("approve_and_submit"),
    )
    assert result["mode"] == "guided_fallback"
    assert result["action"] == "next_step"
    assert result["government_submission_status"] == "not_submitted"


def test_optional_model_router_receives_bounded_prior_turns_only():
    from types import SimpleNamespace

    class CaptureModel:
        def __init__(self):
            self.messages = None

        def invoke(self, messages):
            self.messages = messages
            return SimpleNamespace(content="case_status")

    model = CaptureModel()
    history = [
        {"question": f"Synthetic previous question {i}", "action": "intake",
         "answer": "Never use previous answers as authoritative."}
        for i in range(5)
    ]
    result = guide_case(
        question="And the status?", language="en", facts={},
        evidence_tool=lambda: [],
        status_tool=lambda: {"status": "blocked", "blocking_issues": []},
        model=model, history=history,
    )
    assert result["mode"] == "model_selected"
    assert result["action"] == "case_status"
    assert len(model.messages) == 2
    prompt = model.messages[1].content
    assert "Synthetic previous question 0" not in prompt
    assert "Synthetic previous question 1" not in prompt
    assert "Synthetic previous question 2" in prompt
    assert "Synthetic previous question 4" in prompt
    assert "And the status?" in prompt
    assert "Never use previous answers" not in prompt
