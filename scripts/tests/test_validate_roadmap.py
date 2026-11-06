"""Fast, offline negative-control tests for roadmap acceptance validation."""
from copy import deepcopy
from pathlib import Path
import unittest

import yaml

from scripts.validate_roadmap import validate

ROOT = Path(__file__).resolve().parents[2]


class RoadmapGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "PracticaMIA_Complete_Project_Specification.md").read_text()
        cls.base = yaml.safe_load((ROOT / "docs" / "TASKS.yaml").read_text())

    def test_genuine_tracker_is_valid(self):
        self.assertEqual(validate(self.base, self.source), [])

    def test_dropped_or_duplicate_parent_fails(self):
        mutated = deepcopy(self.base)
        mutated["tasks"][44]["id"] = 44
        self.assertTrue(validate(mutated, self.source))
        mutated = deepcopy(self.base)
        mutated["tasks"].pop()
        self.assertTrue(validate(mutated, self.source))

    def test_malformed_rag_subtask_list_fails(self):
        mutated = deepcopy(self.base)
        mutated["tasks"][44]["subtasks"].pop()
        self.assertTrue(any("six subtasks" in x for x in validate(mutated, self.source)))

    def test_dont_silently_change_canonical_task_objective(self):
        mutated = deepcopy(self.base)
        mutated["tasks"][44]["objective"] = "Invent rules"
        self.assertTrue(any("canonical source" in x for x in validate(mutated, self.source)))

    def test_no_unverified_task_can_be_completed(self):
        mutated = deepcopy(self.base)
        mutated["tasks"][44]["status"] = "completed"
        self.assertTrue(any("without verified evidence" in x for x in validate(mutated, self.source)))
        self.assertTrue(any("without evidence_links" in x for x in validate(mutated, self.source)))

    def test_human_approval_gate_for_completed_task(self):
        mutated = deepcopy(self.base)
        task = mutated["tasks"][13]
        self.assertTrue(task["requires_human_approval"])
        task.update(status="completed", evidence_review="verified",
                    evidence_links=["https://github.com/example/meaningful-evidence"])
        self.assertTrue(any("human approval" in x for x in validate(mutated, self.source)))

    def test_global_execution_cannot_resume_while_unreconciled(self):
        mutated = deepcopy(self.base)
        mutated["execution_blocked_until_reconciled"] = False
        self.assertTrue(any("Execution cannot resume" in x for x in validate(mutated, self.source)))


if __name__ == "__main__":
    unittest.main()
