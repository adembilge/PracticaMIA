from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.main import http_exception_handler
from memory_store import MemoryChatStore


def _client(
    monkeypatch, user_id: UUID, store: MemoryChatStore | None = None
) -> tuple[TestClient, MemoryChatStore]:
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
    return TestClient(application), store


def test_conversation_crud(monkeypatch):
    user_id = uuid4()
    client, _store = _client(monkeypatch, user_id)

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

    client, _store = _client(monkeypatch, other, store=store)
    response = client.delete(f"/api/conversations/{conv_id}")
    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "Chat not found."}


def test_title_too_long_returns_bad_request(monkeypatch):
    user_id = uuid4()
    client, _store = _client(monkeypatch, user_id)
    response = client.post("/api/conversations", json={"title": "a" * 61})
    assert response.status_code == 400
    assert response.json() == {"code": "bad_request", "message": "Title is too long."}


def _messages_client(monkeypatch, user_id: UUID, store: MemoryChatStore):
    monkeypatch.setattr("app.api.messages.get_store", lambda: store)

    async def fake_user() -> UUID:
        return user_id

    monkeypatch.setattr("app.api.messages.current_user_id", fake_user)

    from app.auth import current_user_id as auth_current_user_id
    from app.api.conversations import router as conversations_router
    from app.api.messages import router as messages_router

    application = FastAPI()
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.dependency_overrides[auth_current_user_id] = fake_user
    application.include_router(conversations_router)
    application.include_router(messages_router)
    return TestClient(application)


def test_body_user_id_is_ignored_message_stays_with_token_user(monkeypatch):
    token_user = uuid4()
    other_user = uuid4()
    store = MemoryChatStore()
    monkeypatch.setattr("app.api.conversations.get_store", lambda: store)

    async def token_auth() -> UUID:
        return token_user

    monkeypatch.setattr("app.api.conversations.current_user_id", token_auth)
    conv_client, _store = _client(monkeypatch, token_user, store=store)
    create = conv_client.post("/api/conversations", json={"title": "Identity"})
    conv_id = create.json()["id"]

    def check_quota(*_args, **_kwargs):
        return {"allowed": True, "reason": "ok"}

    def increment_quota(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.quota.check_quota", check_quota)
    monkeypatch.setattr("app.quota.increment_quota", increment_quota)
    monkeypatch.setattr("app.api.messages.check_quota", check_quota, raising=False)
    monkeypatch.setattr("app.api.messages.increment_quota", increment_quota, raising=False)
    monkeypatch.setattr("app.db.get_supabase", lambda: object())
    monkeypatch.setattr("app.api.messages.get_supabase", lambda: object(), raising=False)
    monkeypatch.setattr("app.agent.graph.groq_complete", lambda _m: (_ for _ in ()).throw(AssertionError()))
    monkeypatch.setattr("app.agent.graph.groq_stream", lambda _m: (_ for _ in ()).throw(AssertionError()))

    context = {
        "embedder": type("E", (), {"embed_query": lambda self, _q: [0.9, 0.1]})(),
        "profiles": [{"topic": "immigrazione", "embedding": [1.0, 0.0]}],
        "rpc": lambda *_a, **_k: [],
        "complete": lambda _m: "Answer\nCITATIONS:",
    }
    monkeypatch.setattr("app.api.messages.build_turn_context", lambda: context, raising=False)

    msg_client = _messages_client(monkeypatch, token_user, store)
    question = "How do I renew a residence permit?"
    response = msg_client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": question, "user_id": str(other_user)},
    )
    assert response.status_code == 200

    assert store.list_conversations(str(other_user)) == []
    token_convs = store.list_conversations(str(token_user))
    assert [row["id"] for row in token_convs] == [conv_id]
    rows = store.list_messages(conv_id)
    assert [row["role"] for row in rows] == ["user", "assistant"]
    assert rows[0]["content"] == question

    other_client = _messages_client(monkeypatch, other_user, store)
    assert other_client.get("/api/conversations").json() == []