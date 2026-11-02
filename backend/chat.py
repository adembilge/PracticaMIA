"""One turn on the open case. The stop is not written here."""
import secrets

from fastapi import APIRouter, Request
from sqlalchemy import text
from starlette.exceptions import HTTPException

from auth import _body, _caller, engine
from case import ANSWERS, _accepted, _audit, _load_case
from intake import turn
from intent import read
from onboard import PASSWORD, QUESTIONS

router = APIRouter()
NOT_STATED = "This release does not state that."
LEASE = "Please upload the lease."
OWNERSHIP = "Please upload the ownership paper."


def _line(body):
    if set(body) != {"text"}:
        return None
    line = body["text"]
    if not isinstance(line, str) or not line.strip():
        return None
    return line.strip()


def _facts(row):
    facts = {}
    for key in ANSWERS:
        value = row[key]
        if isinstance(value, str) and value:
            facts[key] = value
    return facts


def _asking(facts):
    # A blank turn names the missing field. It is not a stored message.
    state = turn({"facts": dict(facts), "asked": [], "asking": None}, " ")
    return state.get("asking")


def _sentence(field, facts):
    if field == "f07":
        if facts.get("f05") == "Owner":
            return OWNERSHIP
        return LEASE
    if field in QUESTIONS:
        return QUESTIONS[field]
    return None


def _listed(conn, case_id):
    return list(
        conn.execute(
            text("SELECT body FROM message WHERE case_id = :id ORDER BY position"),
            {"id": case_id},
        ).scalars().all()
    )


def _append(conn, case_id, bodies):
    start = conn.execute(
        text("SELECT COALESCE(MAX(position), 0) FROM message WHERE case_id = :id"),
        {"id": case_id},
    ).scalar()
    for offset, body in enumerate(bodies, start=1):
        conn.execute(
            text(
                """
                INSERT INTO message (id, case_id, position, body)
                VALUES (:id, :case_id, :position, :body)
                """
            ),
            {
                "id": secrets.token_urlsafe(),
                "case_id": case_id,
                "position": start + offset,
                "body": body,
            },
        )


def _research(line):
    stated = read(line)["stated"]
    return any(stated.get(key) for key in ("deadline", "paper", "sign_in"))


def _view(row, messages):
    facts = _facts(row)
    return {
        "messages": messages,
        "stop": row["stop"],
        "question": _sentence(_asking(facts), facts),
    }


def _owned(request, case_id):
    _session_id, person_id, owned = _caller(request)
    if owned != case_id:
        raise HTTPException(status_code=404)
    return person_id


def _row(conn, case_id, person_id):
    row = _load_case(conn, case_id, person_id)
    if row is None:
        raise HTTPException(status_code=404)
    return row


@router.get("/v1/case/{case_id}/messages")
def read_messages(case_id: str, request: Request):
    person_id = _owned(request, case_id)
    with engine.begin() as conn:
        row = _row(conn, case_id, person_id)
        return _view(row, _listed(conn, case_id))


@router.post("/v1/case/{case_id}/messages")
async def send_message(case_id: str, request: Request):
    line = _line(await _body(request))
    if line is None:
        raise HTTPException(status_code=400)
    person_id = _owned(request, case_id)
    with engine.begin() as conn:
        row = _row(conn, case_id, person_id)
        if "password" in line.lower():
            view = _view(row, _listed(conn, case_id))
            view["text"] = PASSWORD
            return view
        facts = _facts(row)
        if _research(line):
            reply = NOT_STATED
        else:
            asking = _asking(facts)
            reply = _sentence(asking, facts)
            if asking in ANSWERS:
                updated = turn(
                    {"facts": dict(facts), "asked": [], "asking": asking},
                    line,
                )
                value = updated["facts"].get(asking)
                if (
                    isinstance(value, str)
                    and value != facts.get(asking)
                    and _accepted({asking: value}, False)
                ):
                    conn.execute(
                        text('UPDATE "case" SET %s = :value WHERE id = :id' % asking),
                        {"value": value, "id": case_id},
                    )
                    _audit(conn, case_id, "answer saved")
                    row = _row(conn, case_id, person_id)
                    reply = _sentence(_asking(_facts(row)), _facts(row))
        if reply:
            _append(conn, case_id, [line, reply])
        else:
            _append(conn, case_id, [line])
        row = _row(conn, case_id, person_id)
        return _view(row, _listed(conn, case_id))
