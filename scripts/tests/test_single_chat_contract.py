"""Negative controls: future plans cannot silently restore a visible case UI."""
import unittest

from pathlib import Path
from tempfile import TemporaryDirectory
from scripts.validate_single_chat_contract import (FILES, PHASE_FILES, REQUIRED,
    runtime_legacy_inventory, unregistered_customer_pages, validate_texts, validate_visible_chat_fixture)


def sample() -> dict[str, str]:
    result = {name: "D-010 binding product contract" for name in PHASE_FILES}
    result.update({name: " ".join(tokens) for name, tokens in REQUIRED.items()})
    return result


class SingleChatContractTests(unittest.TestCase):
    def test_complete_active_plan_passes(self):
        self.assertEqual(validate_texts(sample()), [])

    def test_missing_governing_decision_is_rejected(self):
        data = sample()
        data["docs/DECISIONS.md"] = "No decision text"
        self.assertTrue(any("DECISIONS" in e for e in validate_texts(data)))

    def test_phase_without_binding_requirement_is_rejected(self):
        data = sample()
        data[PHASE_FILES[3]] = "Separate document app"
        self.assertTrue(any("phase-07" in e for e in validate_texts(data)))

    def test_case_switcher_reintroduction_is_rejected(self):
        data = sample()
        data[PHASE_FILES[1]] += " A compact conversation/case switcher may live"
        self.assertTrue(any("case switcher" in e for e in validate_texts(data)))

    def test_chat_fixture_rejects_visible_case_picker(self):
        self.assertTrue(validate_visible_chat_fixture('Cases in this conversation'))
        self.assertTrue(validate_visible_chat_fixture('Open saved case task 12345678'))
        self.assertEqual(validate_visible_chat_fixture('One composer and conversation history'), [])

    def test_runtime_audit_flags_old_customer_pages_without_deleting_data(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / 'frontend/src/app/cases/new/page.tsx'
            old.parent.mkdir(parents=True)
            old.write_text('export default function Old() {}', encoding='utf-8')
            landing = root / 'frontend/src/app/page.tsx'
            landing.parent.mkdir(parents=True, exist_ok=True)
            landing.write_text('import {HomeView} from "legacy";', encoding='utf-8')
            self.assertEqual(len(runtime_legacy_inventory(root)), 2)
            old.unlink()
            landing.write_text('export default function Chat() {}', encoding='utf-8')
            self.assertEqual(runtime_legacy_inventory(root), [])


    def test_new_standalone_case_route_is_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / 'frontend/src/app/cases/new/page.tsx'
            legacy.parent.mkdir(parents=True)
            legacy.write_text('legacy', encoding='utf-8')
            self.assertEqual(unregistered_customer_pages(root), [])
            unexpected = root / 'frontend/src/app/cases/surprise/page.tsx'
            unexpected.parent.mkdir(parents=True)
            unexpected.write_text('not allowed', encoding='utf-8')
            self.assertEqual(unregistered_customer_pages(root), [
                'frontend/src/app/cases/surprise/page.tsx',
            ])

    def test_missing_gap_audit_is_rejected(self):
        data = sample()
        del data["docs/SINGLE_CHAT_GAP_AUDIT.md"]
        self.assertTrue(any("GAP_AUDIT" in e for e in validate_texts(data)))


if __name__ == "__main__":
    unittest.main()
