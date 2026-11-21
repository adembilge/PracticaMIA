"""Read-only intent extraction against a server-supplied reviewed catalogue."""

from collections.abc import Sequence
from dataclasses import dataclass
import re
from typing import Literal
import unicodedata

from app.agent.checkpoints import CheckpointState, RoutingCorrections
from app.agent.case_selection import OTHER_CASE_CUE
from app.agent.contract import MAX_MESSAGE_GOALS, MAX_PROCEDURE_CANDIDATES, AgentIntent, MessageGoal
from app.agent.destination_correction import destination_correction_name
from app.agent.filing_clarification import (
    MARRIAGE_BANNS, PERMIT_RENEWAL, SAVED_CASE_FILING, mentions_marriage_banns, reports_conflicting_postal_filing,
)
from app.agent.notice_clarification import unreadable_notice_field
from app.agent.run_requests import StoredMessage
from app.knowledge.entity_matching import (
    CatalogueName, MAX_NAME_QUERY_LENGTH, NameMatchResult, match_catalogue_names, normalize_name,
)
from app.rules.engine import JURISDICTION, PROCEDURE

MissingContext = Literal["intent", "procedure", "procedure_location", "case_reference"]
_PLACE_TYPES = ("municipality", "province", "region")
_GOAL_BREAK = re.compile(r"[,;]|\n+|[.!?]+(?=\s|$)|\b(?:and also|and then|and|then|e anche|e poi|e|inoltre|poi)\b", re.I)
_REQUEST_CUE = re.compile(
    r"^(?:(?:i (?:also )?(?:want|need|would like) to|how (?:do|can) i|can i) )?"
    r"(?:(?:apply for|renew|request) (?:a|an|my|the) \w|"
    r"(?:(?:vorrei|voglio|devo|posso) )?(?:richiedere|rinnovare|ottenere) \w)"
)
_NEGATED_CUE = re.compile(r"^(?:(?:i )?don t|not|non|senza|invece di|anziche)\b")
_ALTERNATIVE_CUE = re.compile(r"^(?:or|o|oppure|in alternativa)\b")
_PREFERENCE_CUE = re.compile(
    r"(?:(?:please |let s |i d like to )?(?:start|begin) with |"
    r"(?:iniziamo|cominciamo|vorrei iniziare|vorrei cominciare) da(?:l|lla)? )(.+)"
)
_NUMBERED_GOAL = re.compile(r"(?:the |la |il )?(?:task|goal|option|pratica|obiettivo|opzione) ([1-6])")
_MOVE_AND_UPDATE_ADDRESS = re.compile(
    r"(?:(?:i (?:have )?moved and (?:need to|want to) (?:change|update) my "
    r"(?:registered |residential )?address (?:in|to))|"
    r"(?:(?:ho cambiato casa|mi sono trasferit[oa]) e (?:devo|voglio) (?:cambiare|aggiornare) "
    r"(?:il mio|l) indirizzo (?:a|in))) (?P<place>.+)"
)
_FILE_DECLARATION = re.compile(
    r"(?:(?:where|how) (?:do|can|should) i (?:file|send|submit|deliver) "
    r"(?:the|my) (?:declaration|application)|"
    r"(?:dove|come) (?:invio|presento|consegno|deposito) (?:la|l) (?:dichiarazione|domanda))"
)

# Narrow bilingual intent cues. Bare procedure names and reviewed variants
# come from the supplied catalogue.
_INTENT_CUES: tuple[tuple[AgentIntent, re.Pattern[str]], ...] = (
    ("plan_multiple_tasks", re.compile(
        r"\b(?:plan several tasks|multiple procedures|piu pratiche)\b"
    )),
    ("resume_case", re.compile(
        r"\b(?:(?:resume|continue) (?:(?:my|the|this) )?(?:case|application)|"
        r"pick up (?:my|our|where)|riprendere (?:la|il)|riprendi (?:la|il)|"
        r"continua(?:re)? (?:la|il) mi[ao] (?:pratica|caso))\b"
    )),
    ("explain_form_field", re.compile(
        r"\b(?:form field|field on (?:the|this) form|field in (?:the|this) form|"
        r"(?:mean|enter|put|write|fill in) .* (?:form|field)|"
        r"campo (?:del|nel) modulo|(?:significa|scrivo|inserisco|compilo) .* (?:modulo|campo))\b"
    )),
    ("explain_notice", re.compile(
        r"\b(?:what does .* (?:letter|notice|communication)|"
        r"(?:explain|understand) .* (?:letter|notice|communication)|"
        r"(?:significa|spiegami|capire) .* (?:lettera|avviso|comunicazione))\b"
    )),
    ("request_information", re.compile(
        r"\b(?:what (?:is|are|does)|which documents|how much|"
        r"(?:what|which) (?:exact )?(?:limit|maximum)|"
        r"cosa (?:e|sono|significa)|che cosa (?:e|sono|significa)|quali documenti|quanto costa|"
        r"quale (?:limite|massimo))\b"
    )),
    ("find_procedure", re.compile(
        r"\b(?:(?:how|where) (?:do|can|should) (?:i|we)|find (?:the|a) procedure|"
        r"(?:can|should|do) (?:i|we) (?:file|submit|deliver)|"
        r"(?:come|dove) (?:invio|presento|consegno|deposito)|"
        r"come (?:faccio|posso|comunico|richiedo)|dove posso|da dove inizio|"
        r"(?:posso|devo) (?:inviare|presentare|consegnare|depositare)|"
        r"a quale (?:comune|ufficio) (?:mi rivolgo|ci rivolgiamo))\b"
    )),
)


