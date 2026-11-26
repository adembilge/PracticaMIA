import json
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.main import http_exception_handler
from memory_store import MemoryChatStore

QUOTA_IT = "La capacità giornaliera di risposte è esaurita. Riprova domani."
QUOTA_EN = "The daily answer capacity is used. Try again tomorrow."
CHUNK_URL = "https://www.poliziadistato.it/articolo/225"
UNSUPPORTED_ANSWER = (
    "PracticaMIA answers in English and Italian. "
    "Ask your question again in one of those languages."
)

CHUNK = {
    "id": "chunk-1",
    "content": "Il rinnovo si chiede in Questura.",
    "heading": "Rinnovo",
    "url": CHUNK_URL,
    "title": "Permesso",
    "topic": "immigrazione",
    "fetched_at": "2026-11-01T00:00:00+00:00",
    "cosine_similarity": 0.8,
}

PROFILES = [{"topic": "immigrazione", "embedding": [1.0, 0.0]}]


class FakeEmbedder:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_query(self, query: str) -> list[float]:
        self.queries.append(query)
        return [0.9, 0.1]


class ChunkRpc:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self.rows = list(rows) if rows is not None else [CHUNK]
        self.queries: list[str] = []

    def __call__(self, embedding, query_text, topic_filter, match_count):
        self.queries.append(query_text)
        return [dict(row) for row in self.rows]


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in body.replace("\r\n", "\n").split("\n\n"):
        if not block.strip():
            continue
        event_name = None
        data = None
        for line in block.split("\n"):
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
        events.append((event_name, data))
    return events


def _client(
    monkeypatch, user_id: UUID, store: MemoryChatStore | None = None
) -> tuple[TestClient, MemoryChatStore]:
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


def _patch_quota(monkeypatch, decision: dict, increments: list | None = None) -> None:
    def check_quota(*_args, **_kwargs):
        return decision

    def increment_quota(*args, **kwargs):
        if increments is not None:
            increments.append((args, kwargs))

    monkeypatch.setattr("app.quota.check_quota", check_quota)
    monkeypatch.setattr("app.quota.increment_quota", increment_quota)
    monkeypatch.setattr("app.api.messages.check_quota", check_quota, raising=False)
    monkeypatch.setattr("app.api.messages.increment_quota", increment_quota, raising=False)
    monkeypatch.setattr("app.db.get_supabase", lambda: object())
    monkeypatch.setattr("app.api.messages.get_supabase", lambda: object(), raising=False)


def _patch_groq(monkeypatch, calls: dict) -> None:
    def groq_complete(_messages):
        calls["groq_complete"] += 1
        raise AssertionError("groq_complete should not run")

    def groq_stream(_messages):
        calls["groq_stream"] += 1
        raise AssertionError("groq_stream should not run")

    monkeypatch.setattr("app.agent.graph.groq_complete", groq_complete)
    monkeypatch.setattr("app.api.messages.groq_complete", groq_complete, raising=False)
    monkeypatch.setattr("app.agent.graph.groq_stream", groq_stream, raising=False)
    monkeypatch.setattr("app.api.messages.groq_stream", groq_stream, raising=False)


def _install_context(monkeypatch, *, complete, rpc, embedder=None, profiles=None) -> None:
    context = {
        "embedder": embedder or FakeEmbedder(),
        "profiles": PROFILES if profiles is None else profiles,
        "rpc": rpc,
        "complete": complete,
    }
    monkeypatch.setattr(
        "app.api.messages.build_turn_context",
        lambda: context,
        raising=False,
    )


def _post(client: TestClient, conv_id: str, content: str, accept_language: str | None = None):
    headers = {}
    if accept_language is not None:
        headers["Accept-Language"] = accept_language
    return client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": content},
        headers=headers,
    )


def test_quota_user_denial_is_sse_error_without_model_or_rows(monkeypatch):
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "New chat")
    increments: list = []
    calls = {"groq_complete": 0, "groq_stream": 0}
    _patch_quota(
        monkeypatch,
        {"allowed": False, "reason": "user_daily"},
        increments,
    )
    _patch_groq(monkeypatch, calls)

    response = _post(client, conv["id"], "How do I renew a residence permit?")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: error" in response.text
    events = parse_sse(response.text)
    assert events[0][0] == "error"
    assert events[0][1]["code"] == "quota_user"
    assert events[0][1]["message"] == QUOTA_EN
    assert calls["groq_complete"] == 0
    assert calls["groq_stream"] == 0
    assert increments == []
    assert store.list_messages(conv["id"]) == []


def test_quota_user_italian_when_accept_language_starts_with_it(monkeypatch):
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "New chat")
    _patch_quota(monkeypatch, {"allowed": False, "reason": "user_daily"})
    _patch_groq(monkeypatch, {"groq_complete": 0, "groq_stream": 0})

    response = _post(
        client,
        conv["id"],
        "Come rinnovo il permesso?",
        accept_language="  it-IT ",
    )

    events = parse_sse(response.text)
    assert response.status_code == 200
    assert events[0][1] == {"code": "quota_user", "message": QUOTA_IT}
    assert store.list_messages(conv["id"]) == []


