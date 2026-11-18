"""Synthetic case context and service assignments for Phase 4 task 34.4."""

from dataclasses import replace
from datetime import date

import pytest

from app.agent.catalogue_applicability import resolve_candidate_applicability
from app.agent.checkpoints import CheckpointState
from app.knowledge.service_areas import CaseLocation, EffectivePeriod
from test_service_areas import TRUSTED, area


SWITCH = date(2026, 4, 1)
LAST_OLD_DAY = date(2026, 3, 31)
DESTINATION = CaseLocation(municipality_id="municipality-b", confirmed=True)
STATE = CheckpointState(next_node="find_evidence", procedure_candidates=["procedure-a", "procedure-b"])
ASSIGNMENTS = (
    replace(
        area(assignment_id="old", authority_id="authority-old"),
        effective_period=EffectivePeriod("filing_date", effective_until=LAST_OLD_DAY),
    ),
    replace(
        area(assignment_id="rental", authority_id="authority-rental"),
        effective_period=EffectivePeriod("filing_date", effective_from=SWITCH),
        required_circumstances=(("housing_basis", "rental"),),
    ),
    replace(
        area(assignment_id="ownership", authority_id="authority-owner"),
        effective_period=EffectivePeriod("filing_date", effective_from=SWITCH),
        required_circumstances=(("housing_basis", "owner"),),
    ),
    area(
        assignment_id="other-procedure", procedure_id="procedure-b", role="activity_location",
        unit_ids=("municipality-c",), authority_id="authority-activity",
    ),
)


@pytest.mark.parametrize(("filing_date", "housing_basis", "authority"), [
    (LAST_OLD_DAY, None, "authority-old"),
    (SWITCH, "rental", "authority-rental"),
    (SWITCH, "owner", "authority-owner"),
])
def test_checkpoint_candidates_are_evaluated_by_date_location_role_and_case_circumstance(
    filing_date, housing_basis, authority,
):
    results = resolve_candidate_applicability(
        STATE, case_locations={
            "destination": DESTINATION,
            "activity_location": CaseLocation(municipality_id="municipality-c", confirmed=True),
        },
        confirmed_dates={"filing_date": filing_date, "move_in_date": LAST_OLD_DAY},
        confirmed_circumstances={"housing_basis": housing_basis} if housing_basis else {},
        assignments=ASSIGNMENTS, trusted_passage_ids=TRUSTED,
    )
    assert results["procedure-a"].status == "supported"
    assert results["procedure-a"].authority_ids == (authority,)
    assert results["procedure-b"].authority_ids == ("authority-activity",)


def test_named_date_and_confirmed_destination_remain_missing_despite_other_dates_and_locations():
    results = resolve_candidate_applicability(
        STATE,
        case_locations={"current_position": DESTINATION, "residence": DESTINATION},
        confirmed_dates={"move_in_date": SWITCH},
        confirmed_circumstances={"housing_basis": "unknown"},
        assignments=ASSIGNMENTS, trusted_passage_ids=TRUSTED,
    )
    candidate = results["procedure-a"]
    assert candidate.status == "needs_information"
    assert candidate.authority_ids == ()
    assert candidate.missing_location_roles == ("destination",)
    assert candidate.missing_date_fields == ("filing_date",)
    assert candidate.missing_circumstance_fields == ("housing_basis",)
    assert results["procedure-b"].missing_location_roles == ("activity_location",)


def test_known_mismatch_excludes_assignment_without_requesting_irrelevant_context():
    retired = ASSIGNMENTS[0]
    rejected_housing = replace(ASSIGNMENTS[1], case_location_role="activity_location")
    revoked = replace(
        ASSIGNMENTS[2], case_location_role="activity_location", evidence_ref="withdrawn-passage",
    )
    results = resolve_candidate_applicability(
        STATE, case_locations={"destination": DESTINATION},
        confirmed_dates={"filing_date": SWITCH},
        confirmed_circumstances={"housing_basis": "owner"},
        assignments=(retired, rejected_housing, revoked, ASSIGNMENTS[2]),
        trusted_passage_ids=TRUSTED,
    )
    assert results["procedure-a"].status == "supported"
    assert results["procedure-a"].authority_ids == ("authority-owner",)
    assert results["procedure-a"].missing_location_roles == ()
    assert results["procedure-b"].status == "unresolved"


def test_distinct_territorial_units_change_the_set_of_matching_candidates():
    results = resolve_candidate_applicability(
        STATE,
        case_locations={"destination": CaseLocation(municipality_id="municipality-c", confirmed=True)},
        confirmed_dates={}, confirmed_circumstances={},
        assignments=ASSIGNMENTS, trusted_passage_ids=TRUSTED,
    )
    assert results["procedure-a"].status == "unresolved"
    assert results["procedure-a"].missing_date_fields == ()
    assert results["procedure-a"].missing_circumstance_fields == ()
    assert results["procedure-b"].status == "needs_information"


def test_effective_period_requires_a_named_date_role_and_coherent_bounds():
    with pytest.raises(ValueError, match="at least one bound"):
        EffectivePeriod("filing_date")
    with pytest.raises(ValueError, match="case date field"):
        EffectivePeriod("", effective_from=SWITCH)
    with pytest.raises(ValueError, match="first effective day"):
        EffectivePeriod("filing_date", effective_from=SWITCH, effective_until=LAST_OLD_DAY)
