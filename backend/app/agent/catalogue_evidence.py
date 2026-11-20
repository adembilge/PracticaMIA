"""Internal Phase 4 adapter for the existing approved Milan passage catalogue."""

from datetime import timezone
import re
from uuid import UUID

from psycopg import OperationalError as PostgresOperationalError
from pydantic import ValidationError
from sqlalchemy import and_, select
from sqlalchemy.exc import DBAPIError, TimeoutError as PoolTimeout
from sqlalchemy.orm import Session

from app.agent.checkpoints import CheckpointState, RoutingCorrections
from app.agent.contract import AnswerResult, Citation, Language, NextAction
from app.agent.destination_correction import reassess_destination
from app.agent.diagnostics import AgentFailureDiagnostic, EvidenceQueryKind
from app.agent.threads import AgentThread, AgentThreadCase
from app.agent.tool_contract import (
    CatalogueEvidence, CataloguePassage, CatalogueScope, FindEvidence, OpenSourceDetails,
)
from app.agent.tool_access import ToolAccessDenied
from app.agent.tool_execution import check_tool_execution
from app.auth.tokens import Principal
from app.cases.intake_model import CaseIntake
from app.cases.intake_schemas import IntakeFacts, describe_intake
from app.cases.model import CaseRecord
from app.cases.scope import DEMO_ANSWERS, classify_scope
from app.knowledge.entity_matching import normalize_name
from app.knowledge.search import (
    EvidencePassage, normalize_query, resolve_approved_passage, search_approved_passages,
)
from app.rules.engine import JURISDICTION, PROCEDURE

_RESIDENCE_TERMS = re.compile(r"\b(?:residenza|registered residence|registered address)\b")
_DOMICILE_TERMS = re.compile(r"\b(?:domicilio|domicile)\b")
_ADDRESS_CHANGE_TERMS = re.compile(
    r"\b(?:change of address|chang(?:e|ed|ing) (?:my|the|a) address|"
    r"(?:report|register) (?:my|the|a) new address|"
    r"cambio (?:di )?indirizzo|(?:cambio|cambiare) il (?:mio )?indirizzo|"
    r"(?:comunicar|registrar)e il nuovo indirizzo)\b"
)
_ANPR_TERMS = re.compile(r"\b(?:anpr|a n p r)\b")
_MILAN_SCOPE = CatalogueScope(procedure_id=PROCEDURE, location_id=JURISDICTION)
_TRANSIENT_SQLSTATES = frozenset({"40001", "40P01", "53300", "55P03", "57P01", "57P02", "57P03"})


class CatalogueUnavailable(RuntimeError):
    """An evidence lookup failed with a temporary storage error."""


def corrected_query_kind(corrections: RoutingCorrections | None) -> EvidenceQueryKind:
    if corrections is not None and (corrections.procedure is not None or corrections.destination is not None):
        return "procedure_hint"
    return "message_lexical"


def _milan_search_hint(query: str) -> str:
    """Build one lexical fallback. Its terms narrow retrieval inside case scope."""
    key = normalize_name(query)
    terms = []
    if _DOMICILE_TERMS.search(key):
        terms.append("domicilio")
        if _RESIDENCE_TERMS.search(key):
            terms.append("residenza")
    elif _ADDRESS_CHANGE_TERMS.search(key):
        terms.extend(("cambio", "residenza"))
    elif _RESIDENCE_TERMS.search(key):
        terms.append("residenza")
    if _ANPR_TERMS.search(key):
        terms.append("anpr")
    return " ".join(terms)


