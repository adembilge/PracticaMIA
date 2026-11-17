"""Synthetic identity matching; no actual IPA/Istat record is asserted."""

from dataclasses import replace
import unittest

from app.knowledge.entity_matching import (
    CatalogueName, match_catalogue_names, normalize_name,
)


def record(
    catalogue_id: str, name: str, *, kind="current_official",
    entity_type="municipality", locations=(), approved=True,
) -> CatalogueName:
    return CatalogueName(
        catalogue_id=catalogue_id, entity_type=entity_type,
        display_name=name, name=name, kind=kind,
        evidence_ref="synthetic-batch:1", location_ids=locations,
        approved_for_search=approved,
    )


class EntityMatchingTests(unittest.TestCase):
    def test_normalization_preserves_distinguishing_words_and_numbers(self):
        self.assertEqual(normalize_name("  Città  di  Milàno! "), "citta di milano")
        self.assertNotEqual(normalize_name("Roma 1"), normalize_name("Roma 2"))
        self.assertNotEqual(normalize_name("Provincia di Roma"), normalize_name("Roma"))

    def test_exact_official_name_resolves_one_id(self):
        result = match_catalogue_names("Milàno", [record("m-1", "Milano")])
        self.assertEqual(result.status, "resolved")
        self.assertEqual((result.selected_type, result.selected_id), ("municipality", "m-1"))
        self.assertEqual(result.candidates[0].matched_kind, "current_official")

    def test_former_name_keeps_stable_id_and_current_display_name(self):
        old = replace(record("m-1", "Oldtown", kind="former_official"),
                      display_name="Newtown")
        result = match_catalogue_names("Oldtown", [old])
        self.assertEqual(result.selected_id, "m-1")
        self.assertEqual(result.candidates[0].display_name, "Newtown")
        self.assertEqual(result.candidates[0].matched_kind, "former_official")

    def test_namesakes_return_all_ids_until_confirmed_location(self):
        names = [
            record("m-1", "Castello", locations=("p-1",)),
            record("m-2", "Castello", locations=("p-2",)),
        ]
        ambiguous = match_catalogue_names("Castello", names)
        self.assertEqual(ambiguous.status, "ambiguous")
        self.assertEqual({x.catalogue_id for x in ambiguous.candidates}, {"m-1", "m-2"})
        resolved = match_catalogue_names("Castello", names, confirmed_location_id="p-2")
        self.assertEqual(resolved.selected_id, "m-2")
        self.assertEqual(len(resolved.candidates), 2)

    def test_municipality_and_province_are_distinct(self):
        names = [
            record("m-1", "Valle"),
            record("p-1", "Valle", entity_type="province"),
        ]
        self.assertEqual(match_catalogue_names("Valle", names).status, "ambiguous")
        result = match_catalogue_names("Valle", names, entity_type="province")
        self.assertEqual((result.selected_type, result.selected_id), ("province", "p-1"))

    def test_dotted_acronym_matches_without_changing_stored_name(self):
        result = match_catalogue_names(
            "ASL", [record("a-1", "A.S.L.", kind="official_acronym",
                           entity_type="authority")],
        )
        self.assertEqual(result.status, "needs_confirmation")
        self.assertEqual(result.candidates[0].matched_name, "A.S.L.")

    def test_spelling_suggestion_needs_confirmation(self):
        result = match_catalogue_names("Miano", [record("m-1", "Milano")])
        self.assertEqual(result.status, "needs_confirmation")
        self.assertIsNone(result.selected_id)
        self.assertEqual(result.candidates[0].match_type, "spelling_suggestion")
        transposed = match_catalogue_names("Milnao", [record("m-1", "Milano")])
        self.assertEqual(transposed.status, "needs_confirmation")

    def test_multiple_changes_do_not_create_a_spelling_hit(self):
        self.assertEqual(
            match_catalogue_names("Comune di Bari", [record("m-1", "Comune di Como")]).status,
            "unresolved",
        )

    def test_unreviewed_alias_and_conflicting_location_do_not_resolve(self):
        alias = record("m-1", "The City", kind="reviewed_alias", approved=False)
        self.assertEqual(match_catalogue_names("The City", [alias]).status, "unresolved")
        no_evidence = replace(record("m-1", "Milano"), evidence_ref="")
        self.assertEqual(match_catalogue_names("Milano", [no_evidence]).status, "unresolved")
        official = record("m-1", "Milano", locations=("p-1",))
        result = match_catalogue_names("Milano", [official], confirmed_location_id="p-2")
        self.assertEqual(result.status, "unresolved")
        self.assertIsNone(result.selected_id)

    def test_invalid_queries_are_rejected(self):
        with self.assertRaises(ValueError):
            match_catalogue_names("!!!", [])
        with self.assertRaises(ValueError):
            match_catalogue_names("a" * 181, [])


if __name__ == "__main__":
    unittest.main()
