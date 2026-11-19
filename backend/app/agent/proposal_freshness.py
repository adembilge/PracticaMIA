"""Case and registry snapshots for the approved case-write transaction."""

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json

from pydantic import Field
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.agent.contract import ContractModel, PassageId
from app.cases.intake_model import CaseIntake
from app.cases.model import CaseRecord
from app.knowledge.model import KnowledgeSource, KnowledgeSourceVersion
from app.knowledge.search import resolve_approved_passage
from app.knowledge.snapshot_model import KnowledgePassage
from app.rules.engine import JURISDICTION, PROCEDURE


class ProposalFreshness(ContractModel):
    case_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    passage_ids: list[PassageId] = Field(max_length=30)
    evidence_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


def _encode_time(value: datetime) -> str:
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat()


def _fingerprint(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=_encode_time)
    return sha256(encoded.encode()).hexdigest()


def case_snapshot_query(case_id: str, owner: str):
    return (
        select(CaseRecord, CaseIntake)
        .outerjoin(CaseIntake, and_(
            CaseIntake.case_id == CaseRecord.id, CaseIntake.owner_subject == CaseRecord.owner_subject,
        ))
        .where(CaseRecord.id == case_id, CaseRecord.owner_subject == owner)
        .execution_options(populate_existing=True)
    )


def case_proposal_fingerprint(case: CaseRecord, intake: CaseIntake | None) -> str | None:
    if case.procedure != PROCEDURE or case.archived_at is not None:
        return None
    return _fingerprint([
        case.id, case.procedure, case.status, case.scope_answers, case.created_at, case.updated_at,
        None if intake is None else [
            intake.facts, intake.confirmed_at, intake.updated_at,
            intake.checklist_progress, intake.progress_fingerprint,
        ],
    ])


def proposal_evidence_fingerprint(db: Session, passage_ids: list[str]) -> str | None:
    """Verify exact versions and hold their registry rows through commit."""
    if not passage_ids:
        return _fingerprint([])

    sources = (
        select(KnowledgeSourceVersion.source_id)
        .join(KnowledgePassage, KnowledgePassage.version_id == KnowledgeSourceVersion.id)
        .where(KnowledgePassage.id.in_(passage_ids))
    )
    # Ingestion and review lock these same rows before changing a version.
    db.scalars(
        select(KnowledgeSource.id).where(KnowledgeSource.id.in_(sources))
        .order_by(KnowledgeSource.id).with_for_update(read=True)
    ).all()

    evidence = []
    for passage_id in sorted(set(passage_ids)):
        passage = resolve_approved_passage(
            db, citation_id=passage_id, jurisdiction=JURISDICTION, procedure_id=PROCEDURE, language="it",
        )
        if passage is None:
            return None
        evidence.append(asdict(passage))
    return _fingerprint(evidence)