def test_quota_global_uses_the_same_sentences(monkeypatch):
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "New chat")
    _patch_quota(monkeypatch, {"allowed": False, "reason": "global_daily"})
    _patch_groq(monkeypatch, {"groq_complete": 0, "groq_stream": 0})

    english = _post(client, conv["id"], "How do I renew a residence permit?")
    italian = _post(client, conv["id"], "Come rinnovo il permesso?", accept_language="it")

    assert parse_sse(english.text)[0][1] == {"code": "quota_global", "message": QUOTA_EN}
    assert parse_sse(italian.text)[0][1] == {"code": "quota_global", "message": QUOTA_IT}
    assert store.list_messages(conv["id"]) == []


def test_stream_token_citations_done_and_saves_rows(monkeypatch):
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "New chat")
    increments: list = []
    calls = {"groq_complete": 0, "groq_stream": 0, "complete": 0}
    roles_at_complete: list[str] = []
    _patch_quota(monkeypatch, {"allowed": True, "reason": "ok"}, increments)
    _patch_groq(monkeypatch, calls)

    def complete(_messages):
        calls["complete"] += 1
        roles_at_complete.extend(
            row["role"] for row in store.list_messages(conv["id"])
        )
        return "Answer text\nCITATIONS: chunk-1"

    rpc = ChunkRpc()
    _install_context(monkeypatch, complete=complete, rpc=rpc)
    question = "Come rinnovo il permesso di soggiorno?"
    response = _post(client, conv["id"], question)

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    events = parse_sse(response.text)
    assert [name for name, _payload in events] == ["token", "citations", "done"]
    assert events[0][1] == {"text": "Answer text"}
    assert events[1][1]["citations"] == [
        {
            "chunk_id": "chunk-1",
            "title": "Permesso",
            "url": CHUNK_URL,
            "heading": "Rinnovo",
            "fetched_at": "2026-11-01T00:00:00+00:00",
        }
    ]
    rows = store.list_messages(conv["id"])
    assert [row["role"] for row in rows] == ["user", "assistant"]
    assert rows[0]["content"] == question
    assert rows[0]["citations"] == []
    assert rows[1]["content"] == "Answer text"
    assert rows[1]["citations"] == events[1][1]["citations"]
    assert events[2][1] == {"message_id": rows[1]["id"], "answer": "Answer text"}
    assert roles_at_complete == ["user"]
    assert calls["complete"] == 1
    assert calls["groq_complete"] == 0
    assert len(increments) == 1
    assert rpc.queries == [question]


def test_model_runtime_error_emits_upstream_and_keeps_user_row(monkeypatch):
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "New chat")
    increments: list = []
    _patch_quota(monkeypatch, {"allowed": True, "reason": "ok"}, increments)

    def complete(_messages):
        raise RuntimeError("groq down")

    _install_context(monkeypatch, complete=complete, rpc=ChunkRpc())
    question = "How do I renew a residence permit?"
    response = _post(client, conv["id"], question)

    assert response.status_code == 200
    events = parse_sse(response.text)
    assert events[-1][0] == "error"
    assert events[-1][1]["code"] == "upstream"
    assert isinstance(events[-1][1]["message"], str)
    assert events[-1][1]["message"]
    assert "done" not in [name for name, _payload in events]
    rows = store.list_messages(conv["id"])
    assert [row["role"] for row in rows] == ["user"]
    assert rows[0]["content"] == question
    assert increments == []


def test_context_failure_emits_upstream_without_assistant_or_quota(monkeypatch):
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "New chat")
    increments: list = []
    _patch_quota(monkeypatch, {"allowed": True, "reason": "ok"}, increments)

    def boom():
        raise TimeoutError("profile load failed")

    monkeypatch.setattr("app.api.messages.build_turn_context", boom)
    question = "How do I renew a residence permit?"
    response = _post(client, conv["id"], question)

    assert response.status_code == 200
    events = parse_sse(response.text)
    assert events[-1] == (
        "error",
        {"code": "upstream", "message": "The answer service is unavailable."},
    )
    assert "done" not in [name for name, _payload in events]
    rows = store.list_messages(conv["id"])
    assert [row["role"] for row in rows] == ["user"]
    assert rows[0]["content"] == question
    assert increments == []


def test_refine_runs_second_retrieval_and_stops(monkeypatch):
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "New chat")
    increments: list = []
    calls = {"n": 0}
    _patch_quota(monkeypatch, {"allowed": True, "reason": "ok"}, increments)

    def complete(_messages):
        calls["n"] += 1
        if calls["n"] == 1:
            return "Partial\nCITATIONS: chunk-1\nREFINE: permesso di soggiorno"
        if calls["n"] == 2:
            return "Answer text\nCITATIONS: chunk-1\nREFINE: altra query"
        raise AssertionError("third model call")

    rpc = ChunkRpc()
    question = "Come rinnovo il permesso di soggiorno?"
    _install_context(monkeypatch, complete=complete, rpc=rpc)
    response = _post(client, conv["id"], question)

    events = parse_sse(response.text)
    assert [name for name, _payload in events] == ["token", "citations", "done"]
    assert [payload for name, payload in events if name == "token"] == [
        {"text": "Answer text"}
    ]
    assert "Partial" not in response.text
    assert events[1][1]["citations"][0]["url"] == CHUNK_URL
    assert events[2][1]["answer"] == "Answer text"
    rows = store.list_messages(conv["id"])
    assert rows[1]["content"] == "Answer text"
    assert calls["n"] == 2
    assert rpc.queries == [question, "permesso di soggiorno"]
    assert len(increments) == 1


