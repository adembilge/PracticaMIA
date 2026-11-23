"""Explicit safety gate for mounting authenticated Phase 4 agent routes in staging.

The API exposes durable encrypted conversation transport only. A separately
authorised and deployed worker is required to process queued runs. This module
never launches a worker, approves official sources or enables real documents.
"""
from hashlib import sha256
from hmac import compare_digest

from sqlalchemy.engine import make_url

from app.config import Settings
from app.preparation.crypto import decode_key

REVIEWED_PREVIEW_BRANCH = "preview/auth-review-isolated"


def validate_agent_preview_settings(settings: Settings) -> bytes | None:
    """Return the journal encryption key only for a pinned isolated Preview.

    Configuration mistakes abort startup. A deployed server cannot silently
    expose an agent endpoint to production, another branch or another database.
    """
    if not settings.enable_agent_preview_api:
        return None
    if settings.deployment_environment != "preview":
        raise ValueError("Agent transport requires Vercel Preview; production is forbidden")
    if settings.deployment_git_branch != REVIEWED_PREVIEW_BRANCH:
        raise ValueError("Agent transport requires the isolated reviewed Preview branch")
    if not all((
        settings.enable_task_api,
        settings.enable_knowledge_catalog_api,
        settings.enable_preparation_api,
        settings.enable_agent_history_api,
    )):
        raise ValueError("Agent transport requires authenticated staging task API, catalogue, preparation and history")
    if settings.preparation_target != "isolated_staging":
        raise ValueError("Agent transport requires isolated staging")
    if not all((settings.auth_issuer, settings.auth_audience, settings.auth_jwks_url)):
        raise ValueError("Agent transport requires configured issuer, audience and JWKS")
    try:
        url = make_url(settings.database_url)
    except Exception as exc:
        raise ValueError("Agent transport requires a valid PostgreSQL database URL") from exc
    if url.drivername not in {"postgresql", "postgresql+psycopg"} or not url.database or not url.host:
        raise ValueError("Agent transport requires a dedicated PostgreSQL staging database")
    # An explicit fingerprint binds this service to the already reviewed
    # isolation target, not just to a vaguely named staging database.
    actual = sha256(settings.database_url.encode("utf-8")).hexdigest()
    if len(settings.preparation_database_fingerprint) != 64 or not compare_digest(
        settings.preparation_database_fingerprint, actual,
    ):
        raise ValueError("Agent transport staging database fingerprint mismatch")
    key = decode_key(settings.agent_preview_journal_key)
    document_key = decode_key(settings.preparation_document_key)
    if compare_digest(key, document_key):
        raise ValueError("Agent journal and preparation document keys must be different")
    return key
