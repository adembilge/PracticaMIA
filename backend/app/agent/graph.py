from typing import Callable, Literal

from langgraph.graph import END, StateGraph

from app.agent.parse import parse_generation, validate_citations
from app.agent.prompt import build_prompt
from app.agent.state import AgentState
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