@dataclass(frozen=True)
class CatalogueMention:
    expression: str
    match: NameMatchResult
    start: int
    end: int


@dataclass(frozen=True)
class IntentExtraction:
    intent: AgentIntent | None
    mentions: tuple[CatalogueMention, ...]
    procedure_candidates: tuple[str, ...]
    missing_context: tuple[MissingContext, ...]
    goals: tuple[MessageGoal, ...] = ()
    preferred_goal: int | None = None
    uses_confirmed_case_scope: bool = False


def _catalogue_mentions(
    text: str, catalogue_names: Sequence[CatalogueName],
) -> tuple[CatalogueMention, ...]:
    # Index exact names and the compact spelling of reviewed acronyms. The
    # Phase 3 resolver still decides whether a mention needs confirmation.
    names: dict[tuple[str, ...], list[CatalogueName]] = {}
    acronyms: dict[str, list[CatalogueName]] = {}
    for record in catalogue_names:
        if not record.approved_for_search or not record.evidence_ref.strip():
            continue
        key = tuple(normalize_name(record.name).split())
        if key and len(record.name) <= MAX_NAME_QUERY_LENGTH:
            names.setdefault(key, []).append(record)
            if record.kind == "official_acronym":
                acronyms.setdefault("".join(key), []).append(record)

    tokens = list(re.finditer(r"[^\W_]+", text))
    words = [normalize_name(token.group()) for token in tokens]
    max_width = max(max(map(len, names), default=0), max(map(len, acronyms), default=0))
    mentions = []
    start = 0
    while start < len(tokens):
        for end in range(min(start + max_width, len(tokens)), start, -1):
            key = tuple(words[start:end])
            records = names.get(key, [])
            if len(key) == 1 or all(len(word) == 1 for word in key):
                if variants := acronyms.get("".join(key)):
                    records = list(dict.fromkeys([*records, *variants]))
            if not records:
                continue
            first, last = tokens[start].start(), tokens[end - 1].end()
            expression = text[first:last]
            if len(expression) > MAX_NAME_QUERY_LENGTH:
                continue
            # A longer authority name owns its span. For example, a city inside
            # an issuer's name is not a separate place expression.
            mentions.append(CatalogueMention(expression, match_catalogue_names(expression, records), first, last))
            start = end
            break
        else:
            start += 1
    return tuple(mentions)


def _procedures(mentions: Sequence[CatalogueMention]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(
        candidate.catalogue_id for mention in mentions
        for candidate in mention.match.candidates if candidate.entity_type == "procedure"
    ))


def _places(mentions: Sequence[CatalogueMention]) -> tuple[tuple[str, str], ...]:
    return tuple(dict.fromkeys(
        (candidate.entity_type, candidate.catalogue_id) for mention in mentions
        for candidate in mention.match.candidates if candidate.entity_type in _PLACE_TYPES
    ))


def _matches_confirmed_case(
    message: StoredMessage, place: str | None, mentions: Sequence[CatalogueMention],
    catalogue_names: Sequence[CatalogueName],
) -> bool:
    case = message.case_context
    if case is None or case.case_id != message.case_id or not case.matches_first_milan_route:
        return False
    places = _places(mentions)
    if places and places != (("municipality", JURISDICTION),):
        return False
    if place is None:
        return True
    if len(place) > MAX_NAME_QUERY_LENGTH:
        return False
    match = match_catalogue_names(place, list(catalogue_names), entity_type="municipality")
    return match.selected_type == "municipality" and match.selected_id == JURISDICTION


def _goal(mentions: list[CatalogueMention]) -> MessageGoal:
    procedures = _procedures(mentions)
    places = _places(mentions)
    missing = []
    if len(procedures) != 1 or not any(mention.match.selected_type == "procedure" for mention in mentions):
        missing.append("procedure")
    if len(places) != 1 or not any(mention.match.selected_type in _PLACE_TYPES for mention in mentions):
        missing.append("procedure_location")
    location_ids = list(dict.fromkeys(place_id for _, place_id in places))
    return MessageGoal(
        procedure_candidates=list(procedures) if len(procedures) <= MAX_PROCEDURE_CANDIDATES else [],
        location_candidates=location_ids if len(location_ids) <= MAX_PROCEDURE_CANDIDATES else [],
        missing_fields=missing,
    )


