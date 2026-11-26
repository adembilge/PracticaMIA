from typing import Literal, TypedDict


class Citation(TypedDict):
    chunk_id: str
    title: str
    url: str
    heading: str
    fetched_at: str


class AgentState(TypedDict):
    question: str
    language: Literal["en", "it"]
    unsupported_language: bool
    topic: str
    history: list[dict]
    chunks: list[dict]
    retrieval_round: int
    refined_query: str | None
    answer: str
    citations: list[Citation]
    insufficient: bool