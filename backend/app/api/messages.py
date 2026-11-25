import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.auth import current_user_id
from app.store import Message, get_store

ITALIAN_MARKERS = ("come", "che", "per", "non", "sono", "il", "la")

ITALIAN_HOLDING = (
    "La domanda è salvata. L'archivio ufficiale non è ancora collegato."
)
ENGLISH_HOLDING = (
    "Your question is saved. The official archive is not connected yet."
)

router = APIRouter()

_MAX_QUESTION_LEN = 8000


class ContentBody(BaseModel):
    content: str
    model_config = ConfigDict(extra="ignore")


def holding_answer(content: str) -> str:
    lowered = content.lower()
    matches = sum(
        1
        for word in ITALIAN_MARKERS
        if re.search(rf"\b{word}\b", lowered)
    )
    if matches >= 2:
        return ITALIAN_HOLDING
    return ENGLISH_HOLDING


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "not_found", "message": "Chat not found."},
    )


def _title_from_question(content: str) -> str:
    value = " ".join(content.split())
    return value[:60]


def validate_content(content: str) -> None:
    if not content.strip():
        raise HTTPException(
            status_code=400,
            detail={"code": "bad_request", "message": "Question is required."},
        )
    if len(content) > _MAX_QUESTION_LEN:
        raise HTTPException(
            status_code=400,
            detail={"code": "bad_request", "message": "Question is too long."},
        )


def save_turn(user_id: UUID, conversation_id: str, content: str) -> Message:
    store = get_store()
    conv = store.get_conversation(str(user_id), conversation_id)
    if conv is None:
        raise _not_found()
    store.insert_message(conversation_id, "user", content, [])
    assistant = holding_answer(content)
    message = store.insert_message(conversation_id, "assistant", assistant, [])
    title = (
        _title_from_question(content) if conv["title"] == "New chat" else None
    )
    store.touch(conversation_id, title)
    return message


@router.get("/api/conversations/{conversation_id}/messages")
async def list_conversation_messages(
    conversation_id: str,
    user_id: UUID = Depends(current_user_id),
) -> list[Message]:
    store = get_store()
    if store.get_conversation(str(user_id), conversation_id) is None:
        raise _not_found()
    return store.list_messages(conversation_id)


@router.post("/api/conversations/{conversation_id}/messages")
async def post_conversation_message(
    conversation_id: str,
    body: ContentBody,
    user_id: UUID = Depends(current_user_id),
) -> Message:
    validate_content(body.content)
    return save_turn(user_id, conversation_id, body.content)