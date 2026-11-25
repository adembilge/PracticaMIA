from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.auth import current_user_id
from app.store import Conversation, get_store

router = APIRouter()


class TitleBody(BaseModel):
    title: str
    model_config = ConfigDict(extra="ignore")


def clean_title(title: str) -> str:
    value = " ".join(title.split())
    if not value:
        raise HTTPException(
            status_code=400,
            detail={"code": "bad_request", "message": "Title is required."},
        )
    if len(value) > 60:
        raise HTTPException(
            status_code=400,
            detail={"code": "bad_request", "message": "Title is too long."},
        )
    return value


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "not_found", "message": "Chat not found."},
    )


@router.post("/api/conversations", status_code=201)
async def create_conversation(
    body: TitleBody,
    user_id: UUID = Depends(current_user_id),
) -> Conversation:
    store = get_store()
    title = clean_title(body.title)
    return store.insert_conversation(str(user_id), title)


@router.get("/api/conversations")
async def list_conversations(
    user_id: UUID = Depends(current_user_id),
) -> list[Conversation]:
    store = get_store()
    return store.list_conversations(str(user_id))


@router.patch("/api/conversations/{conversation_id}")
async def rename_conversation(
    conversation_id: str,
    body: TitleBody,
    user_id: UUID = Depends(current_user_id),
) -> Conversation:
    store = get_store()
    title = clean_title(body.title)
    updated = store.rename_conversation(str(user_id), conversation_id, title)
    if updated is None:
        raise _not_found()
    return updated


@router.delete("/api/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    user_id: UUID = Depends(current_user_id),
) -> None:
    store = get_store()
    if not store.delete_conversation(str(user_id), conversation_id):
        raise _not_found()