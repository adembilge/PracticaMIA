"""Pure offline guardrail tests: no network, credentials, browser or case writes."""
import unittest
from types import SimpleNamespace

from audit.authenticated_preview_e2e import (
    Blocked, Failed, assert_identity_origin, require_test_accounts,
    status_is, validate_target,
)

HOST = "practicamia-4cacckohr-firatadembilge-4729.vercel.app"
AUTH = "testing.eu.auth0.com"


class PreviewSafetyTests(unittest.TestCase):
    def test_exact_preview_allows_only_matching_operator_host(self):
        base = "https://" + HOST
        self.assertEqual(validate_target(base, HOST, AUTH), base)

    def test_production_phishing_and_main_alias_are_blocked(self):
        candidates = [
            "https://practicamia.vercel.app",
            "https://practicamia-api.vercel.app",
            "http://" + HOST,
            "https://evil.test@" + HOST,
            "https://" + HOST + ":443",
            "https://" + HOST + "/auth/login",
            "https://" + HOST + "?x=1",
            "https://practicamia-git-main-firatadembilge-4729.vercel.app",
            "https://practicamia-attacker.vercel.app",
        ]
        for url in candidates:
            with self.subTest(url=url), self.assertRaises(Blocked):
                validate_target(url, HOST, AUTH)

    def test_auth0_redirect_must_be_exact_expected_identity_host(self):
        assert_identity_origin("https://" + AUTH + "/u/login", AUTH)
        for url in ["https://evil.test/u/login", "https://" + AUTH + ".evil.test/u/login",
                    "http://" + AUTH + "/u/login", "https://user@" + AUTH]:
            with self.subTest(url=url), self.assertRaises(Blocked):
                assert_identity_origin(url, AUTH)

    def test_distinct_nonempty_synthetic_accounts_required(self):
        good = {"E2E_A_EMAIL": "a@example.test", "E2E_A_PASSWORD": "testA",
                "E2E_B_EMAIL": "b@example.test", "E2E_B_PASSWORD": "testB"}
        require_test_accounts(good)
        with self.assertRaises(Blocked):
            require_test_accounts({**good, "E2E_B_EMAIL": "A@EXAMPLE.TEST"})
        with self.assertRaises(Blocked):
            require_test_accounts({**good, "E2E_A_PASSWORD": ""})

    def test_expected_reviewer_denial_is_a_pass_not_preview_blocker(self):
        status_is(SimpleNamespace(status=403), 403, "ordinary user denied")
        with self.assertRaises(Blocked):
            status_is(SimpleNamespace(status=403), 200, "reviewer")
        with self.assertRaises(Failed):
            status_is(SimpleNamespace(status=200), 404, "cross-user read")


if __name__ == "__main__":
    unittest.main()
