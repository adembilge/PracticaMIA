"""Choose a read-only worker response when procedure routing is unresolved."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
import re
from uuid import uuid4

from app.agent.catalogue_applicability import resolve_candidate_applicability
from app.agent.checkpoints import CheckpointState
from app.agent.clarification_context import ClarificationHint, prepare_clarification_context
from app.agent.clarification_priority import prioritize_routing_fields
from app.agent.contract import (
    MAX_PROCEDURE_CANDIDATES, AnswerResult, Citation, ClarifyingQuestion, EvidenceLinkedClaim, GoalSelection,
    NextAction, OfficialChannel,
)
from app.agent.filing_clarification import (
    MARRIAGE_BANNS, PERMIT_RENEWAL, marriage_municipality_question, permit_category_question,
    mentions_renewal, reports_conflicting_postal_filing, verify_filing_channel,
)
from app.agent.notice_clarification import NoticeField, unreadable_notice_field
from app.agent.routing_corrections import (
    ROUTING_FIELD_LABELS as _FIELD_LABELS, apply_routing_reply, citizenship_options, housing_options,
)
from app.agent.run_requests import StoredMessage
from app.agent.worker import RequestClarification
from app.knowledge.entity_matching import CatalogueName, normalize_name
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
    ("circumstance", "citizenship_class"): (
        "What citizenship category applies to this case?", "Quale categoria di cittadinanza vale per questa pratica?",
    ),
}
_IDENTITY_FIELDS = ("intent", "case_reference", "procedure")
_FORM_LIMIT_CUES = (
    re.compile(r"\banpr\b"),
    re.compile(r"\b(?:old(?:er)? (?:anpr )?(?:guide|handbook)|(?:vecchia|precedente) guida|guida (?:vecchia|precedente))\b"),
    re.compile(r"\b(?:upload|uploads|attachment size|caricamento|dimensione (?:degli )?allegati)\b"),
    re.compile(r"\b(?:limit|maximum|limite|massimo)\b"),
    re.compile(r"\b(?:(?:current|today s|latest) (?:anpr )?form|modulo (?:attuale|di oggi|aggiornato))\b"),
)
_NOTICE_PROMPTS = {
    "appointment_date": (
        "Can you share just the line with the appointment date, if you can read it?",
        "Puoi riportare solo la riga con la data dell’appuntamento, se riesci a leggerla?",
    ),
    "attachment_name": (
        "Can you share just the line that names the requested attachment, if you can read it?",
        "Puoi riportare solo la riga con il nome dell’allegato richiesto, se riesci a leggerla?",
    ),
}
_NOTICE_HINTS = (
    "Remove names, identifiers and other personal details. If the line is still unreadable, check with the issuing office.",
    "Oscura nomi, identificativi e altri dati personali. Se la riga resta illeggibile, chiedi conferma all’ufficio che ha emesso l’avviso.",
)
_ROUTING_FIELDS = tuple(field for field in _QUESTIONS if isinstance(field, tuple))
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
    catalogue_names: Sequence[CatalogueName] = (),
) -> CheckpointState | RequestClarification | AnswerResult:
    """Use server-reviewed assignments and confirmed facts at a worker boundary."""
    if state.next_node != "choose_next_step":
        raise ValueError("Candidate resolution requires the choose_next_step node")
    if state.goals:
        return _choose_message_goal(message, state, reviewed_labels)
    if state.intent == "explain_notice" and (field := unreadable_notice_field(message.text)):
        return _clarify_notice(message, state, field)
    if state.intent == "request_information" and _asks_about_current_upload_limit(message.text):
        return _check_current_form(message.language)
    if state.intent == "find_procedure" and reports_conflicting_postal_filing(message.text):
        return verify_filing_channel(message.language, reported_notice=True)

    revised = apply_routing_reply(message, state, catalogue_names)
    applied_correction = revised is not state
    state = revised
    corrections = state.routing_corrections
    if corrections and corrections.procedure:
        # The previous procedure's role and date inputs cannot be assumed for the replacement.
        case_locations, confirmed_dates, confirmed_circumstances = {}, {}, {}
    context = prepare_clarification_context(
        message, procedure_ids=state.procedure_candidates, case_locations=case_locations,
        confirmed_dates=confirmed_dates, confirmed_circumstances=confirmed_circumstances,
    )
    case_locations = dict(context.case_locations)
    confirmed_dates = dict(context.confirmed_dates)
    confirmed_circumstances = dict(context.confirmed_circumstances)
    corrected_fields = corrections.model_dump(exclude_none=True) if corrections else {}
    for field in ("destination", "activity_location"):
        if municipality := corrected_fields.get(field):
            existing = case_locations.get(field)
            if existing is None or not existing.confirmed or existing.municipality_id != municipality:
                case_locations[field] = CaseLocation(municipality_id=municipality, confirmed=True)
    for field in ("move_in_date", "filing_date"):
        if value := corrected_fields.get(field):
            confirmed_dates[field] = value
    for field in ("housing_basis", "citizenship_class"):
        if value := corrected_fields.get(field):
            confirmed_circumstances[field] = value
    hints = {field: hint for field, hint in context.hints.items() if field not in corrected_fields}
    results = resolve_candidate_applicability(
        state, case_locations=case_locations, confirmed_dates=confirmed_dates,
        confirmed_circumstances=confirmed_circumstances, assignments=tuple(assignments),
        trusted_passage_ids=trusted_passage_ids,
    )
    if state.intent == "find_procedure" and len(results) == 1 and "procedure" not in state.missing_fields:
        procedure, applicability = next(iter(results.items()))
        if applicability.status == "unresolved":
            question = None
            if procedure == PERMIT_RENEWAL and mentions_renewal(message.text) and not confirmed_circumstances.get(
                "permit_category"
            ):
                question = permit_category_question(message.language)
            elif procedure == MARRIAGE_BANNS:
                question = marriage_municipality_question(
                    message.text, message.language, catalogue_names=catalogue_names, case_locations=case_locations,
                )
            if question is not None:
                if message.clarification_reply is None:
                    return RequestClarification(question, state)
                answer = verify_filing_channel(message.language)
                if message.clarification_reply.disposition in ("unknown", "skip"):
                    return answer.model_copy(update={"missing_information": question.missing_fields})
                return answer
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
        fields = prioritize_routing_fields(pending, _ROUTING_FIELDS, hints)
        if fields:
            question = _QUESTIONS[fields[0]]
            question_field = fields[0][1]
            missing_information = [name for _, name in fields]

    candidate_ids = plausible if procedure_conflict else list(results)
    can_ask = message.clarification_reply is None or (applied_correction and question_field not in corrected_fields)
    if question and question_field and can_ask:
        context_hint = hints.get(question_field)
        prompt = _clarification_prompt(question_field, question[language], language, context_hint)
        if len(missing_information) > 1:
            prompt = _grouped_prompt(missing_information, language)
        if question_field == "procedure":
            labels = _candidate_labels(candidate_ids, reviewed_labels)
            if labels and len(details := f"{prompt} {hint} {labels}.") <= 300:
                prompt = details
        options = []
        answer_format = reply_hint = None
        if len(missing_information) > 1:
            reply_hint = (
                "Put each detail on its own line in the form label: value.",
                "Scrivi ogni dato su una riga separata nel formato etichetta: valore.",
            )[language]
        elif question_field == "citizenship_class":
            options = citizenship_options(message.language)
        elif context_hint is None:
            if question_field == "housing_basis":
                options = housing_options(message.language)
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
        return state.model_copy(update={
            "next_node": "find_evidence" if corrections else "verify_and_respond", "missing_fields": missing,
        })

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
    claims = []
    if len(contacts) == 1:
        citation = contacts[0]
        label = ("Ask for official assistance", "Chiedi assistenza ufficiale")[language]
        action = NextAction(label=label, operation="open_official_channel")
        channel = OfficialChannel(label=citation.publisher, url=citation.official_url)
        claims.append(EvidenceLinkedClaim(
            kind="channel", evidence_ids=[citation.passage_id], statement=(
                "The cited source provides an official contact for this procedure.",
                "La fonte citata fornisce un contatto ufficiale per questa pratica.",
            )[language],
        ))
    elif deferral_note and missing_information:
        label = ("Provide the missing details later", "Fornisci i dettagli mancanti in seguito")[language]
        action = NextAction(label=label, operation="provide_information")
    return AnswerResult(
        explanation=explanation,
        verification_status="conflicting_evidence" if conflict else "insufficient_evidence",
        missing_information=missing_information,
        official_channel=channel, next_action=action, citations=contacts if channel else [], claims=claims,
    )


def _clarify_notice(
    message: StoredMessage, state: CheckpointState, field: NoticeField,
) -> RequestClarification | AnswerResult:
    language = 0 if message.language == "en" else 1
    question = message.clarification_question
    if message.clarification_reply is None or question is None or question.answer_format != "redacted_excerpt":
        return RequestClarification(
            question=ClarifyingQuestion(
                question_id=uuid4(), text=_NOTICE_PROMPTS[field][language], answer_shape="free_text",
                missing_fields=[field], answer_format="redacted_excerpt", reply_hint=_NOTICE_HINTS[language],
            ),
            resume_state=state,
        )
    return AnswerResult(
        explanation=(
            "Check the readable original or ask the issuing office to confirm the detail."
            if language == 0
            else "Controlla l’originale leggibile o chiedi conferma all’ufficio che ha emesso l’avviso."
        ),
        verification_status="insufficient_evidence", missing_information=[field],
        next_action=NextAction(
            label="Check the notice" if language == 0 else "Controlla l’avviso", operation="provide_information",
        ),
    )


def _asks_about_current_upload_limit(text: str) -> bool:
    normalized = normalize_name(text)
    return all(cue.search(normalized) for cue in _FORM_LIMIT_CUES)


def _check_current_form(language: str) -> AnswerResult:
    en = language == "en"
    return AnswerResult(
        explanation=(
            "Check the upload limit shown in the current ANPR form. If it is unclear, ask the registry office to confirm it."
            if en else
            "Controlla il limite di caricamento nel modulo ANPR attuale. Se non è chiaro, chiedi conferma all’ufficio anagrafe."
        ),
        verification_status="insufficient_evidence",
        next_action=NextAction(
            label="Check the current ANPR form" if en else "Controlla il modulo ANPR attuale",
            operation="check_current_form",
        ),
    )


def _candidate_labels(candidate_ids: Sequence[str], reviewed_labels: Mapping[str, str]) -> str:
    labels = [reviewed_labels.get(candidate, "").strip() for candidate in candidate_ids]
    unique_labels = list(dict.fromkeys(label for label in labels if 0 < len(label) <= 120))
    return ", ".join(unique_labels[:MAX_PROCEDURE_CANDIDATES])


def _choose_message_goal(
    message: StoredMessage, state: CheckpointState, reviewed_labels: Mapping[str, str],
) -> RequestClarification | AnswerResult:
    language = message.language
    en = language == "en"
    question, reply = message.clarification_question, message.clarification_reply
    if question is not None and question.procedure_goal is not None and reply is not None and (
        reply.question_id == question.question_id
    ):
        answer = verify_filing_channel(language)
        return answer.model_copy(update={
            "goals": state.goals, "goal_selection": question.procedure_goal,
            "missing_information": question.missing_fields if reply.disposition in ("unknown", "skip") else [],
        })
    responded = (
        question is not None and question.goal_selection_language is not None
        and reply is not None and reply.question_id == question.question_id
    )
    active_goal = state.preferred_goal
    if responded:
        options = question.options
        active_goal = reply.selected_goal
    else:
        options = []
        for number, goal in enumerate(state.goals, 1):
            procedure = _candidate_labels(goal.procedure_candidates, reviewed_labels)[:120].rstrip()
            place = _candidate_labels(goal.location_candidates, reviewed_labels)[:120].rstrip()
            title = procedure or ("Procedure to identify" if en else "Pratica da identificare")
            options.append(f"{number}. {title}" + (f" · {place}" if place else ""))

    if active_goal is None and not responded:
        return RequestClarification(
            ClarifyingQuestion(
                question_id=uuid4(), text="Which task should we start with?" if en else "Da quale pratica iniziamo?",
                answer_shape="single_choice", options=options, missing_fields=["active_goal"],
                goal_selection_language=language,
            ),
            resume_state=state,
        )

    if active_goal is None:
        explanation = "You can choose a task in a new message." if en else (
            "Puoi scegliere una pratica in un nuovo messaggio."
        )
        missing = state.missing_fields
    else:
        explanation = "The selected task is ready for its own case and procedure checks." if en else (
            "La pratica selezionata può passare alla verifica dei suoi dati e della procedura."
        )
        missing = state.goals[active_goal - 1].missing_fields
    return AnswerResult(
        explanation=explanation, verification_status="insufficient_evidence", missing_information=missing,
        goals=state.goals, goal_selection=GoalSelection(language=language, options=options, active_goal=active_goal),
    )
