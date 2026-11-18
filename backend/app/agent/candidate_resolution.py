"""Choose a read-only worker response when procedure routing is unresolved."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from uuid import uuid4

from app.agent.catalogue_applicability import resolve_candidate_applicability
from app.agent.checkpoints import MAX_PROCEDURE_CANDIDATES, CheckpointState
from app.agent.clarification_context import ClarificationHint, prepare_clarification_context
from app.agent.clarification_priority import prioritize_routing_fields
from app.agent.contract import AnswerResult, Citation, ClarifyingQuestion, NextAction, OfficialChannel
from app.agent.run_requests import StoredMessage
from app.agent.worker import RequestClarification
from app.knowledge.service_areas import CaseLocation, ServiceArea, resolve_service_areas


@dataclass(frozen=True)
class AssistanceContact:
    """A separately reviewed assistance assignment and its exact official contact page."""

    scope: ServiceArea
    citation: Citation


_QUESTIONS = {
    "intent": ("What would you like help with?", "Per cosa ti serve aiuto?"),
    "procedure": (
        "Which procedure do you need help with?", "Per quale pratica ti serve aiuto?",
    ),
    "case_reference": (
        "Which saved case would you like to resume?", "Quale pratica salvata vuoi riprendere?",
    ),
    ("location", "destination"): (
        "Which municipality are you moving to?", "In quale comune ti trasferisci?",
    ),
    ("location", "activity_location"): (
        "In which municipality does the activity take place?", "In quale comune si svolge l’attività?",
    ),
    ("date", "filing_date"): (
        "What is the filing date for this case?", "Qual è la data di presentazione della pratica?",
    ),
    ("date", "move_in_date"): ("On what date did you move in?", "In quale data ti sei trasferito o trasferita?"),
    ("circumstance", "housing_basis"): (
        "Do you own the home, rent it, or live there under another arrangement?",
        "La casa è di tua proprietà, è in affitto o ci abiti a un altro titolo?",
    ),
}
_IDENTITY_FIELDS = ("intent", "case_reference", "procedure")
_ROUTING_FIELDS = tuple(field for field in _QUESTIONS if isinstance(field, tuple))
_FIELD_LABELS = {
    "destination": ("the destination municipality", "il comune di destinazione"),
    "activity_location": ("the municipality where the activity takes place", "il comune in cui si svolge l’attività"),
    "filing_date": ("the filing date", "la data di presentazione"),
    "move_in_date": ("the move-in date", "la data del trasferimento"),
    "housing_basis": ("the housing arrangement", "il titolo di occupazione"),
}
_CONTEXT_PROMPTS = {
    "message": (
        "Can you confirm {field} you gave in your message for this case?",
        "Puoi confermare per questa pratica {field} che hai indicato nel messaggio?",
    ),
    "needs_review": (
        "Please review {field} in your document and confirm it for this case.",
        "Puoi controllare {field} nel documento e confermarlo per questa pratica?",
    ),
    "reviewed": (
        "Can you confirm that {field} you reviewed in your document applies to this case?",
        "Puoi confermare per questa pratica {field} che hai verificato nel documento?",
    ),
    "conflict": (
        "I have conflicting information about {field}. Which detail applies to this case?",
        "I dati disponibili sono discordanti per {field}. Quale dato vale per questa pratica?",
    ),
}
_DATE_REPLY_HINTS = (
    "Enter {field} between 1900 and 2100 in YYYY-MM-DD or DD/MM/YYYY format.",
    "Inserisci {field} tra il 1900 e il 2100, nel formato AAAA-MM-GG o GG/MM/AAAA.",
)
_HOUSING_REPLY_HINTS = (
    "Select the choice that describes your housing arrangement.",
    "Seleziona l’opzione che descrive il tuo titolo di occupazione.",
)
_HOUSING_OPTIONS = (
    [
        "I own the home", "I rent under a registered private agreement", "I rent under a different arrangement",
        "I live there as a guest", "Another arrangement",
    ],
    [
        "La casa è di mia proprietà", "Ho un contratto di locazione privata registrato",
        "Ho un altro tipo di affitto", "Ci abito come ospite", "Un altro titolo",
    ],
)
_DEFERRAL_NOTES = {
    "unknown": (
        "I’ll leave the details you’re unsure about open.",
        "Lascio aperti i dettagli di cui non sei sicuro o sicura.",
    ),
    "skip": (
        "I’ll leave the skipped details open for now.",
        "Lascio aperti per ora i dettagli che hai saltato.",
    ),
}


def _clarification_prompt(field: str, base: str, language: int, hint: ClarificationHint | None) -> str:
    if hint is None or field not in _FIELD_LABELS:
        return base
    return _CONTEXT_PROMPTS[hint][language].format(field=_FIELD_LABELS[field][language])


def _grouped_prompt(fields: list[str], language: int) -> str:
    labels = [_FIELD_LABELS[field][language] for field in fields]
    joiner = (" and ", " e ")[language]
    details = joiner.join([", ".join(labels[:-1]), labels[-1]])
    templates = (
        "I need these details together to check whether this route applies. Can you provide {details}?",
        "Mi servono tutti questi dati per verificare se la procedura si applica. Puoi indicare {details}?",
    )
    return templates[language].format(details=details)


def choose_candidate_step(
    message: StoredMessage, state: CheckpointState, *,
    case_locations: Mapping[str, CaseLocation], confirmed_dates: Mapping[str, date],
    confirmed_circumstances: Mapping[str, str], assignments: Sequence[ServiceArea],
    trusted_passage_ids: frozenset[str], reviewed_labels: Mapping[str, str],
    assistance_contacts: Sequence[AssistanceContact] = (),
) -> CheckpointState | RequestClarification | AnswerResult:
    """Use server-reviewed assignments and confirmed facts at a worker boundary."""
    if state.next_node != "choose_next_step":
        raise ValueError("Candidate resolution requires the choose_next_step node")

    context = prepare_clarification_context(
        message, procedure_ids=state.procedure_candidates, case_locations=case_locations,
        confirmed_dates=confirmed_dates, confirmed_circumstances=confirmed_circumstances,
    )
    case_locations = context.case_locations
    confirmed_dates = context.confirmed_dates
    confirmed_circumstances = context.confirmed_circumstances
    results = resolve_candidate_applicability(
        state, case_locations=case_locations, confirmed_dates=confirmed_dates,
        confirmed_circumstances=confirmed_circumstances, assignments=tuple(assignments),
        trusted_passage_ids=trusted_passage_ids,
    )
    plausible = [procedure for procedure, result in results.items() if result.status != "unresolved"]
    separate_tasks = state.intent == "plan_multiple_tasks" and "procedure" not in state.missing_fields
    procedure_conflict = len(plausible) > 1 and not separate_tasks
    authority_conflicts = [result for result in results.values() if result.status == "ambiguous"]
    conflict = procedure_conflict or bool(authority_conflicts)
    pending = [result for result in results.values() if result.status == "needs_information"]
    language = 0 if message.language == "en" else 1
    hint = ("Possible matches include", "Tra le possibili corrispondenze ci sono")[language]

    identity_gap = next((field for field in _IDENTITY_FIELDS if field in state.missing_fields), None)
    question_field = identity_gap
    if question_field is None and procedure_conflict:
        question_field = "procedure"
    question = _QUESTIONS.get(question_field)
    missing_information = [question_field] if question_field else []
    if question_field is None and not conflict:
        fields = prioritize_routing_fields(pending, _ROUTING_FIELDS, context.hints)
        if fields:
            question = _QUESTIONS[fields[0]]
            question_field = fields[0][1]
            missing_information = [name for _, name in fields]

    candidate_ids = plausible if procedure_conflict else list(results)
    if question and question_field and message.clarification_reply is None:
        context_hint = context.hints.get(question_field)
        prompt = _clarification_prompt(question_field, question[language], language, context_hint)
        if len(missing_information) > 1:
            prompt = _grouped_prompt(missing_information, language)
        if question_field == "procedure":
            labels = _candidate_labels(candidate_ids, reviewed_labels)
            if labels and len(details := f"{prompt} {hint} {labels}.") <= 300:
                prompt = details
        options = []
        answer_format = reply_hint = None
        if len(missing_information) == 1 and context_hint is None:
            if question_field == "housing_basis":
                options = _HOUSING_OPTIONS[language]
                reply_hint = _HOUSING_REPLY_HINTS[language]
            elif question_field in ("filing_date", "move_in_date"):
                answer_format = "calendar_date"
                reply_hint = _DATE_REPLY_HINTS[language].format(field=_FIELD_LABELS[question_field][language])
        return RequestClarification(
            ClarifyingQuestion(
                question_id=uuid4(), text=prompt, missing_fields=missing_information,
                answer_shape="single_choice" if options else "free_text", options=options,
                answer_format=answer_format, reply_hint=reply_hint,
            ),
            resume_state=state,
        )

    if not question_field and results and all(result.status == "supported" for result in results.values()):
        missing = [field for field in state.missing_fields if field != "procedure_location"]
        return state.model_copy(update={"next_node": "verify_and_respond", "missing_fields": missing})

    if conflict:
        explanation = (
            "The reviewed records point to multiple candidates.",
            "Le fonti verificate indicano più candidati.",
        )[language]
        if not procedure_conflict:
            candidate_ids = [authority for result in authority_conflicts for authority in result.authority_ids]
        if labels := _candidate_labels(candidate_ids, reviewed_labels):
            explanation += f" {hint} {labels}."
    else:
        explanation = (
            "I could not verify an applicable procedure and authority with the available information.",
            "Con le informazioni disponibili non ho potuto verificare la pratica applicabile e l’ente competente.",
        )[language]

    disposition = message.clarification_reply.disposition if message.clarification_reply else None
    deferral_note = _DEFERRAL_NOTES.get(disposition)
    if deferral_note:
        explanation = f"{deferral_note[language]} {explanation}"
        if message.clarification_question:
            still_open = set(missing_information)
            for result in pending:
                still_open.update(result.missing_location_roles)
                still_open.update(result.missing_date_fields)
                still_open.update(result.missing_circumstance_fields)
            fallback_fields = message.clarification_question.missing_fields
            unanswered = [field for field in fallback_fields if not still_open or field in still_open]
            missing_information = list(dict.fromkeys([*unanswered, *missing_information]))[:12]

    contacts = [
        contact.citation for contact in assistance_contacts
        if len(results) == 1 and identity_gap is None
        and contact.scope.procedure_id in results
        and contact.scope.procedure_id == contact.citation.procedure_id
        and contact.scope.evidence_ref == contact.citation.passage_id
        and contact.scope.unit_ids == (contact.citation.location_id,)
        and resolve_service_areas(
            contact.scope.procedure_id, case_locations, (contact.scope,),
            trusted_passage_ids=trusted_passage_ids, confirmed_dates=confirmed_dates,
            confirmed_circumstances=confirmed_circumstances,
        ).status == "supported"
    ]
    channel = action = None
    if len(contacts) == 1:
        citation = contacts[0]
        label = ("Ask for official assistance", "Chiedi assistenza ufficiale")[language]
        action = NextAction(label=label, operation="open_official_channel")
        channel = OfficialChannel(label=citation.publisher, url=citation.official_url)
    elif deferral_note and missing_information:
        label = ("Provide the missing details later", "Fornisci i dettagli mancanti in seguito")[language]
        action = NextAction(label=label, operation="provide_information")
    return AnswerResult(
        explanation=explanation,
        verification_status="conflicting_evidence" if conflict else "insufficient_evidence",
        missing_information=missing_information,
        official_channel=channel, next_action=action, citations=contacts if channel else [],
    )


def _candidate_labels(candidate_ids: Sequence[str], reviewed_labels: Mapping[str, str]) -> str:
    labels = [reviewed_labels.get(candidate, "").strip() for candidate in candidate_ids]
    unique_labels = list(dict.fromkeys(label for label in labels if 0 < len(label) <= 120))
    return ", ".join(unique_labels[:MAX_PROCEDURE_CANDIDATES])
