from datetime import datetime, timezone
from uuid import uuid4

from app.store import Conversation, Message


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryChatStore:
    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._messages: dict[str, list[Message]] = {}

    def insert_conversation(self, user_id: str, title: str) -> Conversation:
        conv_id = str(uuid4())
        now = _now()
        conv: Conversation = {
            "id": conv_id,
            "user_id": user_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
        }
        self._conversations[conv_id] = conv
        return conv

    def list_conversations(self, user_id: str) -> list[Conversation]:
        rows = [c for c in self._conversations.values() if c["user_id"] == user_id]
        return sorted(rows, key=lambda c: c["updated_at"], reverse=True)

    def get_conversation(self, user_id: str, conversation_id: str) -> Conversation | None:
        conv = self._conversations.get(conversation_id)
        if conv is None or conv["user_id"] != user_id:
            return None
        return conv

    def rename_conversation(
        self, user_id: str, conversation_id: str, title: str
    ) -> Conversation | None:
        conv = self.get_conversation(user_id, conversation_id)
        if conv is None:
            return None
        updated: Conversation = {**conv, "title": title, "updated_at": _now()}
        self._conversations[conversation_id] = updated
        return updated

    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        if self.get_conversation(user_id, conversation_id) is None:
            return False
        del self._conversations[conversation_id]
        self._messages.pop(conversation_id, None)
        return True

    def list_messages(self, conversation_id: str) -> list[Message]:
        return list(self._messages.get(conversation_id, []))

    def insert_message(
        self, conversation_id: str, role: str, content: str, citations: list
    ) -> Message:
        msg_id = str(uuid4())
        now = _now()
        msg: Message = {
            "id": msg_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "citations": citations,
            "created_at": now,
        }
        self._messages.setdefault(conversation_id, []).append(msg)
        if conversation_id in self._conversations:
            self._conversations[conversation_id] = {
                **self._conversations[conversation_id],
                "updated_at": now,
            }
        return msg

    def touch(self, conversation_id: str, title: str | None) -> None:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            return
        updated: Conversation = {**conv, "updated_at": _now()}
        if title is not None:
            updated["title"] = title
        self._conversations[conversation_id] = updated