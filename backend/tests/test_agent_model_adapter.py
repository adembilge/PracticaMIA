"""Offline contract tests for the case-free, privacy-bounded model selector."""
import json
from types import SimpleNamespace

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.agent.model_adapter import ModelReferenceSelector
from app.config import Settings

KEY = "unit-test-only-case-free-usage-secret-32-bytes"
PASSAGE_ID = "123e4567-e89b-12d3-a456-426614174000:0000"


def _settings(**overrides):
    values = {
        "deployment_environment": "preview",
        "deployment_git_branch": "preview/auth-review-isolated",
        "enable_case_free_agent_model": True,
        "assistant_model_privacy_approved": True,
        "assistant_chat_model": "test-model",
        "assistant_llm_provider": "openai",
        "assistant_openai_api_key": "test-key-not-used",
        "assistant_usage_hash_key": KEY,
        "assistant_daily_limit": 2,
    }
    values.update(overrides)
    return Settings(**values)


def _passage(passage_id=PASSAGE_ID):
    return SimpleNamespace(
        passage_id=passage_id,
        title="Cambio di residenza",
        section_path="Servizi > Residenza",
        content="Testo pubblico approvato per una verifica sintetica della procedura.",
    )


def _factory(output, calls):
    def invoke(prompt):
        calls.append(prompt.to_string())
        return AIMessage(content=output)
    return lambda: RunnableLambda(invoke)


def test_selector_receives_only_bounded_topic_and_public_evidence(client):
    calls = []
    selector = ModelReferenceSelector(
        client.app.state.session_factory, _settings(),
        model_factory=_factory(json.dumps([PASSAGE_ID]), calls),
    )

    selected = selector.select(
        owner_subject="auth0|synthetic-user",
        topic_category="residenza",
        passages=[_passage()],
    )

    assert selected == (PASSAGE_ID,)
    assert len(calls) == 1
    assert "Topic category: residenza" in calls[0]
    assert "Testo pubblico approvato" in calls[0]
    assert "auth0|synthetic-user" not in calls[0]
    assert "private@example.test" not in calls[0]
    assert "passport number" not in calls[0]


def test_selector_reserves_quota_before_provider_invocation(client):
    calls = []
    selector = ModelReferenceSelector(
        client.app.state.session_factory,
        _settings(assistant_daily_limit=1),
        model_factory=_factory(json.dumps([PASSAGE_ID]), calls),
    )

    assert selector.select(
        owner_subject="auth0|same-user",
        topic_category="residenza",
        passages=[_passage()],
    ) == (PASSAGE_ID,)
    assert selector.select(
        owner_subject="auth0|same-user",
        topic_category="residenza",
        passages=[_passage()],
    ) is None
    assert len(calls) == 1


def test_selector_rejects_unapproved_ids_and_duplicate_ids(client):
    for output in (json.dumps(["not-a-candidate"]), json.dumps([PASSAGE_ID, PASSAGE_ID]), "not-json"):
        calls = []
        selector = ModelReferenceSelector(
            client.app.state.session_factory, _settings(),
            model_factory=_factory(output, calls),
        )
        assert selector.select(
            owner_subject="auth0|synthetic-user",
            topic_category="residenza",
            passages=[_passage()],
        ) is None


def test_selector_can_abstain_without_inventing_a_reference(client):
    calls = []
    selector = ModelReferenceSelector(
        client.app.state.session_factory, _settings(),
        model_factory=_factory("[]", calls),
    )
    assert selector.select(
        owner_subject="auth0|synthetic-user",
        topic_category="residenza",
        passages=[_passage()],
    ) == ()


def test_selector_is_disabled_without_both_privacy_gates_or_isolated_preview(client):
    for settings in (
        _settings(assistant_model_privacy_approved=False),
        _settings(enable_case_free_agent_model=False),
        _settings(deployment_git_branch="main"),
        _settings(deployment_environment="production"),
        _settings(assistant_openai_api_key=""),
        _settings(assistant_chat_model=""),
    ):
        factory_calls = []
        selector = ModelReferenceSelector(
            client.app.state.session_factory, settings,
            model_factory=lambda: factory_calls.append("constructed"),
        )
        assert selector.select(
            owner_subject="auth0|synthetic-user",
            topic_category="residenza",
            passages=[_passage()],
        ) is None
        assert factory_calls == []


def test_selector_rejects_unbounded_categories_and_candidate_lists(client):
    calls = []
    selector = ModelReferenceSelector(
        client.app.state.session_factory, _settings(),
        model_factory=_factory(json.dumps([PASSAGE_ID]), calls),
    )
    assert selector.select(
        owner_subject="auth0|synthetic-user",
        topic_category="user supplied free text",
        passages=[_passage()],
    ) is None
    assert selector.select(
        owner_subject="auth0|synthetic-user",
        topic_category="residenza",
        passages=[_passage(str(index) + ":0000") for index in range(6)],
    ) is None
    assert calls == []

def test_selector_falls_back_cleanly_when_provider_invocation_fails(client):
    def fail(_prompt):
        raise TimeoutError("synthetic provider timeout")

    selector = ModelReferenceSelector(
        client.app.state.session_factory, _settings(),
        model_factory=lambda: RunnableLambda(fail),
    )
    assert selector.select(
        owner_subject="auth0|synthetic-user",
        topic_category="residenza",
        passages=[_passage()],
    ) is None

