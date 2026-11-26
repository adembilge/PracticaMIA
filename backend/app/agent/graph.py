from typing import Callable, Literal

from langgraph.graph import END, StateGraph

from app.agent.parse import parse_generation, strip_urls, validate_citations
from app.agent.prompt import build_prompt
from app.agent.state import AgentState
from app.agent.stream import split_stream_chunk
from app.config import get_settings
from app.rag.language import detect_language
from app.rag.retrieve import portal_reply, retrieve_chunks, route_topic

_UNSUPPORTED_ANSWER = (
    "PracticaMIA answers in English and Italian. "
    "Ask your question again in one of those languages."
)

_ROUTE_MAP = {
    "retrieve": "retrieve",
    "generate": "generate",
    "end": END,
}


def _route(state: AgentState) -> Literal["end", "retrieve", "generate"]:
    return state["route"]


def build_graph(embedder, complete: Callable[[list[dict]], str], profiles: list[dict], rpc):
    def prepare(state: AgentState) -> dict:
        language, unsupported_language = detect_language(state["question"])
        if unsupported_language:
            return {
                "language": language,
                "unsupported_language": True,
                "answer": _UNSUPPORTED_ANSWER,
                "insufficient": True,
                "citations": [],
                "route": "end",
            }

        embedding = embedder.embed_query(state["question"])
        topic = route_topic(embedding, profiles)
        return {
            "language": language,
            "unsupported_language": False,
            "topic": topic,
            "retrieval_round": 0,
            "refined_query": None,
            "chunks": [],
            "route": "retrieve",
        }

    def retrieve(state: AgentState) -> dict:
        query = state["refined_query"] or state["question"]
        chunks = retrieve_chunks(query, state["topic"], embedder, rpc)
        if not chunks:
            answer, citations = portal_reply(state["topic"], state["language"])
            return {
                "chunks": [],
                "answer": answer,
                "citations": citations,
                "insufficient": True,
                "route": "end",
            }
        return {
            "chunks": chunks,
            "route": "generate",
        }

    def generate(state: AgentState) -> dict:
        messages = build_prompt(state)
        raw = complete(messages)
        answer, citation_ids, refine = parse_generation(raw)
        citations = validate_citations(citation_ids, state["chunks"])
        result: dict = {
            "answer": answer,
            "citations": citations,
            "insufficient": False,
        }

        if state["retrieval_round"] == 1:
            result["refined_query"] = None
            result["route"] = "end"
            return result

        if refine:
            result["refined_query"] = refine
            result["retrieval_round"] = 1
            result["route"] = "retrieve"
            return result

        result["route"] = "end"
        return result

    graph = StateGraph(AgentState)
    graph.add_node("prepare", prepare)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.set_entry_point("prepare")
    graph.add_conditional_edges("prepare", _route, _ROUTE_MAP)
    graph.add_conditional_edges("retrieve", _route, _ROUTE_MAP)
    graph.add_conditional_edges("generate", _route, _ROUTE_MAP)
    return graph.compile()


def groq_complete(messages: list[dict]) -> str:
    from langchain_groq import ChatGroq

    settings = get_settings()
    model = ChatGroq(
        api_key=settings.groq_api_key,
        model_name=settings.llm_model,
        temperature=0.1,
        max_tokens=700,
    )
    result = model.invoke(messages)
    return str(result.content)


def _piece_text(piece) -> str:
    if isinstance(piece, str):
        return piece
    content = getattr(piece, "content", "")
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or ""))
            else:
                text = getattr(item, "text", None)
                if text:
                    parts.append(str(text))
        return "".join(parts)
    return str(content)


def iter_model_chunks(messages: list[dict], complete: Callable):
    """Yield model text. A string return is one chunk; ChatGroq.stream is many."""
    result = complete(messages)
    if isinstance(result, str):
        if result:
            yield result
        return
    for piece in result:
        text = _piece_text(piece)
        if text:
            yield text


def _visible_tail(held: str) -> str:
    if not held:
        return ""
    if held.startswith("CITATIONS:") or held.startswith("REFINE:"):
        return ""
    if "CITATIONS:".startswith(held) or "REFINE:".startswith(held):
        return ""
    return held


def groq_stream(messages: list[dict]):
    from langchain_groq import ChatGroq

    settings = get_settings()
    model = ChatGroq(
        api_key=settings.groq_api_key,
        model_name=settings.llm_model,
        temperature=0.1,
        max_tokens=700,
    )
    return model.stream(messages)


def stream_grounded_answer(question, history, embedder, complete, profiles, rpc):
    language, unsupported_language = detect_language(question)
    if unsupported_language:
        yield ("token", _UNSUPPORTED_ANSWER)
        yield ("result", {"answer": _UNSUPPORTED_ANSWER, "citations": []})
        return

    embedding = embedder.embed_query(question)
    topic = route_topic(embedding, profiles)
    refined_query = None
    retrieval_round = 0

    while retrieval_round < 2:
        query = refined_query or question
        chunks = retrieve_chunks(query, topic, embedder, rpc)
        if not chunks:
            answer, citations = portal_reply(topic, language)
            if answer:
                yield ("token", answer)
            yield ("result", {"answer": answer, "citations": citations})
            return

        raw_parts: list[str] = []
        held = ""
        visible_chunks: list[str] = []
        for piece in iter_model_chunks(
            build_prompt(
                {
                    "question": question,
                    "language": language,
                    "history": history,
                    "chunks": chunks,
                }
            ),
            complete,
        ):
            raw_parts.append(piece)
            visible, held = split_stream_chunk(held, piece)
            if visible:
                visible_chunks.append(visible)
        tail = _visible_tail(held)
        if tail:
            visible_chunks.append(tail)

        raw = "".join(raw_parts)
        answer, citation_ids, refine = parse_generation(raw)
        citations = validate_citations(citation_ids, chunks)
        if refine and retrieval_round == 0:
            refined_query = refine
            retrieval_round = 1
            continue
        for chunk_text in visible_chunks:
            yield ("token", strip_urls(chunk_text))
        yield ("result", {"answer": answer, "citations": citations})
        return