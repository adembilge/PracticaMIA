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


def _load_session(conn, session_id):
    return conn.execute(
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


def _expired(row):
    return row["expires_at"] is not None and _aware(row["expires_at"]) <= datetime.now(timezone.utc)


def _caller(request):
    session_id = request.cookies.get(COOKIE)
    if not session_id:
        raise HTTPException(status_code=401)
    with engine.begin() as conn:
        row = _load_session(conn, session_id)
        if row is not None and _expired(row):
            conn.execute(text("DELETE FROM session WHERE id = :id"), {"id": session_id})
            row = None
    if row is None:
        raise HTTPException(status_code=401)
    return session_id, row["person_id"], row["case_id"]


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


@router.get("/v1/person")
def read_person(request: Request):
    _session_id, person_id, _case_id = _caller(request)
    return {"id": person_id}


@router.patch("/v1/person")
async def update_person(request: Request):
    _session_id, person_id, _case_id = _caller(request)
    if await _body(request):
        raise HTTPException(status_code=400)
    return {"id": person_id}


@router.delete("/v1/person")
def delete_person(request: Request, response: Response):
    _session_id, person_id, _case_id = _caller(request)
    with engine.begin() as conn:
        paths = conn.execute(
            text(
                """
                SELECT u.path
                FROM upload AS u
                JOIN "case" AS c ON c.id = u.case_id
                WHERE c.person_id = :person_id
                """
            ),
            {"person_id": person_id},
        ).scalars().all()
        conn.execute(text("DELETE FROM person WHERE id = :id"), {"id": person_id})
        for path in paths:
            if path and os.path.isfile(path):
                os.remove(path)
    response.delete_cookie(COOKIE)
    return {"status": "ok"}


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
    _session_id, person_id, case_id = _caller(request)
    return {"person_id": person_id, "case_id": case_id}


@router.delete("/v1/session/{session_id}")
def close_named_session(session_id: str, request: Request, response: Response):
    cookie_id, person_id, _case_id = _caller(request)
    with engine.begin() as conn:
        row = _load_session(conn, session_id)
        if row is None or row["person_id"] != person_id:
            owned = False
        else:
            conn.execute(text("DELETE FROM session WHERE id = :id"), {"id": session_id})
            owned = True
    if not owned:
        raise HTTPException(status_code=404)
    if cookie_id == session_id:
        response.delete_cookie(COOKIE)
    return {"status": "ok"}


@router.delete("/v1/session")
def close_session(request: Request, response: Response):
    session_id = request.cookies.get(COOKIE)
    if session_id:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM session WHERE id = :id"), {"id": session_id})
    response.delete_cookie(COOKIE)
    return {"status": "ok"}