def _case_evidence_gap(
    db: Session, thread_id: UUID, case_id: UUID, principal: Principal,
) -> CatalogueEvidence | None:
    # Fetch the case link, ownership, scope and intake together so they describe one database
    # snapshot. Select columns directly to avoid reusing cached ORM instances.
    context = db.execute(
        select(
            CaseRecord.procedure, CaseRecord.status, CaseRecord.scope_answers, CaseRecord.archived_at,
            CaseIntake.facts, CaseIntake.confirmed_at,
        )
        .join(AgentThreadCase, AgentThreadCase.case_id == CaseRecord.id)
        .join(AgentThread, AgentThread.id == AgentThreadCase.thread_id)
        .outerjoin(CaseIntake, and_(
            CaseIntake.case_id == CaseRecord.id,
            CaseIntake.owner_subject == CaseRecord.owner_subject,
        ))
        .where(
            AgentThread.id == str(thread_id),
            AgentThread.owner_subject == principal.subject,
            CaseRecord.id == str(case_id),
            CaseRecord.owner_subject == principal.subject,
        )
    ).one_or_none()
    if context is None:
        return CatalogueEvidence(status="case_unavailable")

    procedure, status, scope_answers, archived_at, facts, confirmed_at = context
    if archived_at is not None or procedure != PROCEDURE or status == "unsupported":
        return CatalogueEvidence(status="unsupported_scope")
    if not isinstance(scope_answers, list):
        return CatalogueEvidence(status="needs_information", missing_fields=("scope_answers",))
    if classify_scope(scope_answers) == "unsupported":
        return CatalogueEvidence(status="unsupported_scope")
    if status != "provisionally_in_scope" or tuple(scope_answers) != DEMO_ANSWERS:
        return CatalogueEvidence(status="needs_information", missing_fields=("scope_answers",))

    if confirmed_at is None:
        return CatalogueEvidence(status="needs_information", missing_fields=("intake_confirmation",))
    try:
        typed_facts = IntakeFacts.model_validate(facts).model_dump(exclude_none=True)
    except ValidationError:
        return CatalogueEvidence(status="needs_information", missing_fields=("intake_confirmation",))
    intake = describe_intake(typed_facts, confirmed=True)
    if intake["outside_first_scenario"]:
        return CatalogueEvidence(status="unsupported_scope")
    if not intake["first_scenario_match"]:
        return CatalogueEvidence(status="needs_information", missing_fields=tuple(intake["missing_fields"]))
    return None


def catalogue_passage(passage: EvidencePassage) -> CataloguePassage:
    # All review writes record UTC. SQLite drops the offset on timestamp reads.
    reviewed_at = passage.reviewed_at
    if reviewed_at.tzinfo is None:
        reviewed_at = reviewed_at.replace(tzinfo=timezone.utc)
    return CataloguePassage(
        citation=Citation(
            citation_id=passage.citation_id,
            passage_id=passage.passage_id,
            source_id=passage.source_id,
            source_version_id=passage.source_version_id,
            official_url=passage.official_url,
            publisher=passage.institution,
            reviewed_at=reviewed_at,
            procedure_id=passage.procedure_id,
            location_id=passage.jurisdiction,
        ),
        source_revision=passage.source_revision,
        section_path=passage.section_path,
        content=passage.content,
    )


def find_catalogue_evidence(
    db: Session, *, thread_id: UUID, case_id: UUID, principal: Principal, query: str, limit: int = 5,
) -> CatalogueEvidence:
    """Read Italian excerpts using the owning case's confirmed scope."""
    if gap := _case_evidence_gap(db, thread_id, case_id, principal):
        return gap
    call = FindEvidence(tool="find_evidence", case_id=case_id, scope=_MILAN_SCOPE, query=query, limit=limit)
    search_scope = {
        "jurisdiction": call.scope.location_id, "procedure_id": call.scope.procedure_id,
        "language": "it", "limit": call.limit,
    }
    rows = search_approved_passages(db, query=call.query, **search_scope)
    if not rows and (hint := _milan_search_hint(call.query)) and hint != normalize_query(call.query)[0]:
        rows = search_approved_passages(db, query=hint, **search_scope)
    return CatalogueEvidence(
        status="evidence_found" if rows else "insufficient_evidence",
        passages=tuple(catalogue_passage(row) for row in rows),
    )


def resolve_catalogue_evidence(
    db: Session, *, thread_id: UUID, case_id: UUID, principal: Principal, citation_id: str,
) -> CatalogueEvidence:
    """Recheck an exact citation at use time with the current approval gates."""
    if gap := _case_evidence_gap(db, thread_id, case_id, principal):
        return gap
    try:
        call = OpenSourceDetails(
            tool="open_source_details", case_id=case_id, scope=_MILAN_SCOPE, citation_id=citation_id,
        )
    except ValidationError:
        return CatalogueEvidence(status="insufficient_evidence")
    row = resolve_approved_passage(
        db, citation_id=call.citation_id, jurisdiction=call.scope.location_id,
        procedure_id=call.scope.procedure_id, language="it",
    )
    if row is None:
        return CatalogueEvidence(status="insufficient_evidence")
    return CatalogueEvidence(status="evidence_found", passages=(catalogue_passage(row),))


