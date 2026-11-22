"""Case-free Phase 4 conversational LangGraph for the bounded Preview worker.

The graph owns intent routing, location clarification, approved-only retrieval
and reference-only publication. It never creates or selects a user-facing case,
never infers a legal rule, and never publishes a verified claim. The first
pilot scope is enabled only while its exact approved source passage is active.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from psycopg import OperationalError as PostgresOperationalError
from sqlalchemy.exc import DBAPIError, TimeoutError as PoolTimeout
from sqlalchemy.orm import sessionmaker

from app.agent.catalogue_evidence import CatalogueUnavailable, catalogue_passage
from app.agent.candidate_resolution import choose_candidate_step
from app.agent.checkpoints import CheckpointState
from app.agent.contract import AnswerResult, ClarifyingQuestion, NextAction
from app.agent.intent_extraction import identify_intent_step
from app.agent.model_adapter import ModelReferenceSelector
from app.agent.routing_corrections import apply_routing_reply
from app.agent.run_requests import StoredMessage
from app.agent.worker import RequestClarification
from app.config import Settings
from app.knowledge.entity_matching import CatalogueName, normalize_name
from app.knowledge.search import EvidencePassage, resolve_approved_passage, search_approved_passages
from app.knowledge.service_areas import CaseLocation
from app.rules.engine import JURISDICTION, PROCEDURE

PILOT_SCOPE_CITATION = "e139e910-3a89-4994-b450-b5107d8db7dd:0000"
_TRANSIENT_SQLSTATES = frozenset({"40001", "40P01", "53300", "55P03", "57P01", "57P02", "57P03"})


class ChatGraphState(TypedDict, total=False):
    message: StoredMessage
    checkpoint: CheckpointState
    catalogue_names: Sequence[CatalogueName]
    passages: list[EvidencePassage]
    result: Any


def _is_transient_database_error(exc: DBAPIError) -> bool:
    sqlstate = getattr(exc.orig, "sqlstate", None)
    return bool(
        exc.connection_invalidated
        or (sqlstate is not None and (
            sqlstate.startswith("08") or sqlstate in _TRANSIENT_SQLSTATES
        ))
        or (sqlstate is None and isinstance(exc.orig, PostgresOperationalError))
    )


def load_pilot_catalogue_names(sessions: sessionmaker) -> tuple[CatalogueName, ...]:
    """Enable only narrow aliases while the exact approved Milan passage is active."""
    with sessions() as db:
        active = resolve_approved_passage(
            db, citation_id=PILOT_SCOPE_CITATION, jurisdiction=JURISDICTION,
            procedure_id=PROCEDURE, language="it",
        )
    if active is None:
        return ()

    # English variants are search/routing vocabulary, not additional official
    # names or proof of applicability. The source is rechecked at retrieval
    # and publication, so revocation disables both references and this route.
    records = (
        ("procedure", PROCEDURE, "Cambio di residenza", "cambio di residenza", "current_official"),
        ("procedure", PROCEDURE, "Cambio di residenza", "cambiare la residenza", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "cambio residenza", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "residence change", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "change of residence", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "change residence", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "change my address", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "address change", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "cambio di indirizzo", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "file the residence change", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "file my residence change", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "change address", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "registered residence", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "registered address", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "register a new address", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "register my new address", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "comunicare il nuovo indirizzo", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "registrare il nuovo indirizzo", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "update my registered address", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "change my registered residence", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "transfer my residence", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "register my residence", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "trasferire la residenza", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "spostare la residenza", "search_variant"),
        ("procedure", PROCEDURE, "Cambio di residenza", "fare il cambio di residenza", "search_variant"),
        ("municipality", JURISDICTION, "Milano", "Milano", "current_official"),
        ("municipality", JURISDICTION, "Milano", "Milan", "search_variant"),
    )
    return tuple(CatalogueName(
        catalogue_id=catalogue_id, entity_type=entity_type, display_name=display_name,
        name=name, kind=kind, evidence_ref=active.citation_id, approved_for_search=True,
    ) for entity_type, catalogue_id, display_name, name, kind in records)


def _next(state: ChatGraphState) -> str:
    if state.get("result") is not None:
        return END
    return state["checkpoint"].next_node


def _answer_without_evidence(language: str, *, unsupported: bool = False) -> AnswerResult:
    if language == "it":
        explanation = (
            "In questa anteprima sono disponibili riferimenti verificati solo per il percorso di cambio di residenza a Milano. "
            "Non posso fornire indicazioni verificate per il comune indicato."
            if unsupported else
            "Non ho trovato estratti ufficiali attualmente approvati per questa domanda. "
            "Non dedurrò requisiti o scadenze non verificati."
        )
        label = "Fornisci altri dettagli"
    else:
        explanation = (
            "This Preview currently has reviewed reference scope only for the Milan residence-change route. "
            "I cannot provide verified guidance for the municipality named."
            if unsupported else
            "I could not find currently approved official excerpts for this question. "
            "I will not infer unverified requirements or deadlines."
        )
        label = "Provide more details"
    return AnswerResult(
        explanation=explanation,
        verification_status="unsupported" if unsupported else "insufficient_evidence",
        missing_information=["procedure_location"] if unsupported else [],
        next_action=NextAction(label=label, operation="provide_information"),
    )


def _search_query(message: StoredMessage) -> str:
    text = normalize_name(message.text)
    if re.search(r"\btari\b", text):
        return "TARI"
    if any(term in text.split() for term in ("lease", "rental", "locazione", "affitto")):
        return "locazione"
    if any(term in text.split() for term in ("upload", "attachment", "allegati", "allegato")):
        return "allegati"
    if any(term in text.split() for term in ("domicilio", "domicile")):
        return "domicilio"
    return "residenza"


def _clarify_location(state: CheckpointState) -> RequestClarification:
    question = ClarifyingQuestion(
        question_id=uuid4(),
        text=(
            "Which municipality is this about? This Preview can currently retrieve reviewed references only for Milano."
            if state.intent != "request_information" else
            "Which municipality does your question concern? Reviewed references are currently available only for Milano."
        ),
        answer_shape="single_choice",
        options=["Milano", "Another municipality"],
        missing_fields=["destination"],
        reply_hint="Choose Milano only if it is the municipality relevant to your request.",
    )
    return RequestClarification(question=question, resume_state=state)


def build_chat_graph(
    sessions: sessionmaker, *, catalogue_names: Sequence[CatalogueName] | None = None,
    reference_selector: ModelReferenceSelector | None = None,
):
    """Compile the actual one-chat execution graph; durable boundaries stay in worker.py."""
    def names() -> tuple[CatalogueName, ...] | CatalogueUnavailable:
        if catalogue_names is not None:
            return tuple(catalogue_names)
        try:
            return load_pilot_catalogue_names(sessions)
        except PoolTimeout:
            return CatalogueUnavailable("Catalogue temporarily unavailable")
        except DBAPIError as exc:
            if _is_transient_database_error(exc):
                return CatalogueUnavailable("Catalogue temporarily unavailable")
            raise

    def load_context(state: ChatGraphState) -> dict:
        if state["message"].case_id is not None:
            raise ValueError("The chat-only worker accepts unlinked conversation messages")
        return {"checkpoint": state["checkpoint"].model_copy(update={"next_node": "identify_intent"})}

    def identify_intent(state: ChatGraphState) -> dict:
        message, checkpoint = state["message"], state["checkpoint"]
        available_names = names()
        if isinstance(available_names, CatalogueUnavailable):
            return {"result": available_names}
        identified = identify_intent_step(message, checkpoint, catalogue_names=available_names)
        normalized = normalize_name(message.text)
        # TARI is a separate municipal declaration, but the approved FAQ has a
        # reference passage for it within the Milan residence-change topic.
        if identified.intent == "request_information" and "tari" in normalized.split():
            if identified.location_candidates == [JURISDICTION]:
                identified = identified.model_copy(update={
                    "next_node": "find_evidence", "procedure_candidates": [PROCEDURE],
                    "location_candidates": [JURISDICTION], "missing_fields": [],
                })
            else:
                identified = identified.model_copy(update={
                    "next_node": "choose_next_step", "procedure_candidates": [PROCEDURE],
                    "missing_fields": ["procedure_location"],
                })
        return {"checkpoint": identified, "catalogue_names": available_names}

    def choose_next_step(state: ChatGraphState) -> dict:
        message, checkpoint = state["message"], state["checkpoint"]
        if message.case_id is None and checkpoint.intent == "resume_case":
            return {"result": AnswerResult(
                explanation=(
                    "To resume a different topic, open its conversation from the history sidebar. "
                    "You can also describe the topic here and continue in this chat."
                    if message.language == "en" else
                    "Per riprendere un altro argomento, apri la relativa conversazione dalla cronologia. "
                    "Puoi anche descrivere qui l’argomento e continuare in questa chat."
                ),
                verification_status="insufficient_evidence",
            )}
        available_names = state.get("catalogue_names") or names()
        if isinstance(available_names, CatalogueUnavailable):
            return {"result": available_names}
        available_names = tuple(available_names)
        checkpoint = apply_routing_reply(message, checkpoint, available_names)
        if checkpoint.intent == "request_information" and not checkpoint.procedure_candidates:
            missing = list(checkpoint.missing_fields)
            if "procedure" not in missing:
                missing.append("procedure")
            if not checkpoint.location_candidates and "procedure_location" not in missing:
                missing.append("procedure_location")
            checkpoint = checkpoint.model_copy(update={"missing_fields": missing})

        if "procedure_location" in checkpoint.missing_fields and not any(
            field in checkpoint.missing_fields for field in ("intent", "procedure")
        ):
            reply = message.clarification_reply
            if reply is not None and reply.disposition == "answer":
                return {"result": _answer_without_evidence(message.language, unsupported=True)}
            if reply is not None and reply.disposition in ("unknown", "skip"):
                return {"result": AnswerResult(
                    explanation=(
                        "I can leave the municipality open, but cannot check a location-specific route without it."
                        if message.language == "en" else
                        "Posso lasciare in sospeso il comune, ma non posso verificare un percorso locale senza questo dato."
                    ),
                    verification_status="insufficient_evidence",
                    missing_information=["procedure_location"],
                    next_action=NextAction(
                        label="Provide the municipality later" if message.language == "en"
                        else "Indica il comune in seguito",
                        operation="provide_information",
                    ),
                )}
            return {"result": _clarify_location(checkpoint)}

        if (
            checkpoint.procedure_candidates == [PROCEDURE]
            and checkpoint.location_candidates == [JURISDICTION]
            and not checkpoint.missing_fields
        ):
            return {"checkpoint": checkpoint.model_copy(update={"next_node": "find_evidence"})}

        corrections = checkpoint.routing_corrections
        case_locations = {}
        confirmed_dates = {}
        confirmed_circumstances = {}
        if corrections is not None:
            if corrections.destination:
                case_locations["destination"] = CaseLocation(
                    municipality_id=corrections.destination, confirmed=True,
                )
            if corrections.activity_location:
                case_locations["activity_location"] = CaseLocation(
                    municipality_id=corrections.activity_location, confirmed=True,
                )
            for field in ("move_in_date", "filing_date"):
                value = getattr(corrections, field)
                if value is not None:
                    confirmed_dates[field] = value
            for field in ("housing_basis", "citizenship_class"):
                value = getattr(corrections, field)
                if value is not None:
                    confirmed_circumstances[field] = value

        decision = choose_candidate_step(
            message, checkpoint, case_locations=case_locations,
            confirmed_dates=confirmed_dates, confirmed_circumstances=confirmed_circumstances,
            assignments=(), trusted_passage_ids=frozenset(),
            reviewed_labels={item.catalogue_id: item.display_name for item in available_names},
            catalogue_names=available_names,
        )
        if isinstance(decision, RequestClarification):
            return {"result": decision}
        if isinstance(decision, AnswerResult):
            return {"result": decision}
        if decision.next_node == "choose_next_step":
            return {"result": _answer_without_evidence(message.language)}
        return {"checkpoint": decision}

    def find_evidence(state: ChatGraphState) -> dict:
        message, checkpoint = state["message"], state["checkpoint"]
        if checkpoint.procedure_candidates != [PROCEDURE]:
            return {"result": _answer_without_evidence(message.language, unsupported=True)}
        # Retrieval is limited to this exact approved pilot passage. A place
        # mentioned in the request may guide reference retrieval, but the answer
        # remains explicitly non-applicability advice until scope is confirmed.
        try:
            with sessions() as db:
                passages = search_approved_passages(
                    db, query=_search_query(message), jurisdiction=JURISDICTION,
                    procedure_id=PROCEDURE, language="it", limit=5,
                )
        except PoolTimeout:
            return {"result": CatalogueUnavailable("Catalogue temporarily unavailable")}
        except DBAPIError as exc:
            if _is_transient_database_error(exc):
                return {"result": CatalogueUnavailable("Catalogue temporarily unavailable")}
            raise
        if not passages:
            return {"result": _answer_without_evidence(message.language)}
        next_state = checkpoint.model_copy(update={
            "next_node": "verify_and_respond",
            "evidence_ids": [item.passage_id for item in passages],
        })
        return {"checkpoint": next_state, "passages": passages}

    def verify_and_respond(state: ChatGraphState) -> dict:
        message, checkpoint = state["message"], state["checkpoint"]
        passages = list(state.get("passages", ()))
        if not passages and checkpoint.evidence_ids:
            with sessions() as db:
                passages = [
                    passage for passage_id in checkpoint.evidence_ids
                    if (passage := resolve_approved_passage(
                        db, citation_id=passage_id, jurisdiction=JURISDICTION,
                        procedure_id=PROCEDURE, language=None,
                    )) is not None
                ]
        if reference_selector is not None:
            selected_ids = reference_selector.select(
                owner_subject=message.owner_subject,
                topic_category=_search_query(message),
                passages=passages,
            )
            if selected_ids is not None:
                if not selected_ids:
                    return {"result": _answer_without_evidence(message.language)}
                checkpoint = checkpoint.model_copy(update={"evidence_ids": list(selected_ids)})
        by_id = {item.passage_id: item for item in passages}
        citations = [
            catalogue_passage(by_id[passage_id]).citation
            for passage_id in checkpoint.evidence_ids if passage_id in by_id
        ]
        if not citations:
            return {"result": _answer_without_evidence(message.language)}
        explanation = (
            "I found reviewed official excerpts related to the Milan residence-change topic. "
            "They are reference material only: this does not confirm which requirements apply to your circumstances. "
            "Tell me more about your situation so I can check what information is still needed."
            if message.language == "en" else
            "Ho trovato estratti ufficiali revisionati relativi al cambio di residenza a Milano. "
            "Sono solo riferimenti: non confermano quali requisiti si applichino alla tua situazione. "
            "Descrivimi meglio il tuo caso per verificare quali informazioni servono."
        )
        action = NextAction(
            label="Tell me more about your situation" if message.language == "en"
            else "Descrivi meglio la tua situazione",
            operation="provide_information",
        )
        return {"result": AnswerResult(
            explanation=explanation, verification_status="insufficient_evidence",
            citations=citations, next_action=action,
        )}

    graph = StateGraph(ChatGraphState)
    graph.add_node("load_context", load_context)
    graph.add_node("identify_intent", identify_intent)
    graph.add_node("choose_next_step", choose_next_step)
    graph.add_node("find_evidence", find_evidence)
    graph.add_node("verify_and_respond", verify_and_respond)
    routes = {
        "load_context": "load_context",
        "identify_intent": "identify_intent",
        "choose_next_step": "choose_next_step",
        "find_evidence": "find_evidence",
        "verify_and_respond": "verify_and_respond",
        END: END,
    }
    graph.add_conditional_edges(START, _next, routes)
    for node in ("load_context", "identify_intent", "choose_next_step", "find_evidence", "verify_and_respond"):
        graph.add_conditional_edges(node, _next, routes)
    return graph.compile()


def build_chat_executor(
    sessions: sessionmaker, *, catalogue_names: Sequence[CatalogueName] | None = None,
    settings: Settings | None = None, model_factory: Callable[[], object] | None = None,
) -> Callable[[StoredMessage, CheckpointState], Any]:
    selector = (
        ModelReferenceSelector(sessions, settings, model_factory=model_factory)
        if settings is not None else None
    )
    graph = build_chat_graph(
        sessions, catalogue_names=catalogue_names, reference_selector=selector,
    )

    def execute(message: StoredMessage, checkpoint: CheckpointState):
        if message.case_id is not None:
            raise ValueError("The Phase 4 chat worker does not process legacy case-linked runs")
        result = graph.invoke(
            {"message": message, "checkpoint": checkpoint},
            config={"recursion_limit": 8},
        )
        if result.get("result") is not None:
            return result["result"]
        return result["checkpoint"]

    return execute
