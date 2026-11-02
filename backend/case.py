"""One open case. The client does not write the stop."""
import secrets

from fastapi import APIRouter, Request
from sqlalchemy import text
from starlette.exceptions import HTTPException

from auth import COOKIE, _body, _caller, engine
from checklist import from_stored, stored
from prepare import prepare

router = APIRouter()
ANSWERS = ("language", "f02", "f03", "f04", "f05", "f06")
REQUIRED = ("language", "f02", "f04", "f05")
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
        row = _insert(conn, person_id, body)
    return _public(row)


def _insert(conn, person_id, body):
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
            "f03": body.get("f03"),
            "f04": body["f04"],
            "f05": body["f05"],
            "f06": body.get("f06"),
        },
    )
    _audit(conn, case_id, "opened")
    return _load_case(conn, case_id, person_id)


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


def _open_row(conn, case_id, person_id):
    row = conn.execute(
        text(
            """
            SELECT stop, language, f02, f03, f04, f05, f06, named_name, named_address
            FROM "case"
            WHERE id = :id AND person_id = :person_id
            """
        ),
        {"id": case_id, "person_id": person_id},
    ).mappings().first()
    if row is None:
        return None, None
    uploads = conn.execute(
        text(
            """
            SELECT role, status, extracted_name, extracted_address
            FROM upload
            WHERE case_id = :id AND current
            """
        ),
        {"id": case_id},
    ).mappings().all()
    return row, uploads


def _package(row, uploads):
    facts, papers, named = stored(row, uploads)
    found = prepare(facts, papers, named)
    stop = "ready to hand over" if found["ready"] else "not ready"
    missing = ["f07"] if "f07" not in facts else found["missing"]
    language = row["language"]
    body = {
        "stop": stop,
        "missing": missing,
        "name": found["name"],
        "address": found["address"],
        "language": language if language in ("English", "Italian") else None,
        "warnings": found["warnings"],
    }
    if stop == "ready to hand over" and found["link"]:
        body["link"] = found["link"]
        method = "CIE" if language == "Italian" else "SPID"
        body["notice"] = (
            "I will not take your %s password, and I will not file it. "
            "Opening that page is not acceptance by the Comune di Milano."
        ) % method
    return body


def sync_stop(conn, case_id, person_id):
    row, uploads = _open_row(conn, case_id, person_id)
    if row is None:
        return None
    body = _package(row, uploads)
    if row["stop"] != body["stop"]:
        conn.execute(
            text('UPDATE "case" SET stop = :stop WHERE id = :id'),
            {"stop": body["stop"], "id": case_id},
        )
        if body["stop"] == "ready to hand over":
            conn.execute(
                text(
                    """
                    INSERT INTO audit_event (id, case_id, action)
                    VALUES (:id, :case_id, 'stop became ready')
                    """
                ),
                {"id": secrets.token_urlsafe(), "case_id": case_id},
            )
    return body


def _conflict(found):
    warnings = found["warnings"]
    return warnings["name"]["status"] == "conflict" or warnings["address"]["status"] == "conflict"


@router.get("/v1/case/{case_id}/checklist")
def read_checklist(case_id: str, request: Request):
    _session_id, person_id, _case_id = _caller(request)
    with engine.begin() as conn:
        row, uploads = _open_row(conn, case_id, person_id)
    if row is None:
        raise HTTPException(status_code=404)
    found = from_stored(row, uploads)
    return {"stop": row["stop"], "items": found["items"], "missing": found["missing"]}


@router.get("/v1/case/{case_id}/review")
def read_review(case_id: str, request: Request):
    _session_id, person_id, _case_id = _caller(request)
    with engine.begin() as conn:
        body = sync_stop(conn, case_id, person_id)
    if body is None:
        raise HTTPException(status_code=404)
    return body


@router.post("/v1/case/{case_id}/review")
async def name_review(case_id: str, request: Request):
    _session_id, person_id, _case_id = _caller(request)
    body = await _body(request)
    if set(body) != {"name", "address"}:
        raise HTTPException(status_code=400)
    name = body["name"]
    address = body["address"]
    if not isinstance(name, str) or not isinstance(address, str):
        raise HTTPException(status_code=400)
    name = name.strip()
    address = address.strip()
    if not name or not address:
        raise HTTPException(status_code=400)
    with engine.begin() as conn:
        row, uploads = _open_row(conn, case_id, person_id)
        if row is None:
            raise HTTPException(status_code=404)
        facts, papers, _named = stored(row, uploads)
        if not _conflict(prepare(facts, papers, _named)):
            raise HTTPException(status_code=400)
        conn.execute(
            text(
                """
                UPDATE "case"
                SET named_name = :name, named_address = :address
                WHERE id = :id
                """
            ),
            {"id": case_id, "name": name, "address": address},
        )
        return sync_stop(conn, case_id, person_id)
