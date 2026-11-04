"""App factory for local-only milestone 3 development.

Do not enable unauthenticated demo endpoints on any public deployment.
"""
from fastapi import FastAPI

from app.config import Settings
from app.database import configure_database


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    api = FastAPI(
        title="PracticaMIA Backend",
        description="Development-only API. No official eligibility or submission.",
        version="0.1.0",
    )
    api.state.settings = settings

    @api.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "practicamia-backend"}

    if settings.enable_demo_case_api:
        from app.cases.router import router

        engine, session_factory = configure_database(settings.database_url)
        api.state.engine = engine
        api.state.session_factory = session_factory
        api.include_router(router)

    return api


app = create_app()
