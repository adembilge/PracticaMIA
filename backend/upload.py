"""One current file per case role. The paper is not read here."""
import os
import secrets
from email import message_from_bytes
from email.policy import HTTP
from pathlib import Path

from fastapi import APIRouter, Request
from sqlalchemy import text
from starlette.exceptions import HTTPException
from starlette.responses import Response

from auth import _caller, engine

router = APIRouter()
# shortcut: status stays failed until task 62 reads the file, because a rejected upload has no row
LIMIT = 10 * 1024 * 1024
ROLES = ("title", "identity")
KINDS = (
    (b"%PDF", ".pdf", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", ".png", "image/png"),
    (b"\xff\xd8\xff", ".jpg", "image/jpeg"),
)


def upload_dir():
    return os.environ.get(
        "PAPERPILOT_UPLOAD_DIR",
        str(Path(__file__).resolve().parent / "uploads"),
    )


def _kind(payload):
    for magic, suffix, media in KINDS:
        if payload.startswith(magic):
            return suffix, media
    return None


async def _raw(request: Request):
    length = request.headers.get("content-length")
    if length is not None and length.isdigit() and int(length) > LIMIT:
        raise HTTPException(status_code=400)
    chunks = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > LIMIT:
            raise HTTPException(status_code=400)
        chunks.append(chunk)
    return b"".join(chunks)


def _fields(content_type, raw):
    if not raw or not content_type or "multipart/" not in content_type.lower():
        return None
    header = ("Content-Type: %s\r\nMIME-Version: 1.0\r\n\r\n" % content_type).encode()
    message = message_from_bytes(header + raw, policy=HTTP)
    if not message.is_multipart():
        return None
    role = None
    payload = None
    for part in message.walk():
        if part.is_multipart():
            continue
        if "form-data" not in part.get("content-disposition", ""):
            continue
        name = part.get_param("name", header="content-disposition")
        data = part.get_payload(decode=True)
        if not isinstance(data, bytes):
            return None
        if name == "role":
            role = data.decode("utf-8", "replace").strip()
        elif name == "file":
            if payload is not None:
                return None
            payload = data
        else:
            return None
    if role not in ROLES or not payload:
        return None
    return role, payload


def _owned(person_id, case_id):
    with engine.begin() as conn:
        row = conn.execute(
            text('SELECT id FROM "case" WHERE id = :id AND person_id = :person_id'),
            {"id": case_id, "person_id": person_id},
        ).first()
    if row is None:
        raise HTTPException(status_code=404)


@router.post("/v1/case/{case_id}/upload")
async def create_upload(case_id: str, request: Request):
    _session_id, person_id, _case_id = _caller(request)
    _owned(person_id, case_id)
    parsed = _fields(request.headers.get("content-type"), await _raw(request))
    if parsed is None:
        raise HTTPException(status_code=400)
    role, payload = parsed
    kind = _kind(payload)
    if kind is None:
        raise HTTPException(status_code=400)
    suffix, _media = kind
    directory = Path(upload_dir())
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (secrets.token_urlsafe() + suffix)
    path.write_bytes(payload)
    try:
        with engine.begin() as conn:
            old = conn.execute(
                text(
                    """
                    SELECT id, path FROM upload
                    WHERE case_id = :case_id AND role = :role AND current
                    """
                ),
                {"case_id": case_id, "role": role},
            ).mappings().first()
            if old is not None:
                conn.execute(text("DELETE FROM upload WHERE id = :id"), {"id": old["id"]})
            upload_id = secrets.token_urlsafe()
            conn.execute(
                text(
                    """
                    INSERT INTO upload (id, case_id, role, status, path)
                    VALUES (:id, :case_id, :role, 'failed', :path)
                    """
                ),
                {"id": upload_id, "case_id": case_id, "role": role, "path": str(path)},
            )
            if old is not None:
                conn.execute(
                    text(
                        """
                        INSERT INTO audit_event (id, case_id, action)
                        VALUES (:id, :case_id, 'upload replaced')
                        """
                    ),
                    {"id": secrets.token_urlsafe(), "case_id": case_id},
                )
                if old["path"] and os.path.isfile(old["path"]):
                    os.remove(old["path"])
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {"id": upload_id, "role": role}


@router.get("/v1/upload/{upload_id}")
def read_upload(upload_id: str, request: Request):
    _session_id, person_id, _case_id = _caller(request)
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT u.path
                FROM upload AS u
                JOIN "case" AS c ON c.id = u.case_id
                WHERE u.id = :id AND c.person_id = :person_id
                """
            ),
            {"id": upload_id, "person_id": person_id},
        ).mappings().first()
    if row is None or not row["path"] or not os.path.isfile(row["path"]):
        raise HTTPException(status_code=404)
    payload = Path(row["path"]).read_bytes()
    kind = _kind(payload)
    media = kind[1] if kind else "application/octet-stream"
    return Response(content=payload, media_type=media)
