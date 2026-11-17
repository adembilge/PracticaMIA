"""Fictional service-area fixtures; no real authority routing is asserted."""

import unittest

from app.knowledge.service_areas import (
    CaseLocation, OfficeAddress, ServiceArea, resolve_service_areas,
)


TRUSTED = frozenset({"synthetic-passage-1", "synthetic-passage-2"})


def area(
    assignment_id="s-1", authority_id="authority-a", procedure_id="procedure-a",
    role="destination", unit_type="municipality", unit_ids=("municipality-b",),
    evidence_ref="synthetic-passage-1", approved=True, active=True,
) -> ServiceArea:
    return ServiceArea(
        assignment_id=assignment_id, authority_id=authority_id,
        procedure_id=procedure_id, case_location_role=role,
        unit_type=unit_type, unit_ids=unit_ids,
        evidence_ref=evidence_ref, approved_for_routing=approved, active=active,
    )


class ServiceAreaTests(unittest.TestCase):
    def test_office_address_does_not_define_coverage(self):
        office = OfficeAddress(
            office_id="office-a", authority_id="authority-a",
            address_line="1 Fictional Street", municipality_id="municipality-a",
            evidence_ref="synthetic-address",
        )
        assignment = area(unit_ids=("municipality-b",))
        served = resolve_service_areas(
            "procedure-a",
            {"destination": CaseLocation(municipality_id="municipality-b", confirmed=True)},
            [assignment], trusted_passage_ids=TRUSTED,
        )
        self.assertEqual(served.status, "supported")
        self.assertEqual(served.authority_ids, (office.authority_id,))
        unserved = resolve_service_areas(
            "procedure-a",
            {"destination": CaseLocation(municipality_id=office.municipality_id,
                                         confirmed=True)},
            [assignment], trusted_passage_ids=TRUSTED,
        )
        self.assertEqual(unserved.status, "unresolved")

    def test_same_authority_has_different_areas_by_procedure(self):
        assignments = [
            area(),
            area(assignment_id="s-2", procedure_id="procedure-b",
                 unit_ids=("municipality-c",)),
        ]
        location = {"destination": CaseLocation(municipality_id="municipality-b",
                                                 confirmed=True)}
        self.assertEqual(resolve_service_areas(
            "procedure-a", location, assignments, trusted_passage_ids=TRUSTED,
        ).status, "supported")
        self.assertEqual(resolve_service_areas(
            "procedure-b", location, assignments, trusted_passage_ids=TRUSTED,
        ).status, "unresolved")

    def test_one_area_can_cover_multiple_municipalities(self):
        assignment = area(unit_ids=("municipality-b", "municipality-c"))
        result = resolve_service_areas(
            "procedure-a",
            {"destination": CaseLocation(municipality_id="municipality-c", confirmed=True)},
            [assignment], trusted_passage_ids=TRUSTED,
        )
        self.assertEqual(result.status, "supported")

    def test_province_area_uses_confirmed_province_not_office_city(self):
        assignment = area(unit_type="province", unit_ids=("province-p",))
        result = resolve_service_areas(
            "procedure-a",
            {"destination": CaseLocation(municipality_id="municipality-b",
                                         province_id="province-p", confirmed=True)},
            [assignment], trusted_passage_ids=TRUSTED,
        )
        self.assertEqual(result.status, "supported")

    def test_unconfirmed_or_missing_location_requires_information(self):
        assignment = area()
        for locations in ({}, {"destination": CaseLocation(municipality_id="municipality-b")},
                          {"destination": CaseLocation(province_id="province-p", confirmed=True)}):
            with self.subTest(locations=locations):
                result = resolve_service_areas(
                    "procedure-a", locations, [assignment], trusted_passage_ids=TRUSTED,
                )
                self.assertEqual(result.status, "needs_information")
                self.assertEqual(result.missing_location_roles, ("destination",))

    def test_location_role_changes_routing(self):
        assignment = area(role="activity_location")
        result = resolve_service_areas(
            "procedure-a",
            {"residence": CaseLocation(municipality_id="municipality-b", confirmed=True)},
            [assignment], trusted_passage_ids=TRUSTED,
        )
        self.assertEqual(result.status, "needs_information")
        self.assertEqual(result.missing_location_roles, ("activity_location",))

    def test_two_authorities_with_same_area_remain_ambiguous(self):
        assignments = [area(), area(assignment_id="s-2", authority_id="authority-b",
                                    evidence_ref="synthetic-passage-2")]
        result = resolve_service_areas(
            "procedure-a",
            {"destination": CaseLocation(municipality_id="municipality-b", confirmed=True)},
            assignments, trusted_passage_ids=TRUSTED,
        )
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(result.authority_ids, ("authority-a", "authority-b"))

    def test_unapproved_or_untrusted_claim_never_routes(self):
        location = {"destination": CaseLocation(municipality_id="municipality-b",
                                                confirmed=True)}
        for assignment, trusted in (
            (area(approved=False), TRUSTED),
            (area(active=False), TRUSTED),
            (area(evidence_ref="synthetic-revoked"), TRUSTED),
            (area(), frozenset()),
        ):
            with self.subTest(assignment=assignment, trusted=trusted):
                self.assertEqual(resolve_service_areas(
                    "procedure-a", location, [assignment], trusted_passage_ids=trusted,
                ).status, "unresolved")

    def test_missing_other_role_blocks_partial_match(self):
        assignments = [area(), area(assignment_id="s-2", authority_id="authority-b",
                                    role="activity_location", unit_ids=("municipality-c",))]
        result = resolve_service_areas(
            "procedure-a",
            {"destination": CaseLocation(municipality_id="municipality-b", confirmed=True)},
            assignments, trusted_passage_ids=TRUSTED,
        )
        self.assertEqual(result.status, "needs_information")
        self.assertEqual(result.authority_ids, ())
        self.assertEqual(result.missing_location_roles, ("activity_location",))


if __name__ == "__main__":
    unittest.main()
