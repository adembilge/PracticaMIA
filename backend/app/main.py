from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.config import get_settings
from app.db import get_supabase

app = FastAPI(title="PracticaMIA")
STATIC_DIR = Path(__file__).resolve().parent / "static"


def probe_db() -> str:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return "unconfigured"
    try:
        get_supabase().table("global_usage_daily").select("day").limit(1).execute()
    except Exception:
        return "down"
    return "ok"


@app.get("/api/health")
def health() -> dict[str, str]:
    db = probe_db()
    status = "degraded" if db == "down" else "ok"
    return {"status": status, "db": db}


def register_spa(application: FastAPI) -> None:
    index = STATIC_DIR / "index.html"
    if not index.exists():
        return

    @application.get("/", include_in_schema=False)
    def spa_root():
        return FileResponse(index)

    @application.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return {"code": "not_found", "message": "Not found."}
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)


register_spa(app)
