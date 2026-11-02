"""Health routes and the session. No credential is stored."""
import logging

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from auth import router as auth_router
from case import router as case_router
from ingest import router as ingest_router
from source import router as source_router
from upload import router as upload_router

log = logging.getLogger("app")
router = APIRouter()
ERRORS = {
    400: ("rejected", "That field is not accepted."),
    401: ("unauthorized", "The session is not valid."),
    404: ("not_found", "Not found."),
    405: ("method_not_allowed", "Method not allowed."),
}


@router.get("/health")
@router.get("/v1/health")
def health():
    return {"status": "ok"}


def http_error(request: Request, exc: HTTPException):
    code, message = ERRORS.get(exc.status_code, ("error", "Error."))
    log.info("%s %s", exc.status_code, request.url.path)
    return JSONResponse(status_code=exc.status_code, content={"code": code, "message": message})


app = FastAPI(exception_handlers={HTTPException: http_error})
app.include_router(router)
app.include_router(auth_router)
app.include_router(case_router)
app.include_router(upload_router)
app.include_router(source_router)
app.include_router(ingest_router)
