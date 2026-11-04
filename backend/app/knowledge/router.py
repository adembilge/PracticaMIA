"""Read-only approved-source metadata; never exposes pending material as trusted."""
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.tokens import get_principal
from app.database import get_session
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion


class ApprovedSource(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source_id: str
    source_version_id: str
    revision: int
    institution: str
    title: str
    official_url: str
    language: str
    jurisdiction: str
    procedure_id: str
    reviewed_at: datetime
    content_sha256: str


class SourceCatalog(BaseModel):
    status: str
    sources: list[ApprovedSource]


router = APIRouter(
    prefix="/api/v1/knowledge",
    tags=["official-knowledge"],
    dependencies=[Depends(get_principal)],
)


@router.get("/sources", response_model=SourceCatalog)
def approved_sources(db: Session = Depends(get_session)) -> SourceCatalog:
    """Fail closed unless source and selected, hash-bound version are approved."""
    query = (
        select(KnowledgeSource, KnowledgeSourceVersion)
        .join(KnowledgeSourceVersion,
            (KnowledgeSource.active_version_id == KnowledgeSourceVersion.id)
            & (KnowledgeSource.id == KnowledgeSourceVersion.source_id))
        .where(KnowledgeSource.status == "approved")
        .where(KnowledgeSourceVersion.status == "approved")
        .where(KnowledgeSourceVersion.reviewed_at.is_not(None))
        .where(KnowledgeSourceVersion.reviewed_by.is_not(None))
        .where(KnowledgeSourceVersion.content_sha256.is_not(None))
        .order_by(KnowledgeSource.id)
        .limit(50)
    )
    visible = []
    for source, version in db.execute(query).all():
        if (not version.reviewed_by or len(version.content_sha256) != 64
            or any(c not in "0123456789abcdef" for c in version.content_sha256)):
            continue
        visible.append(ApprovedSource(
            source_id=source.id, source_version_id=version.id,
            revision=version.revision, institution=source.institution,
            title=source.title, official_url=source.official_url,
            language=source.language, jurisdiction=source.jurisdiction,
            procedure_id=source.procedure_id, reviewed_at=version.reviewed_at,
            content_sha256=version.content_sha256,
        ))
    return SourceCatalog(
        status="approved_sources_available" if visible else "insufficient_evidence",
        sources=visible,
    )
