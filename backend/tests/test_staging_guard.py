"""Prevent accidental live knowledge-source imports from both CLIs."""
import pytest

from app.knowledge.staging_guard import (
    require_staging_database, require_staging_intent,
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
