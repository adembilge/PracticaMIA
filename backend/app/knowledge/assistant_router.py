"""Preview-only, authenticated case-bound RAG question answering.

No production route, no document ingestion and no auto-approval. A user can
query only an owned synthetic case and only against active, approved official
passages. The model is never called if the review gate yields no evidence.
"""
import re
from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.runnables import Runnable
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth.tokens import Principal, get_principal
from app.cases.router import get_case
from app.database import get_session
from app.knowledge.rag_chain import answer_from_passages, select_verified_quotes
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
_SUBMISSION_QUOTES = (
    (f"{_ANPR_GUIDE}:0021", r"Verifica la correttezza.*?della dichiarazione;"),
    (f"{_ANPR_GUIDE}:0021", r"Seleziona il tasto “Invio dichiarazione”\."),
)
_PRACTICAMIA_SUBMISSION_QUESTION = re.compile(
    r"(?:can practicamia submit (?:my |the )?residence declaration(?: for me)?"
    r"|practicamia può inviare (?:per me )?la dichiarazione di residenza(?: per me)?)\??",
    re.IGNORECASE,
)
_TOPICS = (
    (r"\btari\b", (
        (f"{_MILAN_FAQ}:0005", r"Inoltre, è necessario dichiarare[^.]+\."),
    )),
    (r"\b(upload|caricare|allegare)\b.*\b(lease|contratto)\b", (
        (f"{_ANPR_GUIDE}:0018", r"Gli allegati non sono obbligatori"),
        (f"{_ANPR_GUIDE}:0017", r"Per agevolare gli accertamenti.*?proprietario\)\."),
    )),
    (r"\b(?:registered|registrato)\b.*\b(?:lease|locazione)\b|"
     r"\blocazione\b.*\bregistrato\b", (
        (f"{_ANPR_GUIDE}:0015", r"seleziona il punto 2[^]+"),
    )),
    (r"\b(submit|inviare)\b.*\b(declaration|dichiarazione)\b", _SUBMISSION_QUOTES),
    (r"\b(when must|how many days|entro quando|entro quanti giorni)\b"
     r"(?=.*\b(milan|milano)\b)(?=.*\b(address|residence|indirizzo|residenza)\b)", (
        (f"{_MILAN_FAQ}:0000", r"Comunicare all'Ufficio Anagrafe[^.]+\."),
    )),
)
# Exact reviewed FAQ wordings can show signed-source quotes without depending
# on a free model's selection. New phrasings still use the relevance check.
_EXACT_REVIEWED_QUESTIONS = frozenset({
    "when must i report my milan address change",
    "entro quando devo comunicare il cambio di indirizzo a milano",
    "is the tari declaration included in my residence change",
    "la dichiarazione tari è inclusa nel cambio di residenza",
    "which details should i prepare for my registered private lease",
    "quali dati devo preparare per il mio contratto di locazione registrato",
    "must i upload my lease to anpr",
    "devo caricare su anpr il contratto di locazione",
})
_REQUIRES_CURRENT_OR_PERSONAL_DECISION = re.compile(
    r"\b(attachment size|file size|limite.{0,35}allegat|"
    r"automatically rejected|respinta automaticamente|missed the deadline|superato il termine)\b",
    re.IGNORECASE,
)


def _reviewed_topic(question: str) -> Sequence[tuple[str, str]]:
    return next((options for pattern, options in _TOPICS
                 if re.search(pattern, question, re.IGNORECASE)), ())


def _resolve_topic(
    db: Session, options: Sequence[tuple[str, str]],
) -> tuple[list[EvidencePassage], tuple[str, ...]]:
    passages = {}
    quotes = []
    for citation_id, pattern in options:
        if citation_id not in passages:
            passages[citation_id] = resolve_approved_passage(
                db, citation_id=citation_id, jurisdiction=JURISDICTION,
                procedure_id=PROCEDURE, language="it",
            )
        passage = passages[citation_id]
        if passage is None:
            return [], ()
        match = re.search(pattern, " ".join(passage.content.split()))
        if match is None:
            return [], ()
        quotes.append(f'[{citation_id}] "{match.group().strip()}"')
    approved = [passage for passage in passages.values() if passage is not None]
    bundle = "\n".join(quotes)
    if not verify_exact_quotations(bundle, {item.citation_id: item.content for item in approved}):
        return [], ()
    return approved, tuple(quotes)


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
    asks_about_product_submission = bool(
        _PRACTICAMIA_SUBMISSION_QUESTION.fullmatch(payload.question.strip())
    )
    topic = _SUBMISSION_QUOTES if asks_about_product_submission else _reviewed_topic(payload.question)
    quotes: tuple[str, ...] = ()
    if topic:
        passages, quotes = _resolve_topic(db, topic)
    else:
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
            excerpt=(
                " ".join(quote.split('] "', 1)[1][:-1] for quote in quotes
                         if quote.startswith(f"[{item.citation_id}] "))
                if quotes else item.content[:1200]
            ),
        )
        for item in passages
    ]

    exact_question = " ".join(payload.question.strip().casefold().rstrip("?").split())
    if asks_about_product_submission or exact_question in _EXACT_REVIEWED_QUESTIONS:
        # These wordings resolve to preselected approved excerpts. The product
        # handoff remains fixed and source revocation is checked above.
        return AskAnswer(status="answer_generated", answer="\n".join(quotes), sources=sources)

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
        if quotes:
            answer = select_verified_quotes(
                question=payload.question, quotes=quotes, chat_model=model,
            )
            if answer == "":
                return AskAnswer(status="insufficient_evidence", sources=[])
        else:
            answer = answer_from_passages(
                question=payload.question, passages=passages, chat_model=model,
            ).answer
    except Exception:
        return AskAnswer(status="generation_unavailable", sources=sources)

    if answer is None or not verify_exact_quotations(
        answer, {item.citation_id: item.content for item in passages},
    ):
        return AskAnswer(status="unverified_answer", sources=sources)

    # Every line is a verified exact quote. Applicability, relevance, and
    # source freshness still require human review and separate evaluation.
    return AskAnswer(
        status="answer_generated", answer=answer, sources=sources,
    )
