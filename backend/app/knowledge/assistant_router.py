"""Preview-only, authenticated case-bound RAG question answering.

No production route, no document ingestion and no auto-approval. A user can
query only an owned synthetic case and only against active, approved official
passages. The model is never called if the review gate yields no evidence.
"""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.runnables import Runnable
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth.tokens import Principal, get_principal
from app.cases.router import get_case
from app.database import get_session
from app.knowledge.rag_chain import answer_from_passages
from app.knowledge.quote_verification import verify_exact_quotations
from app.knowledge.search import normalize_query
from app.knowledge.usage_model import AssistantDailyUsage  # noqa: F401 - register table
from app.knowledge.usage_limit import reserve_daily_model_call
from app.knowledge.vector_search import search_approved_hybrid

JURISDICTION = "IT-MI-MILANO"
PROCEDURE = "milan_residence_change"
router = APIRouter(
    prefix="/api/v1/cases",
    tags=["assistant-preview"],
    dependencies=[Depends(get_principal)],
)


class AskQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=2, max_length=180)
    language: Literal["it", "en"] = "it"


class CitedSource(BaseModel):
    citation_id: str
    source_id: str
    source_version_id: str
    title: str
    official_url: str
    section_path: str
    excerpt: str


class AskAnswer(BaseModel):
    status: Literal[
        "insufficient_evidence", "model_not_configured",
        "answer_generated", "unverified_answer", "generation_unavailable",
    ]
    answer: str | None = None
    sources: list[CitedSource]
    is_demo: bool = True


def _model_for_preview(request: Request) -> Runnable | None:
    # Unit tests may inject a strictly offline model factory. Do not
    # serialize this object or surface credentials to clients.
    factory = getattr(request.app.state, "assistant_model_factory", None)
    if factory is not None:
        return factory()
    settings = request.app.state.settings
    if not settings.assistant_chat_model or not settings.assistant_openai_api_key:
        return None

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.assistant_chat_model,
        api_key=settings.assistant_openai_api_key,
        max_tokens=500,
        timeout=15,
        max_retries=0,
    )


@router.post("/{case_id}/assistant/ask", response_model=AskAnswer)
def ask_case_question(
    case_id: UUID, payload: AskQuestion, request: Request,
    db: Session = Depends(get_session),
    principal: Principal = Depends(get_principal),
) -> AskAnswer:
    record = get_case(db, case_id, principal.subject)
    if record.procedure != PROCEDURE:
        raise HTTPException(422, "Unsupported demo procedure")

    try:
        normalize_query(payload.question)
    except ValueError:
        raise HTTPException(422, "Question must contain 1-12 searchable terms") from None

    # The initial official sources are Italian. English output is supported,
    # but English lexical queries may abstain until multilingual embeddings
    # are evaluated. Never change source scope based on an LLM's inference.
    passages = search_approved_hybrid(
        db, query=payload.question, jurisdiction=JURISDICTION,
        procedure_id=PROCEDURE, language="it", limit=5,
    )
    if not passages:
        return AskAnswer(status="insufficient_evidence", sources=[])

    sources = [
        CitedSource(
            citation_id=item.citation_id, source_id=item.source_id,
            source_version_id=item.source_version_id, title=item.title,
            official_url=item.official_url, section_path=item.section_path,
            excerpt=item.content[:600],
        )
        for item in passages
    ]

    model = None
    try:
        model = _model_for_preview(request)
    except Exception:
        # Never leak model credentials or provider exception text.
        return AskAnswer(status="generation_unavailable", sources=sources)
    if model is None:
        return AskAnswer(status="model_not_configured", sources=sources)

    settings = request.app.state.settings
    if not reserve_daily_model_call(
        db, subject=principal.subject, hash_key=settings.assistant_usage_hash_key,
        daily_limit=settings.assistant_daily_limit,
    ):
        raise HTTPException(status_code=429, detail="Daily assistant limit reached")

    try:
        generated = answer_from_passages(
            question=payload.question, passages=passages, chat_model=model,
        )
    except Exception:
        return AskAnswer(status="generation_unavailable", sources=sources)

    if generated.answer is None or not verify_exact_quotations(
        generated.answer, {item.citation_id: item.content for item in passages},
    ):
        return AskAnswer(status="unverified_answer", sources=sources)

    # Every line is a verified exact quote. Applicability, relevance, and
    # source freshness still require human review and separate evaluation.
    return AskAnswer(
        status="answer_generated", answer=generated.answer, sources=sources,
    )
