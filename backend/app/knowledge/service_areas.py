"""Procedure-specific service areas, separate from physical office addresses.

This is a catalogue decision core. Its caller must obtain trusted passage IDs
from the approved-source registry and confirmed locations from the case.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal, Mapping


UnitType = Literal["municipality", "province", "region", "country"]
ResolutionStatus = Literal[
    "supported", "ambiguous", "needs_information", "unresolved",
]


@dataclass(frozen=True)
class OfficeAddress:
    """Where an office is located; never a grant of service competence."""

    office_id: str
    authority_id: str
    address_line: str
    municipality_id: str
    evidence_ref: str


@dataclass(frozen=True)
class CaseLocation:
    """A case location confirmed for a named procedural purpose."""

    municipality_id: str | None = None
    province_id: str | None = None
    region_id: str | None = None
    country_id: str | None = None
    confirmed: bool = False

    def id_for(self, unit_type: UnitType) -> str | None:
        return getattr(self, f"{unit_type}_id")


@dataclass(frozen=True)
class EffectivePeriod:
    """Reviewed calendar bounds evaluated against a named case date."""

    case_date_field: str
    effective_from: date | None = None
    effective_until: date | None = None

    def __post_init__(self) -> None:
        if not self.case_date_field.strip() or (
            self.effective_from is None and self.effective_until is None
        ):
            raise ValueError("An effective period needs a case date field and at least one bound")
        if self.effective_from and self.effective_until and self.effective_from > self.effective_until:
            raise ValueError("The first effective day must be at or before the last effective day")

    def includes(self, case_date: date) -> bool:
        return (
            (self.effective_from is None or self.effective_from <= case_date)
            and (self.effective_until is None or case_date <= self.effective_until)
        )


@dataclass(frozen=True)
class ServiceArea:
    """A reviewed claim that one authority serves a procedure and area."""

    assignment_id: str
    authority_id: str
    procedure_id: str
    case_location_role: str
    unit_type: UnitType
    unit_ids: tuple[str, ...]
    evidence_ref: str
    approved_for_routing: bool = False
    active: bool = True
    effective_period: EffectivePeriod | None = None
    required_circumstances: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class ServiceAreaResult:
    status: ResolutionStatus
    authority_ids: tuple[str, ...] = ()
    matched_assignments: tuple[ServiceArea, ...] = ()
    missing_location_roles: tuple[str, ...] = ()
    missing_date_fields: tuple[str, ...] = ()
    missing_circumstance_fields: tuple[str, ...] = ()


def resolve_service_areas(
    procedure_id: str,
    case_locations: Mapping[str, CaseLocation],
    assignments: tuple[ServiceArea, ...] | list[ServiceArea],
    *,
    trusted_passage_ids: frozenset[str],
    confirmed_dates: Mapping[str, date] | None = None,
    confirmed_circumstances: Mapping[str, str] | None = None,
) -> ServiceAreaResult:
    """Resolve reviewed area claims using the relevant confirmed case location.

    A trusted passage and a reviewed assignment are required for the exact
    procedure, location role and case conditions.
    """
    eligible = [
        assignment for assignment in assignments
        if assignment.procedure_id == procedure_id
        and assignment.approved_for_routing
        and assignment.active
        and assignment.evidence_ref in trusted_passage_ids
        and assignment.unit_ids
        and all(assignment.unit_ids)
    ]
    if not eligible:
        return ServiceAreaResult(status="unresolved")

    dates = confirmed_dates or {}
    circumstances = confirmed_circumstances or {}
    missing_roles: set[str] = set()
    missing_dates: set[str] = set()
    missing_circumstances: set[str] = set()
    matches: list[ServiceArea] = []
    for assignment in eligible:
        location = case_locations.get(assignment.case_location_role)
        unit_id = location.id_for(assignment.unit_type) if location and location.confirmed else None
        if unit_id is not None and unit_id not in assignment.unit_ids:
            continue

        period = assignment.effective_period
        case_date = dates.get(period.case_date_field) if period else None
        if period and case_date is not None and not period.includes(case_date):
            continue

        unknown_fields = {
            field for field, _ in assignment.required_circumstances
            if circumstances.get(field) in (None, "", "unknown")
        }
        if any(
            field not in unknown_fields and circumstances[field] != expected
            for field, expected in assignment.required_circumstances
        ):
            continue

        if unit_id is None:
            missing_roles.add(assignment.case_location_role)
        if period and case_date is None:
            missing_dates.add(period.case_date_field)
        missing_circumstances.update(unknown_fields)
        if unit_id is not None and (period is None or case_date is not None) and not unknown_fields:
            matches.append(assignment)

    matched = tuple(sorted(matches, key=lambda item: item.assignment_id))
    authorities = tuple(sorted({item.authority_id for item in matched}))
    if missing_roles or missing_dates or missing_circumstances:
        return ServiceAreaResult(
            status="needs_information",
            missing_location_roles=tuple(sorted(missing_roles)),
            missing_date_fields=tuple(sorted(missing_dates)),
            missing_circumstance_fields=tuple(sorted(missing_circumstances)),
        )
    if not matched:
        return ServiceAreaResult(status="unresolved")
    if len(authorities) > 1:
        return ServiceAreaResult(
            status="ambiguous", authority_ids=authorities,
            matched_assignments=matched,
        )
    return ServiceAreaResult(
        status="supported", authority_ids=authorities,
        matched_assignments=matched,
    )