def read_tool_evidence(
    db: Session, *, thread_id: UUID, run_id: UUID, principal: Principal,
    call: FindEvidence | OpenSourceDetails,
) -> CatalogueEvidence:
    """Authorize the typed read against the current run before looking up evidence."""
    try:
        check_tool_execution(db, principal=principal, thread_id=thread_id, run_id=run_id, call=call)
        if call.scope != _MILAN_SCOPE:
            return CatalogueEvidence(status="unsupported_scope")
        context = {"thread_id": thread_id, "case_id": call.case_id, "principal": principal}
        if isinstance(call, FindEvidence):
            return find_catalogue_evidence(db, **context, query=call.query, limit=call.limit)
        return resolve_catalogue_evidence(db, **context, citation_id=call.citation_id)
    except PoolTimeout as exc:
        raise CatalogueUnavailable("Catalogue temporarily unavailable") from exc
    except DBAPIError as exc:
        sqlstate = getattr(exc.orig, "sqlstate", None)
        if exc.connection_invalidated or (
            sqlstate is not None and (sqlstate.startswith("08") or sqlstate in _TRANSIENT_SQLSTATES)
        ) or (sqlstate is None and isinstance(exc.orig, PostgresOperationalError)):
            raise CatalogueUnavailable("Catalogue temporarily unavailable") from exc
        raise


def refresh_corrected_evidence(
    db: Session, *, state: CheckpointState, thread_id: UUID, run_id: UUID, case_id: UUID | None,
    principal: Principal, query: str, language: Language,
) -> CheckpointState | AnswerResult:
    """Refresh evidence after routing has been reevaluated with a corrected input."""
    corrections = state.routing_corrections
    if state.next_node != "find_evidence" or corrections is None:
        raise ValueError("Evidence refresh requires a corrected routing decision")
    if case_id is not None and state.procedure_candidates == [PROCEDURE] and (
        corrections.destination not in (None, JURISDICTION)
    ):
        return reassess_destination(language)
    if (
        case_id is None or state.procedure_candidates != [PROCEDURE]
        or corrections.activity_location is not None
        or corrections.housing_basis not in (None, "registered_private_rental")
        or corrections.citizenship_class not in (None, "italian")
    ):
        return _unverified_evidence(language, state.missing_fields)

    query_kind = corrected_query_kind(corrections)
    try:
        call = FindEvidence(
            tool="find_evidence", case_id=case_id, scope=_MILAN_SCOPE,
            query="cambio di residenza" if query_kind == "procedure_hint" else query,
        )
    except ValidationError:
        AgentFailureDiagnostic(
            code="catalogue_invalid_query", stage=state.next_node, intent=state.intent, query_kind=query_kind,
        ).emit()
        return AnswerResult(
            explanation=(
                "Enter a search with 1–12 words and at most 180 characters." if language == "en"
                else "Inserisci una ricerca di 1–12 parole e al massimo 180 caratteri."
            ),
            verification_status="insufficient_evidence",
            missing_information=state.missing_fields,
            next_action=NextAction(
                label="Rephrase the search" if language == "en" else "Riformula la ricerca",
                operation="provide_information",
            ),
        )
    evidence = read_tool_evidence(db, thread_id=thread_id, run_id=run_id, principal=principal, call=call)
    if evidence.status == "case_unavailable":
        raise ToolAccessDenied("Tool scope unavailable")
    if evidence.passages:
        return state.model_copy(update={
            "next_node": "verify_and_respond",
            "evidence_ids": [passage.citation.passage_id for passage in evidence.passages],
        })
    AgentFailureDiagnostic(
        code="catalogue_evidence_unavailable", stage=state.next_node, intent=state.intent,
        query_kind=query_kind, tool=call.tool,
    ).emit()
    if "intake_confirmation" in evidence.missing_fields:
        return AnswerResult(
            explanation=(
                "Complete and confirm your saved case details. Then return here and ask for the filing step."
                if language == "en"
                else "Completa e conferma i dati della pratica salvata. Poi torna qui e chiedi come presentarla."
            ),
            verification_status="insufficient_evidence",
            missing_information=["intake_confirmation"],
            next_action=NextAction(
                label="Confirm saved case details" if language == "en" else "Conferma i dati della pratica",
                operation="confirm_saved_intake",
            ),
        )
    return _unverified_evidence(language, list(evidence.missing_fields) or state.missing_fields)


def _unverified_evidence(language: Language, missing_fields: list[str]) -> AnswerResult:
    return AnswerResult(
        explanation=(
            "I could not verify current evidence for the corrected details. Review the case details."
            if language == "en"
            else "Non ho potuto verificare le fonti aggiornate per i dati corretti. Rivedi i dati della pratica."
        ),
        verification_status="insufficient_evidence",
        missing_information=missing_fields,
        next_action=NextAction(
            label="Review the case details" if language == "en" else "Rivedi i dati della pratica",
            operation="provide_information",
        ),
    )