def test_refine_empty_second_retrieval_does_not_keep_first_draft(monkeypatch):
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "New chat")
    increments: list = []
    calls = {"n": 0}
    _patch_quota(monkeypatch, {"allowed": True, "reason": "ok"}, increments)
    question = "Come rinnovo il permesso di soggiorno?"

    class FirstQueryOnlyRpc:
        def __init__(self) -> None:
            self.queries: list[str] = []

        def __call__(self, embedding, query_text, topic_filter, match_count):
            self.queries.append(query_text)
            if query_text == question:
                return [dict(CHUNK)]
            return []

    def complete(_messages):
        calls["n"] += 1
        return "Partial\nCITATIONS: chunk-1\nREFINE: permesso di soggiorno"

    rpc = FirstQueryOnlyRpc()
    _install_context(monkeypatch, complete=complete, rpc=rpc)
    response = _post(client, conv["id"], question)

    events = parse_sse(response.text)
    token_texts = [payload["text"] for name, payload in events if name == "token"]
    assert len(token_texts) == 1
    assert "Partial" not in response.text
    assert CHUNK_URL in token_texts[0]
    rows = store.list_messages(conv["id"])
    assert rows[1]["content"] == token_texts[0]
    assert "Partial" not in rows[1]["content"]
    assert calls["n"] == 1
    assert len(increments) == 1
    assert events[-1][0] == "done"
    assert events[-1][1]["answer"] == rows[1]["content"]


def test_unsupported_language_skips_model_and_still_increments(monkeypatch):
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "New chat")
    increments: list = []
    calls = {"n": 0}
    _patch_quota(monkeypatch, {"allowed": True, "reason": "ok"}, increments)

    def complete(_messages):
        calls["n"] += 1
        raise AssertionError("model called")

    class RaisingEmbedder:
        def embed_query(self, _query: str):
            raise AssertionError("embedder called")

    monkeypatch.setattr(
        "app.agent.graph.detect_language",
        lambda _text: ("en", True),
    )
    _install_context(
        monkeypatch,
        complete=complete,
        rpc=ChunkRpc(),
        embedder=RaisingEmbedder(),
    )
    response = _post(client, conv["id"], "Oturum iznimi nasıl yenilerim?")

    events = parse_sse(response.text)
    assert events[0] == ("token", {"text": UNSUPPORTED_ANSWER})
    assert events[1][1]["citations"] == []
    assert events[2][0] == "done"
    rows = store.list_messages(conv["id"])
    assert rows[1]["content"] == UNSUPPORTED_ANSWER
    assert rows[1]["citations"] == []
    assert calls["n"] == 0
    assert len(increments) == 1


def test_empty_retrieval_uses_portal_reply_without_model(monkeypatch):
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "New chat")
    increments: list = []
    calls = {"n": 0}
    _patch_quota(monkeypatch, {"allowed": True, "reason": "ok"}, increments)

    def complete(_messages):
        calls["n"] += 1
        raise AssertionError("model called")

    _install_context(monkeypatch, complete=complete, rpc=ChunkRpc(rows=[]))
    response = _post(client, conv["id"], "Come rinnovo il permesso di soggiorno?")

    events = parse_sse(response.text)
    assert events[0][0] == "token"
    assert CHUNK_URL in events[0][1]["text"]
    rows = store.list_messages(conv["id"])
    assert CHUNK_URL in rows[1]["content"]
    assert calls["n"] == 0
    assert len(increments) == 1
    assert events[-1][0] == "done"


def test_history_uses_prior_messages_without_the_new_question(monkeypatch):
    user_id = uuid4()
    client, store = _client(monkeypatch, user_id)
    conv = store.insert_conversation(str(user_id), "Kept")
    for index in range(8):
        store.insert_message(conv["id"], "user", f"hist-{index}", [])
    seen: dict = {}
    _patch_quota(monkeypatch, {"allowed": True, "reason": "ok"}, [])

    def complete(messages):
        seen["messages"] = messages
        return "Answer text\nCITATIONS: chunk-1"

    _install_context(monkeypatch, complete=complete, rpc=ChunkRpc())
    question = "How do I renew a residence permit?"
    response = _post(client, conv["id"], question)

    assert response.status_code == 200
    user_content = seen["messages"][1]["content"]
    history_part = user_content.split("SOURCE CHUNKS", 1)[0]
    assert "hist-0" not in history_part
    assert "hist-1" not in history_part
    assert "user: hist-2" in history_part
    assert "user: hist-7" in history_part
    assert question not in history_part
    assert f"QUESTION\n{question}" in user_content
