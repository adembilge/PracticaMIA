"""Choose questions from the requirements of still-possible assignments."""

from collections import defaultdict
from collections.abc import Hashable, Mapping, Sequence
from datetime import date

from app.agent.clarification_context import ClarificationHint
from app.knowledge.service_areas import EffectivePeriod, PossibleServiceArea, ServiceAreaField, ServiceAreaResult


def prioritize_routing_fields(
    pending: Sequence[ServiceAreaResult], available_fields: Sequence[ServiceAreaField],
    hints: Mapping[str, ClarificationHint],
) -> tuple[ServiceAreaField, ...]:
    """Prefer a distinguishing field, then one that can settle an assignment."""
    choices = []
    for result in pending:
        assignments = result.possible_assignments
        gaps = [set(item.missing_fields) for item in assignments]
        relevant = set().union(*gaps)
        fields = tuple(field for field in available_fields if field in relevant)
        if not fields:
            continue

        priorities = {
            field: (
                _distinguishes_authorities(field, assignments),
                {field} in gaps,
                hints.get(field[1]) == "conflict",
                field[1] in hints,
            )
            for field in fields
        }
        best = max(fields, key=priorities.__getitem__)
        group_needed = (
            len(fields) > 1
            and len({item.assignment.authority_id for item in assignments}) == 1
            and len(fields) == len(relevant)
            and all(gap == relevant for gap in gaps)
            and not any(field[1] in hints for field in fields)
        )
        selected = fields if group_needed else (best,)
        choices.append((priorities[best] + (len(selected) == 1,), selected))

    return max(choices, key=lambda choice: choice[0])[1] if choices else ()


def _distinguishes_authorities(field: ServiceAreaField, assignments: Sequence[PossibleServiceArea]) -> bool:
    alternatives: dict[str, list[PossibleServiceArea]] = defaultdict(list)
    for item in assignments:
        alternatives[item.assignment.authority_id].append(item)
    signatures = {_signature(field, routes) for routes in alternatives.values()}
    return len(signatures) > 1


def _signature(field: ServiceAreaField, routes: Sequence[PossibleServiceArea]) -> Hashable | None:
    # A route that does not need this field keeps its authority possible.
    if any(field not in item.missing_fields for item in routes):
        return None
    kind, name = field
    assignments = [item.assignment for item in routes]
    if kind == "location":
        return frozenset((item.unit_type, unit_id) for item in assignments for unit_id in item.unit_ids)
    if kind == "date":
        return _date_coverage([item.effective_period for item in assignments if item.effective_period])
    return frozenset(value for item in assignments for key, value in item.required_circumstances if key == name)


def _date_coverage(periods: Sequence[EffectivePeriod]) -> tuple[tuple[int, int], ...] | None:
    """Compare the union of inclusive date ranges for each authority."""
    first, last = date.min.toordinal(), date.max.toordinal()
    intervals = sorted(
        ((period.effective_from or date.min).toordinal(), (period.effective_until or date.max).toordinal())
        for period in periods
    )
    merged: list[tuple[int, int]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1] + 1:
            previous_start, previous_end = merged[-1]
            merged[-1] = (previous_start, max(previous_end, end))
        else:
            merged.append((start, end))
    return None if merged == [(first, last)] else tuple(merged)
