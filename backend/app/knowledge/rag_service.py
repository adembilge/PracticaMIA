"""Two-step RAG wiring: approved retrieval first, then LangChain generation.

No HTTP route or background task. An authenticated service layer must derive
jurisdiction and procedure from verified case state before invoking this.
"""
from typing import Sequence

from langchain_core.runnables import Runnable
from sqlalchemy.orm import Session

from app.knowledge.rag_chain import GroundedAnswer, answer_from_passages
from app.knowledge.vector_search import search_approved_hybrid


def answer_reviewed_question(
    db: Session, *, question: str, jurisdiction: str, procedure_id: str,
    language: str, chat_model: Runnable, limit: int = 5,
    query_embedding: Sequence[float] | None = None,
    model_id: str | None = None,
) -> GroundedAnswer:
    """Return insufficient evidence without ever invoking the chat model."""
    passages = search_approved_hybrid(
        db, query=question, jurisdiction=jurisdiction,
        procedure_id=procedure_id, language=language,
        limit=limit, query_embedding=query_embedding, model_id=model_id,
    )
    return answer_from_passages(
        question=question, passages=passages, chat_model=chat_model,
    )
