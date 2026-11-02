"""One open case. The client does not write the stop."""
import secrets

from fastapi import APIRouter, Request
from sqlalchemy import text
from starlette.exceptions import HTTPException

from auth import COOKIE, _body, _caller, engine

router = APIRouter()
ANSWERS = ("language", "f02", "f03", "f04", "f05", "f06")
REQUIRED = ("language", "f02", "f03", "f04", "f05")
LISTS = {
    "language": {"English", "Italian"},
    "f02": {"Yes"},
    "f03": {"Owner, alone", "named tenant, alone"},
    "f05": {"Owner", "named tenant"},
    "f06": {"Yes"},
}
PUBLIC = ("id", "stop", "language", "f02", "f03", "f04", "f05", "f06", "missing_field")


def _accepted(body, creating):
    allowed = set(ANSWERS)
    if creating:
        allowed.add("person_id")
        person_id = body.get("person_id")
        if not isinstance(person_id, str) or not person_id:
            return False
        if not set(REQUIRED) <= set(body):
            return False
    if not set(body) <= allowed:
        return False
    for key in ANSWERS:
        if key not in body:
            continue
        value = body[key]
        if not isinstance(value, str):
            return False
        if key == "f04":
            if "Milano" not in value:
                return False
        elif value not in LISTS[key]:
            return False
    return True


def _load_case(conn, case_id, person_id):
    return conn.execute(
        text(
            """
            SELECT id, stop, language, f02, f03, f04, f05, f06, missing_field
            FROM "case"
            WHERE id = :id AND person_id = :person_id
            """
        ),
        {"id": case_id, "person_id": person_id},
    ).mappings().first()


def _public(row):
    return {key: row[key] for key in PUBLIC}


def _audit(conn, case_id, action):
    conn.execute(
        text(
            "INSERT INTO audit_event (id, case_id, action) VALUES (:id, :case_id, :action)"
        ),
        {"id": secrets.token_urlsafe(), "case_id": case_id, "action": action},
    )


@router.post("/v1/case")
async def open_case(request: Request):
    body = await _body(request)
    if not _accepted(body, True):
        raise HTTPException(status_code=400)
    person_id = body["person_id"]
    if request.cookies.get(COOKIE):
        _session_id, caller, _case_id = _caller(request)
        if caller != person_id:
            raise HTTPException(status_code=404)
    with engine.begin() as conn:
        person = conn.execute(
            text("SELECT id FROM person WHERE id = :id"),
            {"id": person_id},
        ).first()
        if person is None:
            raise HTTPException(status_code=404)
        existing = conn.execute(
            text('SELECT id FROM "case" WHERE person_id = :id AND open'),
            {"id": person_id},
        ).first()
        if existing is not None:
            raise HTTPException(status_code=400)
        case_id = secrets.token_urlsafe()
        conn.execute(
            text(
                """
                INSERT INTO "case"
                    (id, person_id, language, f02, f03, f04, f05, f06, stop)
                VALUES
                    (:id, :person_id, :language, :f02, :f03, :f04, :f05, :f06, 'not ready')
                """
            ),
            {
                "id": case_id,
                "person_id": person_id,
                "language": body["language"],
                "f02": body["f02"],
                "f03": body["f03"],
                "f04": body["f04"],
                "f05": body["f05"],
                "f06": body.get("f06"),
            },
        )
        _audit(conn, case_id, "opened")
        row = _load_case(conn, case_id, person_id)
    return _public(row)


@router.get("/v1/case/{case_id}")
def read_case(case_id: str, request: Request):
    _session_id, person_id, _case_id = _caller(request)
    with engine.begin() as conn:
        row = _load_case(conn, case_id, person_id)
    if row is None:
        raise HTTPException(status_code=404)
    return _public(row)


@router.patch("/v1/case/{case_id}")
async def update_case(case_id: str, request: Request):
    _session_id, person_id, _case_id = _caller(request)
    body = await _body(request)
    if not _accepted(body, False):
        raise HTTPException(status_code=400)
    with engine.begin() as conn:
        row = _load_case(conn, case_id, person_id)
        if row is not None:
            sets = []
            params = {"id": case_id}
            for key in ANSWERS:
                if key in body and row[key] != body[key]:
                    sets.append("%s = :%s" % (key, key))
                    params[key] = body[key]
            if sets:
                conn.execute(
                    text('UPDATE "case" SET %s WHERE id = :id' % ", ".join(sets)),
                    params,
                )
                _audit(conn, case_id, "answer saved")
            row = _load_case(conn, case_id, person_id)
    if row is None:
        raise HTTPException(status_code=404)
    return _public(row)