def _separate_goals(
    text: str, mentions: tuple[CatalogueMention, ...],
) -> tuple[list[MessageGoal], list[CatalogueMention]]:
    # Keep reviewed names intact even when they contain punctuation or a conjunction.
    breaks = [
        match.span() for match in _GOAL_BREAK.finditer(text)
        if not any(mention.start < match.end() and mention.end > match.start() for mention in mentions)
    ]
    groups: list[list[CatalogueMention]] = []
    routing_mentions = []
    start = 0
    for end, next_start in [*breaks, (len(text), len(text))]:
        clause = normalize_name(text[start:end])
        local = [mention for mention in mentions if start <= mention.start and mention.end <= end]
        start = next_start
        if _NEGATED_CUE.match(clause):
            continue
        routing_mentions.extend(local)
        if not _ALTERNATIVE_CUE.match(clause) and (_procedures(local) or _REQUEST_CUE.match(clause)):
            groups.append(local)
        elif groups:
            groups[-1].extend(local)

    merged: list[list[CatalogueMention]] = []
    for group in groups:
        previous = merged[-1] if merged else []
        procedures = _procedures(group)
        places, previous_places = _places(group), _places(previous)
        if (
            len(procedures) == 1 and procedures == _procedures(previous)
            and (not places or not previous_places or set(places) == set(previous_places))
        ):
            previous.extend(group)
        else:
            merged.append(group)
    return [_goal(group) for group in merged], routing_mentions


def _starting_preferences(text: str) -> tuple[str, list[str]]:
    # A standalone instruction can refer back to a task without becoming a new task.
    chunks = re.split(r"([;.!?\n]+)", text)
    preferences = []
    trailing = True
    for index in reversed(range(0, len(chunks), 2)):
        clause = normalize_name(chunks[index])
        if not clause:
            continue
        if cue := _PREFERENCE_CUE.fullmatch(clause):
            preferences.append(cue[1])
            if trailing and not _GOAL_BREAK.search(chunks[index]):
                chunks[index] = " " * len(chunks[index])
        else:
            trailing = False
    return "".join(chunks), preferences


def _preferred_goal(
    preferences: list[str], goals: list[MessageGoal], catalogue_names: Sequence[CatalogueName],
) -> int | None:
    if len(preferences) != 1:
        return None
    target = preferences[0]
    if number := _NUMBERED_GOAL.fullmatch(target):
        index = int(number[1])
        return index if index <= len(goals) else None
    if len(target) > MAX_NAME_QUERY_LENGTH:
        return None

    match = match_catalogue_names(target, list(catalogue_names), entity_type="procedure")
    if match.selected_id is None:
        return None
    options = [
        index for index, goal in enumerate(goals, 1) if match.selected_id in goal.procedure_candidates
    ]
    return options[0] if len(options) == 1 else None


