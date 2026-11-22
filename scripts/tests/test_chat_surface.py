from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "frontend" / "src" / "app"
COMPONENTS = ROOT / "frontend" / "src" / "components"


class SingleChatSurfaceTests(unittest.TestCase):
    def test_root_is_the_only_customer_application_shell(self):
        page = (APP / "page.tsx").read_text(encoding="utf-8")
        self.assertIn("SingleChatWorkspace", page)
        self.assertNotIn("HomeView", page)

    def test_legacy_customer_routes_are_absent(self):
        for path in ("cases", "demo", "account"):
            self.assertFalse((APP / path).exists(), path)
        self.assertFalse((APP / "api" / "cases").exists())
        self.assertFalse((APP / "api" / "demo").exists())

    def test_legacy_customer_components_are_absent(self):
        for name in (
            "HomeView.tsx", "SiteHeader.tsx", "DemoProvider.tsx",
            "SyntheticDemoWorkspace.tsx", "SavedCaseWorkspace.tsx",
            "SavedCasesView.tsx", "StartCaseView.tsx",
        ):
            self.assertFalse((COMPONENTS / name).exists(), name)

    def test_phase_four_is_active_and_phase_five_is_paused(self):
        active = (ROOT / "docs" / "ACTIVE_WORK.md").read_text(encoding="utf-8")
        contract = (ROOT / "docs" / "SINGLE_CHAT_PRODUCT_CONTRACT.md").read_text(encoding="utf-8")
        self.assertIn("Phase 4", active)
        self.assertIn("Phase 5 is paused", active)
        self.assertIn("production execution is disabled", contract.lower())


if __name__ == "__main__":
    unittest.main()
