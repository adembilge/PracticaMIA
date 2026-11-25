from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.messages import holding_answer
from app.main import http_exception_handler
from memory_store import MemoryChatStore


def test_holding_answer_italian():
    text = holding_answer("Come posso chiedere il permesso?")
    assert text.startswith("La domanda")


def test_holding_answer_english():
    text = holding_answer("How do I renew a permit?")
    assert text.startswith("Your question")


def _client(monkeypatch, user_id: UUID, store: MemoryChatStore | None = None) -> tuple[TestClient, MemoryChatStore]:
    store = store or MemoryChatStore()

    monkeypatch.setattr("app.api.messages.get_store", lambda: store)

    async def fake_user() -> UUID:
        return user_id

    monkeypatch.setattr("app.api.messages.current_user_id", fake_user)

    from app.auth import current_user_id as auth_current_user_id
    from app.api.messages import router

    application = FastAPI()
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.dependency_overrides[auth_current_user_id] = fake_user
    application.include_router(router)
    return TestClient(application), store


def test_post_saves_user_then_assistant_in_order(monkeypatch):
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "New chat")
    conv_id = conv["id"]

    posted = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Come cambio residenza oggi subito?"},
    )
    assert posted.status_code == 200
    body = posted.json()
    assert body["role"] == "assistant"
    assert body["citations"] == []

    listed = client.get(f"/api/conversations/{conv_id}/messages")
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 2
    assert rows[0]["role"] == "user"
    assert rows[0]["content"] == "Come cambio residenza oggi subito?"
    assert rows[1]["role"] == "assistant"
    assert rows[1]["id"] == body["id"]


def test_new_chat_title_from_first_question(monkeypatch):
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "New chat")
    conv_id = conv["id"]

    client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Come cambio residenza oggi subito?"},
    )

    updated = store.get_conversation(str(user_id), conv_id)
    assert updated is not None
    assert updated["title"] == "Come cambio residenza oggi subito?"


def test_new_chat_title_truncated_to_60(monkeypatch):
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "New chat")
    conv_id = conv["id"]
    question = "a" * 70

    client.post(f"/api/conversations/{conv_id}/messages", json={"content": question})

    updated = store.get_conversation(str(user_id), conv_id)
    assert updated is not None
    assert updated["title"] == "a" * 60


def test_question_too_long_returns_bad_request(monkeypatch):
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "My chat")
    conv_id = conv["id"]

    response = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "a" * 8001},
    )
    assert response.status_code == 400
    assert response.json() == {"code": "bad_request", "message": "Question is too long."}


def test_empty_question_returns_bad_request(monkeypatch):
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "My chat")
    conv_id = conv["id"]

    response = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "  "})
    assert response.status_code == 400
    assert response.json() == {"code": "bad_request", "message": "Question is required."}


def test_messages_not_found_for_missing_chat(monkeypatch):
    user_id = uuid4()
    client, _store = _client(monkeypatch, user_id)
    missing = str(uuid4())

    get_resp = client.get(f"/api/conversations/{missing}/messages")
    assert get_resp.status_code == 404
    assert get_resp.json() == {"code": "not_found", "message": "Chat not found."}

    post_resp = client.post(f"/api/conversations/{missing}/messages", json={"content": "Hi"})
    assert post_resp.status_code == 404
    assert post_resp.json() == {"code": "not_found", "message": "Chat not found."}


def test_messages_not_found_for_other_user(monkeypatch):
    owner = uuid4()
    other = uuid4()
    store = MemoryChatStore()
    conv = store.insert_conversation(str(owner), "Owned")
    conv_id = conv["id"]

    client, _store = _client(monkeypatch, other, store=store)
    response = client.post(f"/api/conversations/{conv_id}/messages", json={"content": "Hi"})
    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "Chat not found."}