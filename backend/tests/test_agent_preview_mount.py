"""Fail closed unless the Phase 4 agent transport is pinned to isolated Preview."""
import base64
from dataclasses import replace
from hashlib import sha256

import pytest

from app.agent.preview_mount import REVIEWED_PREVIEW_BRANCH, validate_agent_preview_settings
from app.config import Settings
from app.main import create_app


DATABASE = "postgresql+psycopg://synthetic:local@localhost:5432/isolated_agent_test"
DOCUMENT_KEY = base64.b64encode(bytes(range(32))).decode()
JOURNAL_KEY = base64.b64encode(bytes(range(32, 64))).decode()


def preview_settings() -> Settings:
    return Settings(
        database_url=DATABASE,
        enable_task_api=True,
        enable_knowledge_catalog_api=True,
        enable_preparation_api=True,
        enable_agent_history_api=True,
        enable_agent_preview_api=True,
        deployment_environment="preview",
        deployment_git_branch=REVIEWED_PREVIEW_BRANCH,
        preparation_target="isolated_staging",
        preparation_database_fingerprint=sha256(DATABASE.encode()).hexdigest(),
        preparation_document_key=DOCUMENT_KEY,
        agent_preview_journal_key=JOURNAL_KEY,
        auth_issuer="https://preview-identity.invalid/",
        auth_audience="https://api.preview-identity.invalid",
        auth_jwks_url="https://preview-identity.invalid/.well-known/jwks.json",
    )


def test_default_off_keeps_app_without_conversation_transport(client):
    assert validate_agent_preview_settings(Settings()) is None
    assert client.get("/api/v1/agent/conversations/recent").status_code == 404
    assert client.post("/api/v1/agent/conversations", json={}).status_code == 404


def test_only_reviewed_preview_target_with_separate_encryption_key_can_mount():
    settings = preview_settings()
    assert validate_agent_preview_settings(settings) == bytes(range(32, 64))


@pytest.mark.parametrize("field,value", [
    ("deployment_environment", ""),
    ("deployment_environment", "production"),
    ("deployment_environment", "development"),
    ("deployment_git_branch", ""),
    ("deployment_git_branch", "main"),
    ("deployment_git_branch", "preview/other"),
    ("enable_task_api", False),
    ("enable_knowledge_catalog_api", False),
    ("enable_preparation_api", False),
    ("enable_agent_history_api", False),
    ("preparation_target", "production"),
    ("preparation_database_fingerprint", ""),
    ("preparation_database_fingerprint", "a" * 64),
    ("agent_preview_journal_key", ""),
    ("agent_preview_journal_key", "not-base64"),
    ("agent_preview_journal_key", DOCUMENT_KEY),
    ("auth_issuer", ""),
    ("auth_audience", ""),
    ("auth_jwks_url", ""),
    ("database_url", "sqlite+pysqlite:///tmp/agent.db"),
    ("database_url", "postgresql://live.example/main"),
])
def test_preview_agent_rejects_every_unreviewed_configuration(field, value):
    settings = replace(preview_settings(), **{field: value})
    with pytest.raises(ValueError):
        validate_agent_preview_settings(settings)


def test_unsafe_preview_configuration_aborts_startup_before_database_connect():
    with pytest.raises(ValueError, match="Preview"):
        create_app(replace(preview_settings(), deployment_environment="production"))
    with pytest.raises(ValueError, match="journal and preparation"):
        create_app(replace(preview_settings(), agent_preview_journal_key=DOCUMENT_KEY))
