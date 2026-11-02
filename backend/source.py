"""Government source rows. Review does not promote the document."""
import secrets

from fastapi import APIRouter, Request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException

from auth import _body, _caller, engine

router = APIRouter()
# shortcut: any session may register a source, add a role when one exists.


def _document(conn, document_id):
    return conn.execute(
        text("SELECT id, review_status FROM source_document WHERE id = :id"),
        {"id": document_id},
    ).mappings().first()


def _version(conn, document_id, version_id):
    return conn.execute(
        text(
            """
            SELECT id FROM source_version
            WHERE id = :version_id AND source_document_id = :document_id
            """
        ),
        {"version_id": version_id, "document_id": document_id},
    ).first()


@router.post("/v1/source")
async def register_source(request: Request):
    _caller(request)
    body = await _body(request)
    source_id = body.get("id")
    if set(body) != {"id"} or not isinstance(source_id, str) or not source_id:
        raise HTTPException(status_code=400)
    try:
        with engine.begin() as conn:
            if _document(conn, source_id) is not None:
                raise HTTPException(status_code=400)
            conn.execute(
                text(
                    "INSERT INTO source_document (id, review_status) "
                    "VALUES (:id, 'unreviewed')"
                ),
                {"id": source_id},
            )
    except IntegrityError:
        raise HTTPException(status_code=400)
    return {"id": source_id, "review_status": "unreviewed"}


@router.post("/v1/source/{document_id}/version")
async def add_version(document_id: str, request: Request):
    _caller(request)
    if await _body(request):
        raise HTTPException(status_code=400)
    version_id = secrets.token_urlsafe()
    with engine.begin() as conn:
        if _document(conn, document_id) is None:
            raise HTTPException(status_code=404)
        conn.execute(
            text(
                """
                INSERT INTO source_version (id, source_document_id, review_status)
                VALUES (:id, :document_id, 'unreviewed')
                """
            ),
            {"id": version_id, "document_id": document_id},
        )
    return {"id": version_id, "review_status": "unreviewed"}


@router.post("/v1/source/{document_id}/version/{version_id}/review")
async def review_version(document_id: str, version_id: str, request: Request):
    _caller(request)
    if await _body(request):
        raise HTTPException(status_code=400)
    try:
        with engine.begin() as conn:
            if _document(conn, document_id) is None:
                raise HTTPException(status_code=404)
            if _version(conn, document_id, version_id) is None:
                raise HTTPException(status_code=404)
            other = conn.execute(
                text(
                    """
                    SELECT id FROM source_version
                    WHERE source_document_id = :document_id
                      AND review_status = 'trusted'
                      AND id <> :version_id
                    """
                ),
                {"document_id": document_id, "version_id": version_id},
            ).first()
            if other is not None:
                raise HTTPException(status_code=400)
            conn.execute(
                text(
                    """
                    UPDATE source_version
                    SET review_status = 'trusted'
                    WHERE id = :version_id AND source_document_id = :document_id
                    """
                ),
                {"version_id": version_id, "document_id": document_id},
            )
    except IntegrityError:
        raise HTTPException(status_code=400)
    return {"id": version_id, "review_status": "trusted"}


@router.post("/v1/source/{document_id}/version/{version_id}/invalidate")
async def invalidate_version(document_id: str, version_id: str, request: Request):
    _caller(request)
    if await _body(request):
        raise HTTPException(status_code=400)
    with engine.begin() as conn:
        if _version(conn, document_id, version_id) is None:
            raise HTTPException(status_code=404)
        conn.execute(
            text(
                """
                UPDATE source_version
                SET review_status = 'unreviewed'
                WHERE id = :version_id AND source_document_id = :document_id
                """
            ),
            {"version_id": version_id, "document_id": document_id},
        )
    return {"id": version_id, "review_status": "unreviewed"}


@router.get("/v1/source/{document_id}")
def read_source(document_id: str, request: Request):
    _caller(request)
    with engine.begin() as conn:
        document = _document(conn, document_id)
        if document is None:
            raise HTTPException(status_code=404)
        versions = conn.execute(
            text(
                """
                SELECT id, review_status FROM source_version
                WHERE source_document_id = :id
                ORDER BY id
                """
            ),
            {"id": document_id},
        ).mappings().all()
    return {
        "id": document["id"],
        "review_status": document["review_status"],
        "versions": [
            {"id": row["id"], "review_status": row["review_status"]} for row in versions
        ],
    }
