"""Health routes only. No case call."""
import logging

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

log = logging.getLogger("app")
router = APIRouter()
ERRORS = {
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
