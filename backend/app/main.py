"""App factory for development-only authenticated, synthetic case persistence."""
from fastapi import FastAPI, HTTPException, Request, Response
from os import environ

from app.config import Settings
from app.database import configure_database


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    api = FastAPI(
        title="PracticaMIA Backend",
        description="Development-only API. No official eligibility or submission.",
        version="0.2.0",
    )
    api.state.settings = settings

    @api.middleware("http")
    async def basic_security_headers(request, call_next):
        # API JSON responses do not require Next.js inline-script CSP policy.
        # These headers apply even to rejected and unexpected routes.
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        return response
    if settings.enable_agent_history_api and not settings.enable_preparation_api:
        raise ValueError("Agent history requires isolated preparation Preview")
    if settings.enable_preparation_api:
        # No production access to personal-document processing until independent
        # privacy, malware, retention, and legal review gates are complete.
        if settings.deployment_environment == "production":
            raise ValueError("Preparation preview must never be enabled in production")
        if settings.preparation_target != "isolated_staging":
            raise ValueError("Preparation requires explicit isolated staging target")
        if not (settings.enable_demo_case_api and settings.enable_knowledge_catalog_api):
            raise ValueError("Preparation requires authenticated cases and source registry")
        from app.preparation.crypto import decode_key
        api.state.preparation_document_key = decode_key(settings.preparation_document_key)
    if settings.enable_knowledge_catalog_api and not settings.enable_demo_case_api:
        raise ValueError("Knowledge catalog requires the authenticated case API")
    if settings.enable_knowledge_search_api and not (
        settings.enable_demo_case_api and settings.enable_knowledge_catalog_api
    ):
        raise ValueError("Knowledge search requires the authenticated knowledge catalog")
    if settings.enable_assistant_api:
        if settings.deployment_environment == "production":
            raise ValueError("The RAG preview cannot be enabled in production")
        if len(settings.assistant_usage_hash_key) < 32:
            raise ValueError("Assistant requires a dedicated usage HMAC key")
        if not 1 <= settings.assistant_daily_limit <= 50:
            raise ValueError("Assistant daily limit must be between 1 and 50")
        if not (settings.enable_demo_case_api and settings.enable_knowledge_catalog_api
                and settings.enable_knowledge_search_api):
            raise ValueError("Assistant requires authenticated case and knowledge search APIs")
    if settings.enable_knowledge_review_api:
        if not settings.enable_knowledge_catalog_api or not settings.enable_demo_case_api:
            raise ValueError("Knowledge review requires the authenticated knowledge catalog")
        if not settings.knowledge_reviewer_subjects:
            raise ValueError("Knowledge review requires an explicit reviewer subject allowlist")
        if any(not subject.strip() or len(subject) > 255
               for subject in settings.knowledge_reviewer_subjects):
            raise ValueError("Reviewer subject identifiers must be valid")

    @api.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "practicamia-backend"}

    if settings.enable_demo_case_api:
        # Fail closed at startup rather than exposing anonymous case routes.
        from app.auth.tokens import TokenVerifier
        from app.cases.router import router

        api.state.token_verifier = TokenVerifier(settings)
        engine, session_factory = configure_database(settings.database_url)
        if settings.enable_preparation_api and engine.dialect.name == "postgresql":
            from hashlib import sha256
            from hmac import compare_digest
            expected = settings.preparation_database_fingerprint
            actual = sha256(settings.database_url.encode("utf-8")).hexdigest()
            if len(expected) != 64 or not compare_digest(expected, actual):
                engine.dispose()
                raise ValueError("Preparation requires explicit staging database fingerprint")
            try:
                with engine.connect() as connection:
                    revision = connection.exec_driver_sql(
                        "SELECT version_num FROM alembic_version"
                    ).scalar_one()
                if revision not in {"20261106_0011", "20261108_0012"}:
                    raise ValueError("Preparation requires migrated isolated staging schema")
                if settings.enable_agent_history_api and revision != "20261108_0012":
                    raise ValueError("Agent history requires isolated staging schema 0012")
            except Exception:
                engine.dispose()
                raise
        api.state.engine = engine
        api.state.session_factory = session_factory
        api.include_router(router)
        if settings.enable_preparation_api:
            from app.preparation.router import router as preparation_router
            api.include_router(preparation_router)
        if settings.enable_knowledge_catalog_api:
            from app.knowledge.router import router as knowledge_router
            api.include_router(knowledge_router)
            if settings.enable_knowledge_search_api:
                from app.knowledge.search_router import router as search_router
                api.include_router(search_router)
            if settings.enable_assistant_api:
                from app.knowledge.assistant_router import router as assistant_router
                api.include_router(assistant_router)
            if settings.enable_knowledge_review_api:
                from app.knowledge.review_router import router as review_router
                api.include_router(review_router)

    # Temporary isolated Preview smoke check: synthetic prompt only.
    # This route is removed immediately after verification and is never on
    # Production; access requires a separate high-entropy one-time token.
    smoke_token = environ.get("OPENROUTER_SMOKE_TOKEN", "")
    if (
        settings.deployment_environment == "preview"
        and settings.enable_assistant_api
        and len(smoke_token) >= 32
    ):
        @api.get("/__internal/openrouter-smoke", include_in_schema=False)
        def synthetic_model_smoke(request: Request, response: Response, token: str):
            from hmac import compare_digest
            from app.knowledge.assistant_router import _model_for_preview

            response.headers["Cache-Control"] = "no-store"
            if not compare_digest(token, smoke_token):
                raise HTTPException(404, "Not found")
            model = _model_for_preview(request)
            if model is None:
                return {"status": "model_not_configured"}
            try:
                generated = model.invoke(
                    "Synthetic connection test. Reply with exactly: PracticaMIA TEST OK"
                )
                content = generated.content
                if not isinstance(content, str):
                    content = str(content)
                return {
                    "status": "answer_generated" if content.strip() else "empty_response",
                    "model": settings.assistant_chat_model,
                    "provider": settings.assistant_llm_provider,
                    "answer": content[:180],
                    "synthetic_only": True,
                }
            except Exception as exc:
                # Never include provider response bodies, request headers, or secrets.
                return {"status": "provider_error", "error_type": type(exc).__name__}

    return api


app = create_app()
