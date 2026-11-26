from pathlib import Path
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.main import http_exception_handler
from memory_store import MemoryChatStore


def test_messages_module_drops_holding_sentence():
    source = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "messages.py"
    ).read_text(encoding="utf-8")
    assert "not connected yet" not in source


class _FakeEmbedder:
    def embed_query(self, _query: str) -> list[float]:
        return [1.0, 0.0]


class _EmptyRpc:
    def __call__(self, embedding, query_text, topic_filter, match_count):
        return []


def _install_title_path(monkeypatch) -> dict:
    calls = {"groq_complete": 0, "groq_stream": 0, "complete": 0}

    def groq_complete(_messages):
        calls["groq_complete"] += 1
        raise AssertionError("groq_complete should not run")

    def groq_stream(_messages):
        calls["groq_stream"] += 1
        raise AssertionError("groq_stream should not run")

    def complete(_messages):
        calls["complete"] += 1
        raise AssertionError("complete should not run")

    monkeypatch.setattr(
        "app.quota.check_quota",
        lambda *_args, **_kwargs: {"allowed": True, "reason": "ok"},
    )
    monkeypatch.setattr("app.quota.increment_quota", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.db.get_supabase", lambda: object())
    monkeypatch.setattr("app.agent.graph.groq_complete", groq_complete)
    monkeypatch.setattr("app.agent.graph.groq_stream", groq_stream, raising=False)
    monkeypatch.setattr(
        "app.api.messages.build_turn_context",
        lambda: {
            "embedder": _FakeEmbedder(),
            "profiles": [],
            "rpc": _EmptyRpc(),
            "complete": complete,
        },
        raising=False,
    )
    return calls


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
    calls = _install_title_path(monkeypatch)
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "New chat")
    conv_id = conv["id"]
    question = "Come cambio residenza oggi subito?"

    posted = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": question},
    )
    assert posted.status_code == 200
    assert "text/event-stream" in posted.headers["content-type"]
    assert calls["groq_complete"] == 0
    assert calls["groq_stream"] == 0
    assert calls["complete"] == 0

    listed = client.get(f"/api/conversations/{conv_id}/messages")
    assert listed.status_code == 200
    rows = listed.json()
    assert [row["role"] for row in rows] == ["user", "assistant"]
    assert rows[0]["content"] == question


def test_new_chat_title_from_first_question(monkeypatch):
    calls = _install_title_path(monkeypatch)
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
    assert calls["groq_complete"] == 0
    assert calls["groq_stream"] == 0
    assert calls["complete"] == 0


def test_new_chat_title_truncated_to_60(monkeypatch):
    calls = _install_title_path(monkeypatch)
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "New chat")
    conv_id = conv["id"]
    question = "a" * 70

    client.post(f"/api/conversations/{conv_id}/messages", json={"content": question})

    updated = store.get_conversation(str(user_id), conv_id)
    assert updated is not None
    assert updated["title"] == "a" * 60
    assert calls["groq_complete"] == 0
    assert calls["complete"] == 0


def test_title_stays_when_chat_already_named(monkeypatch):
    _install_title_path(monkeypatch)
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "Renamed chat")
    conv_id = conv["id"]

    client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Come cambio residenza oggi subito?"},
    )

    updated = store.get_conversation(str(user_id), conv_id)
    assert updated is not None
    assert updated["title"] == "Renamed chat"


def test_second_question_does_not_replace_title(monkeypatch):
    _install_title_path(monkeypatch)
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "New chat")
    conv_id = conv["id"]

    client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Come cambio residenza oggi subito?"},
    )
    client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Second question should not become the title"},
    )

    updated = store.get_conversation(str(user_id), conv_id)
    assert updated is not None
    assert updated["title"] == "Come cambio residenza oggi subito?"


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