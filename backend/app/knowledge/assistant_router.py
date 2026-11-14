"""Preview-only, authenticated case-bound RAG question answering.

No production route, no document ingestion and no auto-approval. A user can
query only an owned synthetic case and only against active, approved official
passages. The model is never called if the review gate yields no evidence.
"""
import re
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
from app.knowledge.search import EvidencePassage, normalize_query, resolve_approved_passage
from app.knowledge.usage_model import AssistantDailyUsage  # noqa: F401 - register table
from app.knowledge.usage_limit import reserve_daily_model_call
from app.knowledge.vector_search import search_approved_hybrid

JURISDICTION = "IT-MI-MILANO"
PROCEDURE = "milan_residence_change"

# Narrow lexical aliases for English questions over reviewed Italian passages.
# Retrieval hints are NOT administrative facts or translated rules.
ENGLISH_RETRIEVAL_ALIASES = (
    (re.compile(r"\b(residence|residency|change of address|moving)\b"), "residenza"),
    (re.compile(r"\b(documents?|attachments?|paperwork)\b"), "documenti"),
    (re.compile(r"\b(lease|rental|tenant|renting)\b"), "locazione"),
    (re.compile(r"\b(application|submit|submission)\b"), "domanda"),
)

# Known requests within the reviewed route use its existing exact passages.
# A source approval or version change still has to pass the normal resolver.
_MILAN_FAQ = "e139e910-3a89-4994-b450-b5107d8db7dd"
_ANPR_GUIDE = "c89b4c40-4c41-48d5-ad52-be08e9630277"
_TOPICS = (
    (r"\btari\b", (f"{_MILAN_FAQ}:0005",)),
    (r"\b(upload|caricare|allegare)\b.*\b(lease|contratto)\b",
     (f"{_ANPR_GUIDE}:0017",)),
    (r"\b(lease|locazione)\b",
     (f"{_ANPR_GUIDE}:0015", f"{_ANPR_GUIDE}:0017")),
    (r"\b(submit|inviare)\b.*\b(declaration|dichiarazione)\b",
     (f"{_ANPR_GUIDE}:0021", f"{_ANPR_GUIDE}:0022")),
    (r"\b(when must|how many days|entro quando|entro quanti giorni)\b",
     (f"{_MILAN_FAQ}:0000",)),
)
_REQUIRES_CURRENT_OR_PERSONAL_DECISION = re.compile(
    r"\b(attachment size|file size|limite.{0,35}allegat|"
    r"automatically rejected|respinta automaticamente|missed the deadline|superato il termine)\b",
    re.IGNORECASE,
)


def _scope_passages(db: Session, question: str) -> list[EvidencePassage] | None:
    for pattern, citations in _TOPICS:
        if re.search(pattern, question, re.IGNORECASE):
            return [
                passage for citation in citations
                if (passage := resolve_approved_passage(
                    db, citation_id=citation, jurisdiction=JURISDICTION,
                    procedure_id=PROCEDURE, language="it",
                )) is not None
            ]
    return None


def _english_retrieval_hints(question: str) -> tuple[str, ...]:
    lowered = question.casefold()
    return tuple(
        italian for pattern, italian in ENGLISH_RETRIEVAL_ALIASES
        if pattern.search(lowered)
    )
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
    """Create a provider adapter only for an explicitly configured Preview.

    OpenRouter defaults to free-only routing; no paid model may be selected
    accidentally through this Preview integration.
    """
    factory = getattr(request.app.state, "assistant_model_factory", None)
    if factory is not None:
        return factory()

    settings = request.app.state.settings
    if not settings.assistant_chat_model:
        return None

    provider = settings.assistant_llm_provider
    if provider == "openrouter":
        if not settings.assistant_openrouter_api_key:
            return None
        model_id = settings.assistant_chat_model
        if model_id != "openrouter/free" and not model_id.endswith(":free"):
            raise ValueError("OpenRouter Preview requires an explicitly free model")

        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_id,
            api_key=settings.assistant_openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            max_tokens=500,
            timeout=30,
            max_retries=0,
        )

    if provider == "openai":
        if not settings.assistant_openai_api_key:
            return None
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.assistant_chat_model,
            api_key=settings.assistant_openai_api_key,
            max_tokens=500,
            timeout=15,
            max_retries=0,
        )

    raise ValueError("Unsupported assistant model provider")


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
    if _REQUIRES_CURRENT_OR_PERSONAL_DECISION.search(payload.question):
        return AskAnswer(status="insufficient_evidence", sources=[])
    passages = _scope_passages(db, payload.question)
    if passages is None:
        passages = search_approved_hybrid(
            db, query=payload.question, jurisdiction=JURISDICTION,
            procedure_id=PROCEDURE, language="it", limit=5,
        )
        if not passages and payload.language == "en":
            for verified_query in _english_retrieval_hints(payload.question):
                passages = search_approved_hybrid(
                    db, query=verified_query, jurisdiction=JURISDICTION,
                    procedure_id=PROCEDURE, language="it", limit=5,
                )
                if passages:
                    break
    if not passages:
        return AskAnswer(status="insufficient_evidence", sources=[])

    sources = [
        CitedSource(
            citation_id=item.citation_id, source_id=item.source_id,
            source_version_id=item.source_version_id, title=item.title,
            official_url=item.official_url, section_path=item.section_path,
            excerpt=item.content[:1200],
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