def extract_intent(
    message: StoredMessage, *, catalogue_names: Sequence[CatalogueName],
) -> IntentExtraction:
    """Return hypotheses and context gaps, leaving scope and case data untouched."""
    text = unicodedata.normalize("NFC", message.text)
    goal_text, preferences = _starting_preferences(text)
    mentions = _catalogue_mentions(goal_text, catalogue_names)
    goals, routing_mentions = _separate_goals(goal_text, mentions)
    if 2 <= len(goals) <= MAX_MESSAGE_GOALS:
        missing = tuple(dict.fromkeys(field for goal in goals for field in goal.missing_fields))
        preferred = _preferred_goal(preferences, goals, catalogue_names)
        return IntentExtraction("plan_multiple_tasks", mentions, (), missing, tuple(goals), preferred)
    if len(goals) > MAX_MESSAGE_GOALS:
        return IntentExtraction("plan_multiple_tasks", mentions, (), ("procedure",))
    if preferences:
        # A starting cue without a separate list may be the only procedure request.
        mentions = _catalogue_mentions(text, catalogue_names)
        _, routing_mentions = _separate_goals(text, mentions)
    procedures = _procedures(routing_mentions)
    resolved_procedures = {
        mention.match.selected_id for mention in routing_mentions if mention.match.selected_type == "procedure"
    }
    normalized_text = normalize_name(text)
    intent = next((label for label, cue in _INTENT_CUES if cue.search(normalized_text)), None)
    saved_filing = SAVED_CASE_FILING.fullmatch(normalized_text)
    if intent in (None, "find_procedure", "request_information") and OTHER_CASE_CUE.search(normalized_text):
        intent = "resume_case"
    if intent in (None, "find_procedure") and saved_filing:
        intent = "resume_case"
    if intent in (None, "find_procedure", "request_information") and unreadable_notice_field(text):
        intent = "explain_notice"
    if intent is None and reports_conflicting_postal_filing(text):
        intent = "find_procedure"
    if not procedures and intent in (None, "find_procedure") and mentions_marriage_banns(text) and any(
        entry.catalogue_id == MARRIAGE_BANNS and entry.entity_type == "procedure"
        and entry.approved_for_search and entry.evidence_ref.strip()
        for entry in catalogue_names
    ):
        procedures = (MARRIAGE_BANNS,)
        resolved_procedures.add(MARRIAGE_BANNS)
    if intent is None and procedures:
        intent = "find_procedure"

    if not procedures:
        if intent == "resume_case" and saved_filing:
            place = saved_filing["en_place"] or saved_filing["it_place"]
            if _matches_confirmed_case(message, place, routing_mentions, catalogue_names):
                return IntentExtraction(intent, mentions, (PROCEDURE,), (), uses_confirmed_case_scope=True)
        if intent == "find_procedure":
            clauses = [clause for sentence in re.split(r"[.!?;\n]+", text) if (clause := normalize_name(sentence))]
            if len(clauses) == 2 and _FILE_DECLARATION.fullmatch(clauses[1]):
                move = _MOVE_AND_UPDATE_ADDRESS.fullmatch(clauses[0])
                if move and _matches_confirmed_case(message, move["place"], routing_mentions, catalogue_names):
                    return IntentExtraction(intent, mentions, (PROCEDURE,), (), uses_confirmed_case_scope=True)

    missing: list[MissingContext] = []
    if intent is None:
        missing.append("intent")
    if intent == "request_information" and (len(procedures) > 1 or len(resolved_procedures) < len(procedures)):
        missing.append("procedure")
    if intent in ("find_procedure", "plan_multiple_tasks"):
        if intent == "plan_multiple_tasks" or len(procedures) != 1 or len(resolved_procedures) != 1:
            missing.append("procedure")
        locations = _places(routing_mentions)
        resolved_location = len(locations) == 1 and any(
            mention.match.selected_type in _PLACE_TYPES for mention in routing_mentions
        )
        if not resolved_location:
            missing.append("procedure_location")
    if intent == "resume_case" and message.case_context is None:
        missing.append("case_reference")
    return IntentExtraction(intent, mentions, procedures, tuple(missing))


def identify_intent_step(
    message: StoredMessage, state: CheckpointState, *, catalogue_names: Sequence[CatalogueName],
) -> CheckpointState:
    """Project the result onto the worker checkpoint without keeping message spans."""
    if state.next_node != "identify_intent":
        raise ValueError("Intent extraction requires the identify_intent node")
    if message.corrects_destination:
        name = destination_correction_name(message.text, message.language)
        municipality = None
        if name and len(name) <= MAX_NAME_QUERY_LENGTH and normalize_name(name):
            match = match_catalogue_names(name, list(catalogue_names), entity_type="municipality")
            if match.status == "resolved":
                municipality = match.selected_id
        return CheckpointState(
            intent="find_procedure", procedure_candidates=[PROCEDURE],
            location_candidates=[municipality] if municipality else [],
            next_node="find_evidence" if municipality else "choose_next_step",
            routing_corrections=RoutingCorrections(destination=municipality) if municipality else None,
        )
    result = extract_intent(message, catalogue_names=catalogue_names)
    procedures = list(result.procedure_candidates)
    missing = list(result.missing_context)
    if len(procedures) > MAX_PROCEDURE_CANDIDATES:
        # The checkpoint cannot retain all plausible records. Ask for a more
        # specific procedure instead of dropping candidates according to order.
        procedures = []
        if "procedure" not in missing:
            missing.append("procedure")
    evidence_ready = result.uses_confirmed_case_scope or (
        not missing and len(procedures) == 1
        and procedures[0] not in (MARRIAGE_BANNS, PERMIT_RENEWAL)
        and result.intent in ("find_procedure", "request_information")
    )
    # A place mention in a free-form request is only a candidate: "a Milano"
    # does not establish whether Milan is the previous or destination municipality.
    # Keep unconfirmed place names out of the durable routing checkpoint.
    locations = [JURISDICTION] if result.uses_confirmed_case_scope and message.case_context is not None else []
    return CheckpointState(
        next_node="find_evidence" if evidence_ready else "choose_next_step",
        intent=result.intent, procedure_candidates=procedures, location_candidates=locations,
        missing_fields=missing, goals=list(result.goals), preferred_goal=result.preferred_goal,
        uses_confirmed_case_scope=result.uses_confirmed_case_scope,
    )
