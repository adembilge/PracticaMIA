"""Opaque person id and a case session. No credential is stored."""
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request, Response
from sqlalchemy import create_engine, text
from starlette.exceptions import HTTPException

router = APIRouter()
COOKIE = "session"
# shortcut: 12 hours, change when a product duration exists
SESSION_HOURS = 12


def database_url():
    host = os.environ.get("PAPERPILOT_DB_HOST", "127.0.0.1")
    port = os.environ.get("PAPERPILOT_DB_PORT", "5432")
    name = os.environ.get("PAPERPILOT_DB_NAME", "paperpilot")
    user = os.environ.get("PAPERPILOT_DB_USER", "postgres")
    return "postgresql+psycopg://%s@%s:%s/%s" % (user, host, port, name)


engine = create_engine(database_url())


def _aware(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


async def _body(request: Request):
    raw = await request.body()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400)
    if not isinstance(data, dict):
        raise HTTPException(status_code=400)
    return data


@router.post("/v1/person")
async def create_person(request: Request):
    if await _body(request):
        raise HTTPException(status_code=400)
    person_id = secrets.token_urlsafe()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO person (id) VALUES (:id)"), {"id": person_id})
    return {"id": person_id}


@router.post("/v1/session")
async def open_session(request: Request, response: Response):
    body = await _body(request)
    if set(body) != {"person_id", "case_id"}:
        raise HTTPException(status_code=400)
    person_id = body["person_id"]
    case_id = body["case_id"]
    with engine.begin() as conn:
        person = conn.execute(
            text("SELECT id FROM person WHERE id = :id"),
            {"id": person_id},
        ).first()
        if person is None:
            raise HTTPException(status_code=404)
        case = conn.execute(
            text('SELECT id FROM "case" WHERE id = :id AND person_id = :person_id'),
            {"id": case_id, "person_id": person_id},
        ).first()
        if case is None:
            raise HTTPException(status_code=404)
        session_id = secrets.token_urlsafe()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
        conn.execute(
            text(
                "INSERT INTO session (id, case_id, expires_at) VALUES (:id, :case_id, :expires_at)"
            ),
            {"id": session_id, "case_id": case_id, "expires_at": expires_at},
        )
    response.set_cookie(COOKIE, session_id, httponly=True, samesite="lax")
    return {"person_id": person_id, "case_id": case_id}


@router.get("/v1/session")
def read_session(request: Request):
    session_id = request.cookies.get(COOKIE)
    if not session_id:
        raise HTTPException(status_code=401)
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT s.expires_at, s.case_id, c.person_id
                FROM session AS s
                JOIN "case" AS c ON c.id = s.case_id
                WHERE s.id = :id
                """
            ),
            {"id": session_id},
        ).mappings().first()
        if row is None:
            found = None
        elif row["expires_at"] is not None and _aware(row["expires_at"]) <= datetime.now(timezone.utc):
            conn.execute(text("DELETE FROM session WHERE id = :id"), {"id": session_id})
            found = None
        else:
            found = {"person_id": row["person_id"], "case_id": row["case_id"]}
    if found is None:
        raise HTTPException(status_code=401)
    return found


@router.delete("/v1/session")
def close_session(request: Request, response: Response):
    session_id = request.cookies.get(COOKIE)
    if session_id:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM session WHERE id = :id"), {"id": session_id})
    response.delete_cookie(COOKIE)
    return {"status": "ok"}
