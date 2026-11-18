"""Evaluate saved procedure candidates against reviewed assignment conditions."""

from collections.abc import Mapping
from datetime import date

from app.agent.checkpoints import CheckpointState
from app.knowledge.service_areas import CaseLocation, ServiceArea, ServiceAreaResult, resolve_service_areas


def resolve_candidate_applicability(
    state: CheckpointState, *,
    case_locations: Mapping[str, CaseLocation],
    confirmed_dates: Mapping[str, date],
    confirmed_circumstances: Mapping[str, str],
    assignments: tuple[ServiceArea, ...] | list[ServiceArea],
    trusted_passage_ids: frozenset[str],
) -> dict[str, ServiceAreaResult]:
    """Keep applicability separate from message extraction and case mutation."""
    return {
        procedure_id: resolve_service_areas(
            procedure_id, case_locations, assignments,
            trusted_passage_ids=trusted_passage_ids, confirmed_dates=confirmed_dates,
            confirmed_circumstances=confirmed_circumstances,
        )
        for procedure_id in state.procedure_candidates
    }
