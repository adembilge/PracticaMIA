"""Procedure-specific service areas, separate from physical office addresses.

This is a catalogue decision core. Its caller must obtain trusted passage IDs
from the approved-source registry and confirmed locations from the case.
"""

from dataclasses import dataclass
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


@dataclass(frozen=True)
class ServiceAreaResult:
    status: ResolutionStatus
    authority_ids: tuple[str, ...] = ()
    matched_assignments: tuple[ServiceArea, ...] = ()
    missing_location_roles: tuple[str, ...] = ()


def resolve_service_areas(
    procedure_id: str,
    case_locations: Mapping[str, CaseLocation],
    assignments: tuple[ServiceArea, ...] | list[ServiceArea],
    *,
    trusted_passage_ids: frozenset[str],
) -> ServiceAreaResult:
    """Resolve reviewed area claims using the relevant confirmed case location.

    A trusted passage is necessary but not sufficient: the assignment itself
    must have been approved for this exact procedure and location role. Office
    addresses are intentionally absent from the inputs.
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

    missing_roles: set[str] = set()
    matches: list[ServiceArea] = []
    for assignment in eligible:
        location = case_locations.get(assignment.case_location_role)
        if location is None or not location.confirmed:
            missing_roles.add(assignment.case_location_role)
            continue
        unit_id = location.id_for(assignment.unit_type)
        if unit_id is None:
            missing_roles.add(assignment.case_location_role)
            continue
        if unit_id in assignment.unit_ids:
            matches.append(assignment)

    matched = tuple(sorted(matches, key=lambda item: item.assignment_id))
    authorities = tuple(sorted({item.authority_id for item in matched}))
    if missing_roles:
        return ServiceAreaResult(
            status="needs_information",
            missing_location_roles=tuple(sorted(missing_roles)),
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
