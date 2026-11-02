"""One message, then the existing decision. The message is not stored."""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request, Response
from sqlalchemy import text
from starlette.exceptions import HTTPException

from auth import COOKIE, SESSION_HOURS, _body, engine
from case import ANSWERS, _accepted, _insert, _public
from intake import blank, turn
from intent import read
from procedure import ABROAD, select

router = APIRouter()
LIMIT = 8
OPENING = (
    "This release handles one adult changing address inside Milan. "
    "You submit the declaration yourself."
)
PASSWORD = "I will not take your SPID password."
QUESTIONS = {
    "f02": "Are you already registered as a resident of Milano?",
    "f03": (
        "Who is named on the lease or the ownership paper, "
        "and whether the declaration is only for her?"
    ),
    "f04": "New address",
    "f05": "Owner or named tenant",
}
HOUSEHOLD = (
    "ANPR requires the other adult to confirm with her own identity, "
    "that a permit update goes through the Questura path, "
    "and that Milan's TARI page is separate."
)


def _messages(body):
    if set(body) != {"messages"}:
        return None
    messages = body["messages"]
    if not isinstance(messages, list) or not messages or len(messages) > LIMIT:
        return None
    if any(not isinstance(item, str) or not item.strip() for item in messages):
        return None
    return messages


def _scenario(messages):
    found = None
    for message in messages:
        record = read(message)
        if record["scenario"]:
            found = record["scenario"]
    return found


def _guidance(messages, found):
    scenario = _scenario(messages)
    if scenario == "U-02":
        return HOUSEHOLD
    if scenario == "U-03" or found.get("door") == "English or Italian":
        return "Continue in English or Italian."
    door = found.get("door")
    if door == ABROAD:
        return (
            "I will not open the address-change case. The door is the "
            + door
            + ". I will not add the steps."
        )
    if door:
        return (
            "I will not open the address-change case. The door is "
            + door
            + ". I will not add the steps."
        )
    return "I will not open the address-change case. I will not add the steps."


def _facts(messages):
    case = blank()
    for message in messages:
        case = turn(case, message)
    return case


def _save(facts):
    body = {}
    for key in ANSWERS:
        value = facts.get(key)
        if isinstance(value, str):
            body[key] = value
    person_id = secrets.token_urlsafe()
    body["person_id"] = person_id
    if not _accepted(body, True):
        return None, None
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO person (id) VALUES (:id)"), {"id": person_id})
        row = _insert(conn, person_id, body)
        session_id = secrets.token_urlsafe()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
        conn.execute(
            text(
                "INSERT INTO session (id, case_id, expires_at) VALUES (:id, :case_id, :expires_at)"
            ),
            {"id": session_id, "case_id": row["id"], "expires_at": expires_at},
        )
    return _public(row), session_id


@router.post("/v1/onboarding")
async def begin(request: Request, response: Response):
    messages = _messages(await _body(request))
    if messages is None:
        raise HTTPException(status_code=400)
    if any("password" in item.lower() for item in messages):
        return {"case": None, "text": PASSWORD}
    case = _facts(messages)
    found = select(case["facts"])
    if found["decision"] == "open":
        public, session_id = _save(case["facts"])
        if public is None:
            return {"case": None, "text": "Error."}
        response.set_cookie(COOKIE, session_id, httponly=True, samesite="lax")
        return {"case": public, "text": OPENING}
    if found["decision"] == "no case":
        return {"case": None, "text": _guidance(messages, found)}
    if case["asking"] in QUESTIONS:
        return {"case": None, "text": QUESTIONS[case["asking"]]}
    return {"case": None, "text": "Error."}
