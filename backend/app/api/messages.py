import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from app import db as db_mod
from app import quota as quota_mod
from app.agent.graph import stream_grounded_answer
from app.agent.history import trim_history
from app.auth import current_user_id
from app.store import Message, get_store

_QUOTA_IT = "La capacità giornaliera di risposte è esaurita. Riprova domani."
_QUOTA_EN = "The daily answer capacity is used. Try again tomorrow."
_UPSTREAM = "The answer service is unavailable."

_QUOTA_CODES = {
    "user_daily": "quota_user",
    "global_daily": "quota_global",
}

router = APIRouter()

_MAX_QUESTION_LEN = 8000


class ContentBody(BaseModel):
    content: str
    model_config = ConfigDict(extra="ignore")


def sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def quota_denial_message(accept_language: str | None) -> str:
    if accept_language is not None and accept_language.strip().startswith("it"):
        return _QUOTA_IT
    return _QUOTA_EN


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


def _coerce_embedding(raw) -> list[float]:
    if isinstance(raw, list):
        return [float(item) for item in raw]
    if isinstance(raw, str):
        return [float(item) for item in json.loads(raw)]
    raise TypeError(f"unexpected embedding type: {type(raw)}")


def _load_profiles(client) -> list[dict]:
    rows = client.table("topic_profiles").select("topic, embedding").execute().data or []
    return [
        {"topic": row["topic"], "embedding": _coerce_embedding(row["embedding"])}
        for row in rows
    ]


def _match_rpc(client):
    def rpc(query_embedding, query_text, topic_filter, match_count):
        result = client.rpc(
            "match_chunks",
            {
                "query_embedding": query_embedding,
                "query_text": query_text,
                "topic_filter": topic_filter,
                "match_count": match_count,
            },
        ).execute()
        return result.data or []

    return rpc


def build_turn_context() -> dict:
    from app.agent.graph import groq_stream
    from app.rag.embed import Embedder

    client = db_mod.get_supabase()
    return {
        "embedder": Embedder(),
        "profiles": _load_profiles(client),
        "rpc": _match_rpc(client),
        "complete": groq_stream,
    }


def _jsonable_citations(citations: list) -> list[dict]:
    rendered: list[dict] = []
    for item in citations:
        fetched = item.get("fetched_at", "")
        if fetched is not None and not isinstance(fetched, str):
            fetched = fetched.isoformat()
        rendered.append(
            {
                "chunk_id": item.get("chunk_id", ""),
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "heading": item.get("heading", ""),
                "fetched_at": "" if fetched is None else fetched,
            }
        )
    return rendered


def save_turn(
    user_id: UUID,
    conversation_id: str,
    content: str,
    accept_language: str | None,
    conv: dict,
):
    decision = quota_mod.check_quota(
        user_id,
        quota_mod.rome_today(),
        quota_mod.SupabaseQuotaStore(db_mod.get_supabase()),
    )
    if not decision["allowed"]:
        code = _QUOTA_CODES.get(decision["reason"], "quota_global")
        yield sse(
            "error",
            {"code": code, "message": quota_denial_message(accept_language)},
        )
        return

    store = get_store()
    prior = store.list_messages(conversation_id)
    history = trim_history(
        [{"role": row["role"], "content": row["content"]} for row in prior]
    )
    store.insert_message(conversation_id, "user", content, [])
    context = build_turn_context()
    answer = ""
    citations: list[dict] = []
    try:
        for kind, payload in stream_grounded_answer(
            content,
            history,
            context["embedder"],
            context["complete"],
            context["profiles"],
            context["rpc"],
        ):
            if kind == "token":
                yield sse("token", {"text": payload})
            elif kind == "result":
                answer = payload["answer"]
                citations = _jsonable_citations(payload["citations"])
    except RuntimeError:
        yield sse("error", {"code": "upstream", "message": _UPSTREAM})
        return

    message = store.insert_message(conversation_id, "assistant", answer, citations)
    title = _title_from_question(content) if conv["title"] == "New chat" else None
    store.touch(conversation_id, title)
    quota_mod.increment_quota(
        user_id,
        quota_mod.rome_today(),
        quota_mod.SupabaseQuotaStore(db_mod.get_supabase()),
    )
    yield sse("citations", {"citations": citations})
    yield sse("done", {"message_id": message["id"]})


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
    request: Request,
    user_id: UUID = Depends(current_user_id),
) -> StreamingResponse:
    validate_content(body.content)
    store = get_store()
    conv = store.get_conversation(str(user_id), conversation_id)
    if conv is None:
        raise _not_found()
    return StreamingResponse(
        save_turn(
            user_id,
            conversation_id,
            body.content,
            request.headers.get("accept-language"),
            conv,
        ),
        media_type="text/event-stream",
    )
