"""Provider-selection tests: no real network requests or API credentials."""
from types import SimpleNamespace

import pytest
from app.config import Settings
from app.knowledge.assistant_router import _model_for_preview


def _request(settings: Settings):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=settings)))


def test_openrouter_free_router_uses_compatible_endpoint(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "langchain_openai.ChatOpenAI",
        lambda **kwargs: calls.append(kwargs) or object(),
    )
    result = _model_for_preview(_request(Settings(
        assistant_llm_provider="openrouter",
        assistant_chat_model="openrouter/free",
        assistant_openrouter_api_key="synthetic-test-key",
    )))
    assert result is not None
    assert len(calls) == 1
    assert calls[0]["model"] == "openrouter/free"
    assert calls[0]["api_key"] == "synthetic-test-key"
    assert calls[0]["base_url"] == "https://openrouter.ai/api/v1"
    assert calls[0]["max_retries"] == 0


def test_openrouter_missing_key_does_not_call_model(monkeypatch):
    def forbidden(**kwargs):
        raise AssertionError("Model must not be instantiated")

    monkeypatch.setattr("langchain_openai.ChatOpenAI", forbidden)
    assert _model_for_preview(_request(Settings(
        assistant_llm_provider="openrouter",
        assistant_chat_model="openrouter/free",
    ))) is None


@pytest.mark.parametrize("paid_model", [
    "openai/gpt-4o-mini", "anthropic/claude-sonnet-4", "qwen/qwen3",
])
def test_openrouter_rejects_paid_or_unverified_models(paid_model):
    with pytest.raises(ValueError, match="free model"):
        _model_for_preview(_request(Settings(
            assistant_llm_provider="openrouter",
            assistant_chat_model=paid_model,
            assistant_openrouter_api_key="synthetic-test-key",
        )))


def test_explicit_free_model_allowed(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "langchain_openai.ChatOpenAI",
        lambda **kwargs: calls.append(kwargs) or object(),
    )
    _model_for_preview(_request(Settings(
        assistant_llm_provider="openrouter",
        assistant_chat_model="example/model:free",
        assistant_openrouter_api_key="synthetic-test-key",
    )))
    assert calls[0]["model"] == "example/model:free"


def test_openai_backwards_compatible(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "langchain_openai.ChatOpenAI",
        lambda **kwargs: calls.append(kwargs) or object(),
    )
    _model_for_preview(_request(Settings(
        assistant_chat_model="gpt-4o-mini",
        assistant_openai_api_key="synthetic-test-key",
    )))
    assert calls[0]["model"] == "gpt-4o-mini"
    assert "base_url" not in calls[0]


def test_openrouter_settings_read_from_environment(monkeypatch):
    monkeypatch.setenv("ASSISTANT_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("ASSISTANT_CHAT_MODEL", "openrouter/free")
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-test-key")
    config = Settings.from_env()
    assert config.assistant_llm_provider == "openrouter"
    assert config.assistant_chat_model == "openrouter/free"
    assert config.assistant_openrouter_api_key == "synthetic-test-key"
