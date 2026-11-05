"""Authenticated, read-only search over exact reviewed Milan evidence passages."""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.auth.tokens import get_principal
from app.database import get_session
from app.knowledge.search import (
    normalize_query, resolve_approved_passage, search_approved_passages,
)


class EvidenceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    citation_id: str
    passage_id: str
    source_id: str
    source_version_id: str
    source_revision: int
    institution: str
    title: str
    official_url: str
    jurisdiction: str
    procedure_id: str
    language: str
    section_path: str
    content: str
    passage_sha256: str
    source_sha256: str
    reviewed_at: datetime
    retrieved_at: datetime


class EvidenceSearchResponse(BaseModel):
    status: Literal["evidence_found", "insufficient_evidence"]
    normalized_query: str
    jurisdiction: str
    procedure_id: str
    language: str
    evidence: list[EvidenceView]


router = APIRouter(
    prefix="/api/v1/knowledge",
    tags=["official-evidence-search"],
    dependencies=[Depends(get_principal)],
)


@router.get("/search", response_model=EvidenceSearchResponse)
def search(
    query: str = Query(min_length=2, max_length=180),
    jurisdiction: str = Query(min_length=5, max_length=48,
                              pattern=r"^IT-[A-Z]{2}-[A-Z]+$"),
    procedure_id: str = Query(min_length=3, max_length=96,
                              pattern=r"^[a-z][a-z0-9_]+$"),
    language: Literal["it", "en"] = Query(),
    limit: int = Query(default=5, ge=1, le=10),
    db: Session = Depends(get_session),
) -> EvidenceSearchResponse:
    try:
        cleaned, _ = normalize_query(query)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    passages = search_approved_passages(
        db, query=query, jurisdiction=jurisdiction,
        procedure_id=procedure_id, language=language, limit=limit,
    )
    return EvidenceSearchResponse(
        status="evidence_found" if passages else "insufficient_evidence",
        normalized_query=cleaned, jurisdiction=jurisdiction,
        procedure_id=procedure_id, language=language, evidence=[
            EvidenceView.model_validate(item) for item in passages
        ],
    )


@router.get("/passages/{citation_id}", response_model=EvidenceView)
def resolve_citation(
    citation_id: str = Path(
        min_length=41, max_length=41,
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}:[0-9]{4}$",
    ),
    jurisdiction: str = Query(min_length=5, max_length=48,
                              pattern=r"^IT-[A-Z]{2}-[A-Z]+$"),
    procedure_id: str = Query(min_length=3, max_length=96,
                              pattern=r"^[a-z][a-z0-9_]+$"),
    language: Literal["it", "en"] = Query(),
    db: Session = Depends(get_session),
) -> EvidenceView:
    found = resolve_approved_passage(
        db, citation_id=citation_id,
        jurisdiction=jurisdiction, procedure_id=procedure_id,
        language=language,
    )
    if found is None:
        raise HTTPException(404, "Approved citation not found")
    return EvidenceView.model_validate(found)
