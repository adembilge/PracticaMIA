"""Strict staged knowledge-write preconditions shared by both import commands."""
from collections.abc import Mapping
from os import environ

from sqlalchemy import text
from sqlalchemy.orm import Session


STAGING_REVISION = "20261106_0010"
SUPPORTED_STAGING_REVISIONS = frozenset({STAGING_REVISION, "20261106_0011", "20261108_0012", "20261109_0013", "20261109_0014", "20261109_0015", "20261109_0016"})


def require_staging_intent(environment: Mapping[str, str] | None = None) -> None:
    """Require an affirmative environment-specific operator choice.

    This is defense in depth: operators MUST ALSO verify the actual Neon
    branch and connection in the Neon console before supplying DATABASE_URL.
    """
    values = environ if environment is None else environment
    if values.get("PRACTICAMIA_KNOWLEDGE_TARGET") != "staging":
        raise ValueError(
            "Set PRACTICAMIA_KNOWLEDGE_TARGET=staging explicitly for imports"
        )
    if values.get("VERCEL_ENV") == "production":
        raise ValueError("Official-source imports are prohibited in Vercel production")


def require_staging_database(db: Session) -> None:
    """A migrated PostgreSQL knowledge DB is required before any write."""
    if db.get_bind().dialect.name != "postgresql":
        raise ValueError("Official-source imports require PostgreSQL staging")
    revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    if revision not in SUPPORTED_STAGING_REVISIONS:
        raise ValueError(
            "Official-source imports require a reviewed staging schema " +
            ", ".join(sorted(SUPPORTED_STAGING_REVISIONS))
        )
