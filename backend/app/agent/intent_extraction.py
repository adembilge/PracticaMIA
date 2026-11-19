"""Read-only intent extraction against a server-supplied reviewed catalogue."""

from collections.abc import Sequence
from dataclasses import dataclass
import re
from typing import Literal
import unicodedata

from app.agent.checkpoints import CheckpointState
from app.agent.contract import MAX_MESSAGE_GOALS, MAX_PROCEDURE_CANDIDATES, AgentIntent, MessageGoal
from app.agent.run_requests import StoredMessage
from app.knowledge.entity_matching import (
    CatalogueName, MAX_NAME_QUERY_LENGTH, NameMatchResult, match_catalogue_names, normalize_name,
)

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
        r"cosa (?:e|sono|significa)|che cosa (?:e|sono|significa)|quali documenti|quanto costa)\b"
    )),
    ("find_procedure", re.compile(
        r"\b(?:how (?:do|can) i|where (?:do|can) i|find (?:the|a) procedure|"
        r"come (?:faccio|posso|comunico|presento|richiedo)|dove (?:posso|presento)|da dove inizio)\b"
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


def extract_intent(
    message: StoredMessage, *, catalogue_names: Sequence[CatalogueName],
) -> IntentExtraction:
    """Return hypotheses and context gaps, leaving scope and case data untouched."""
    text = unicodedata.normalize("NFC", message.text)
    mentions = _catalogue_mentions(text, catalogue_names)
    goals, routing_mentions = _separate_goals(text, mentions)
    if 2 <= len(goals) <= MAX_MESSAGE_GOALS:
        missing = tuple(dict.fromkeys(field for goal in goals for field in goal.missing_fields))
        return IntentExtraction("plan_multiple_tasks", mentions, (), missing, tuple(goals))
    if len(goals) > MAX_MESSAGE_GOALS:
        return IntentExtraction("plan_multiple_tasks", mentions, (), ("procedure",))
    procedures = _procedures(routing_mentions)
    resolved_procedures = {
        mention.match.selected_id for mention in routing_mentions if mention.match.selected_type == "procedure"
    }
    normalized_text = normalize_name(text)
    intent = next((label for label, cue in _INTENT_CUES if cue.search(normalized_text)), None)
    if intent is None and procedures:
        intent = "find_procedure"

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
    result = extract_intent(message, catalogue_names=catalogue_names)
    procedures = list(result.procedure_candidates)
    missing = list(result.missing_context)
    if len(procedures) > MAX_PROCEDURE_CANDIDATES:
        # The checkpoint cannot retain all plausible records. Ask for a more
        # specific procedure instead of dropping candidates according to order.
        procedures = []
        if "procedure" not in missing:
            missing.append("procedure")
    evidence_ready = (
        not missing and len(procedures) == 1
        and result.intent in ("find_procedure", "request_information")
    )
    return CheckpointState(
        next_node="find_evidence" if evidence_ready else "choose_next_step",
        intent=result.intent, procedure_candidates=procedures, missing_fields=missing, goals=list(result.goals),
    )
