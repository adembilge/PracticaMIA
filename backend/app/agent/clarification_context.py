"""Use case facts and bounded message evidence before choosing a question."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
import re
from typing import Literal

from app.agent.document_context import DocumentFieldStatus
from app.agent.run_requests import StoredMessage
from app.knowledge.service_areas import CaseLocation
from app.private_documents.intelligence import HOUSING_RE, HOUSING_VALUES, MOVE_DATE_RE, normalize_labeled_move_date
from app.rules.engine import JURISDICTION, PROCEDURE

_DATE_VALUE = r"(?P<value>\d{4}-\d{2}-\d{2}|\d{2}[./-]\d{2}[./-]\d{4})\s*[.!]?\s*$"
_MESSAGE_DATES = {
    "move_in_date": re.compile(r"^\s*(?:i moved in on|mi sono trasferit[oa] il)\s+" + _DATE_VALUE, re.I | re.M),
    "filing_date": re.compile(r"^\s*(?:filing date|data di presentazione)\s*:\s*" + _DATE_VALUE, re.I | re.M),
}
_MILAN_DESTINATION = re.compile(
    r"^\s*(?:i(?: am|['’]m) moving to\s+|mi trasferisco a\s+|"
    r"(?:destination municipality|comune di destinazione)\s*:\s*)"
    r"(?:milan|milano)\s*[.!]?\s*$", re.I | re.M,
)

ClarificationHint = Literal["message"] | DocumentFieldStatus


@dataclass(frozen=True)
class ClarificationContext:
    case_locations: Mapping[str, CaseLocation]
    confirmed_dates: Mapping[str, date]
    confirmed_circumstances: Mapping[str, str]
    hints: dict[str, ClarificationHint]


def prepare_clarification_context(
    message: StoredMessage, *, procedure_ids: list[str],
    case_locations: Mapping[str, CaseLocation], confirmed_dates: Mapping[str, date],
    confirmed_circumstances: Mapping[str, str],
) -> ClarificationContext:
    """Reuse confirmed intake for the signed procedure and keep other inputs advisory."""
    if procedure_ids != [PROCEDURE]:
        return ClarificationContext(case_locations, confirmed_dates, confirmed_circumstances, {})

    case = message.case_context
    same_case = case is not None and case.case_id == message.case_id
    facts = case.user_confirmed_facts if same_case else None
    locations = dict(case_locations)
    dates = dict(confirmed_dates)
    circumstances = dict(confirmed_circumstances)
    hints: dict[str, ClarificationHint] = dict(case.document_fields) if same_case else {}
    if facts is not None:
        destination = locations.get("destination")
        if facts.destination_municipality == "milano" and not (destination and destination.confirmed):
            locations["destination"] = CaseLocation(municipality_id=JURISDICTION, confirmed=True)
        if facts.move_in_date is not None:
            dates["move_in_date"] = date.fromisoformat(facts.move_in_date)
        if facts.housing_basis not in (None, "unknown"):
            circumstances["housing_basis"] = facts.housing_basis

    date_tokens = {
        field: [match.group("value") for match in pattern.finditer(message.text)]
        for field, pattern in _MESSAGE_DATES.items()
    }
    date_tokens["move_in_date"].extend(match.group("value") for match in MOVE_DATE_RE.finditer(message.text))
    for field, tokens in date_tokens.items():
        values = {value for token in tokens if (value := normalize_labeled_move_date(token)) is not None}
        existing = dates[field].isoformat() if field in dates else None
        _add_message_hint(hints, field, values, existing)
        if hints.get(field) == "conflict":
            dates.pop(field, None)

    housing = {
        value for match in HOUSING_RE.finditer(message.text)
        if (value := HOUSING_VALUES.get(" ".join(match.group("value").casefold().split()).rstrip("."))) is not None
    }
    _add_message_hint(hints, "housing_basis", housing, circumstances.get("housing_basis"))
    if hints.get("housing_basis") == "conflict":
        circumstances.pop("housing_basis", None)

    if _MILAN_DESTINATION.search(message.text):
        destination = locations.get("destination")
        if facts is not None and facts.destination_municipality == "other":
            hints["destination"] = "conflict"
            locations.pop("destination", None)
        elif destination is None or not destination.confirmed:
            hints["destination"] = "message"
    return ClarificationContext(locations, dates, circumstances, hints)


def _add_message_hint(
    hints: dict[str, ClarificationHint], field: str, values: set[str], current: str | None,
) -> None:
    if len(values) > 1 or (values and current not in (None, "", "unknown") and current not in values):
        hints[field] = "conflict"
    elif values and current in (None, "", "unknown"):
        hints.setdefault(field, "message")
