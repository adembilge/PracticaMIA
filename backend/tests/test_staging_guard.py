"""Prevent accidental live knowledge-source imports from both CLIs."""
import pytest
from sqlalchemy.engine import make_url

from app.knowledge.staging_guard import (
    require_pilot_preview_target, require_staging_database, require_staging_intent,
)


@pytest.mark.parametrize("environment", [
    {}, {"PRACTICAMIA_KNOWLEDGE_TARGET": "production"},
    {"PRACTICAMIA_KNOWLEDGE_TARGET": ""},
    {"PRACTICAMIA_KNOWLEDGE_TARGET": "staging", "VERCEL_ENV": "production"},
])
def test_knowledge_import_rejects_nonstaging_or_production_settings(environment):
    with pytest.raises(ValueError):
        require_staging_intent(environment)


def test_knowledge_import_accepts_explicit_preview_staging_only():
    require_staging_intent({
        "PRACTICAMIA_KNOWLEDGE_TARGET": "staging",
        "VERCEL_ENV": "preview",
    })


def test_non_postgres_database_cannot_be_used_for_official_import(client):
    with client.app.state.session_factory() as db:
        with pytest.raises(ValueError, match="PostgreSQL staging"):
            require_staging_database(db)


@pytest.mark.parametrize("url", [
    "sqlite:///preview-test.db",
    "postgresql://production.example/pilot",
    "postgresql://preview.example/main",
    "postgresql://preview.example:5433/pilot",
    "postgresql://preview.example/pilot?host=production.example",
    "postgresql://preview.example/pilot?dbname=production",
])
def test_pilot_import_rejects_mismatched_or_redirected_targets(url):
    with pytest.raises(ValueError, match="verified direct preview"):
        require_pilot_preview_target(make_url(url), {
            "PRACTICAMIA_KNOWLEDGE_TARGET": "staging",
            "PRACTICAMIA_PILOT_PREVIEW_HOST": "preview.example",
            "PRACTICAMIA_PILOT_PREVIEW_DATABASE": "pilot",
        })


def test_pilot_import_requires_the_separately_confirmed_direct_preview_target():
    environment = {
        "PRACTICAMIA_KNOWLEDGE_TARGET": "staging",
        "PRACTICAMIA_PILOT_PREVIEW_HOST": "preview.example",
        "PRACTICAMIA_PILOT_PREVIEW_DATABASE": "pilot",
    }
    url = make_url("postgresql://preview.example/pilot?sslmode=require")
    require_pilot_preview_target(url, environment)
    with pytest.raises(ValueError, match="production"):
        require_pilot_preview_target(url, {**environment, "VERCEL_ENV": "production"})
    with pytest.raises(ValueError, match="verified direct preview"):
        require_pilot_preview_target(make_url("postgresql://preview-pooler.example/pilot"), {
            **environment, "PRACTICAMIA_PILOT_PREVIEW_HOST": "preview-pooler.example",
        })
