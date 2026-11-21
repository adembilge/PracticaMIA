"""Negative controls: future plans cannot silently restore a visible case UI."""
import unittest

from scripts.validate_single_chat_contract import FILES, PHASE_FILES, REQUIRED, validate_texts


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

    def test_missing_gap_audit_is_rejected(self):
        data = sample()
        del data["docs/SINGLE_CHAT_GAP_AUDIT.md"]
        self.assertTrue(any("GAP_AUDIT" in e for e in validate_texts(data)))


if __name__ == "__main__":
    unittest.main()
