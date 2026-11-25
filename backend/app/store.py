from datetime import datetime, timezone
from typing import Protocol, TypedDict

from supabase import Client

from app.db import get_supabase


class Conversation(TypedDict):
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str


class Message(TypedDict):
    id: str
    conversation_id: str
    role: str
    content: str
    citations: list
    created_at: str


class ChatStore(Protocol):
    def insert_conversation(self, user_id: str, title: str) -> Conversation: ...
    def list_conversations(self, user_id: str) -> list[Conversation]: ...
    def get_conversation(self, user_id: str, conversation_id: str) -> Conversation | None: ...
    def rename_conversation(
        self, user_id: str, conversation_id: str, title: str
    ) -> Conversation | None: ...
    def delete_conversation(self, user_id: str, conversation_id: str) -> bool: ...
    def list_messages(self, conversation_id: str) -> list[Message]: ...
    def insert_message(
        self, conversation_id: str, role: str, content: str, citations: list
    ) -> Message: ...
    def touch(self, conversation_id: str, title: str | None) -> None: ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseChatStore:
    def __init__(self, client: Client) -> None:
        self._client = client

    def insert_conversation(self, user_id: str, title: str) -> Conversation:
        resp = (
            self._client.table("conversations")
            .insert({"user_id": user_id, "title": title})
            .execute()
        )
        return resp.data[0]

    def list_conversations(self, user_id: str) -> list[Conversation]:
        resp = (
            self._client.table("conversations")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return resp.data or []

    def get_conversation(self, user_id: str, conversation_id: str) -> Conversation | None:
        resp = (
            self._client.table("conversations")
            .select("*")
            .eq("user_id", user_id)
            .eq("id", conversation_id)
            .limit(1)
            .execute()
        )
        if not resp.data:
            return None
        return resp.data[0]

    def rename_conversation(
        self, user_id: str, conversation_id: str, title: str
    ) -> Conversation | None:
        resp = (
            self._client.table("conversations")
            .update({"title": title, "updated_at": _now()})
            .eq("user_id", user_id)
            .eq("id", conversation_id)
            .select()
            .execute()
        )
        if not resp.data:
            return None
        return resp.data[0]

    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        resp = (
            self._client.table("conversations")
            .delete()
            .eq("user_id", user_id)
            .eq("id", conversation_id)
            .execute()
        )
        return bool(resp.data)

    def list_messages(self, conversation_id: str) -> list[Message]:
        resp = (
            self._client.table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at")
            .execute()
        )
        return resp.data or []

    def insert_message(
        self, conversation_id: str, role: str, content: str, citations: list
    ) -> Message:
        resp = (
            self._client.table("messages")
            .insert(
                {
                    "conversation_id": conversation_id,
                    "role": role,
                    "content": content,
                    "citations": citations,
                }
            )
            .execute()
        )
        msg = resp.data[0]
        self._client.table("conversations").update({"updated_at": _now()}).eq(
            "id", conversation_id
        ).execute()
        return msg

    def touch(self, conversation_id: str, title: str | None) -> None:
        payload: dict = {"updated_at": _now()}
        if title is not None:
            payload["title"] = title
        self._client.table("conversations").update(payload).eq(
            "id", conversation_id
        ).execute()


def get_store() -> ChatStore:
    return SupabaseChatStore(get_supabase())