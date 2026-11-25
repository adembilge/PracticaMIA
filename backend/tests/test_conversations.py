from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.main import http_exception_handler
from memory_store import MemoryChatStore


def _client(monkeypatch, user_id: UUID, store: MemoryChatStore | None = None) -> TestClient:
    store = store or MemoryChatStore()

    monkeypatch.setattr("app.api.conversations.get_store", lambda: store)

    async def fake_user() -> UUID:
        return user_id

    monkeypatch.setattr("app.api.conversations.current_user_id", fake_user)

    from app.auth import current_user_id as auth_current_user_id
    from app.api.conversations import router

    application = FastAPI()
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.dependency_overrides[auth_current_user_id] = fake_user
    application.include_router(router)
    return TestClient(application)


def test_conversation_crud(monkeypatch):
    user_id = uuid4()
    client = _client(monkeypatch, user_id)

    create = client.post("/api/conversations", json={"title": "  My   chat  "})
    assert create.status_code == 201
    body = create.json()
    assert body["title"] == "My chat"
    assert body["user_id"] == str(user_id)
    conv_id = body["id"]

    listed = client.get("/api/conversations")
    assert listed.status_code == 200
    ids = [row["id"] for row in listed.json()]
    assert ids == [conv_id]

    patched = client.patch(f"/api/conversations/{conv_id}", json={"title": "Renamed"})
    assert patched.status_code == 200
    assert patched.json()["title"] == "Renamed"

    deleted = client.delete(f"/api/conversations/{conv_id}")
    assert deleted.status_code == 204

    assert client.get("/api/conversations").json() == []


def test_delete_other_user_returns_not_found(monkeypatch):
    owner = uuid4()
    other = uuid4()
    store = MemoryChatStore()
    conv = store.insert_conversation(str(owner), "Owned")
    conv_id = conv["id"]

    client = _client(monkeypatch, other, store=store)
    response = client.delete(f"/api/conversations/{conv_id}")
    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "Chat not found."}


def test_title_too_long_returns_bad_request(monkeypatch):
    user_id = uuid4()
    client = _client(monkeypatch, user_id)
    response = client.post("/api/conversations", json={"title": "a" * 61})
    assert response.status_code == 400
    assert response.json() == {"code": "bad_request", "message": "Title is too long."}