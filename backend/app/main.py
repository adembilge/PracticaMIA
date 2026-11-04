"""App factory for development-only authenticated, synthetic case persistence."""
from fastapi import FastAPI

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
    if settings.enable_knowledge_catalog_api and not settings.enable_demo_case_api:
        raise ValueError("Knowledge catalog requires the authenticated case API")

    @api.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "practicamia-backend"}

    if settings.enable_demo_case_api:
        # Fail closed at startup rather than exposing anonymous case routes.
        from app.auth.tokens import TokenVerifier
        from app.cases.router import router

        api.state.token_verifier = TokenVerifier(settings)
        engine, session_factory = configure_database(settings.database_url)
        api.state.engine = engine
        api.state.session_factory = session_factory
        api.include_router(router)
        if settings.enable_knowledge_catalog_api:
            from app.knowledge.router import router as knowledge_router
            api.include_router(knowledge_router)

    return api


app = create_app()
