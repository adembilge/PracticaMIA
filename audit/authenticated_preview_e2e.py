"""Opt-in synthetic two-account browser check against an exact allowlisted Vercel preview.

Never call this against production, real personal cases, or an untrusted login host.
No sources are approved and no LLM is called by this program.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from uuid import UUID


class Blocked(RuntimeError):
    """External preview configuration, authentication or protection is unavailable."""


class Failed(RuntimeError):
    """A configured preview returned a security or behavior regression."""


_PREVIEW_HOST = re.compile(r"^practicamia-[a-z0-9-]+-firatadembilge-4729\.vercel\.app$")


def validate_target(base_url: str, allowed_host: str, auth0_host: str) -> str:
    """Require operator-allowlisted exact preview + separate expected identity host."""
    parsed = urlsplit(base_url)
    host = parsed.hostname or ""
    if (parsed.scheme != "https" or parsed.username or parsed.password or parsed.port
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment
            or not _PREVIEW_HOST.fullmatch(host)
            or host.startswith("practicamia-git-main-")
            or host != allowed_host):
        raise Blocked("Target is not an exact allowlisted frontend preview")
    if (not auth0_host or auth0_host.lower() != auth0_host
            or not re.fullmatch(r"[a-z0-9.-]+\.auth0\.com", auth0_host)):
        raise Blocked("Auth0 identity host is missing or invalid")
    return "https://" + host


def assert_identity_origin(url: str, auth0_host: str) -> None:
    target = urlsplit(url)
    if (target.scheme != "https" or target.hostname != auth0_host
            or target.username or target.password or target.port):
        raise Blocked("Login page is not hosted on the expected Auth0 domain")


def require_test_accounts(env: dict[str, str]) -> None:
    fields = (
        "E2E_A_EMAIL", "E2E_A_PASSWORD", "E2E_B_EMAIL", "E2E_B_PASSWORD",
    )
    if any(not env.get(field) for field in fields):
        raise Blocked("Two dedicated synthetic Auth0 test accounts are required")
    if env["E2E_A_EMAIL"].lower() == env["E2E_B_EMAIL"].lower():
        raise Blocked("Test accounts must have distinct email identities")


def status_is(response, expected: int, label: str) -> None:
    if response.status == expected:
        return
    if response.status in (403, 429, 502, 503):
        raise Blocked(f"{label}: preview inaccessible or unconfigured (HTTP {response.status})")
    raise Failed(f"{label}: expected HTTP {expected}, received HTTP {response.status}")


def login(context, base: str, auth0_host: str, email: str, password: str):
    """Use the real Auth0 hosted login; never fill credentials on an unknown host."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    page = context.new_page()
    try:
        page.goto(base + "/auth/login", wait_until="domcontentloaded", timeout=30000)
        assert_identity_origin(page.url, auth0_host)
        username = page.locator('input[name="username"], input[type="email"]').first
        username.wait_for(state="visible", timeout=10000)
        username.fill(email)
        password_input = page.locator('input[name="password"], input[type="password"]').first
        if not password_input.is_visible():
            page.locator('button[type="submit"]').first.click()
            assert_identity_origin(page.url, auth0_host)
            password_input.wait_for(state="visible", timeout=10000)
        password_input.fill(password)
        page.locator('button[type="submit"]').first.click()
        page.wait_for_url(lambda url: str(url).startswith(base + "/"), timeout=30000)
        page.goto(base + "/account", wait_until="domcontentloaded", timeout=30000)
        # Cookie session -> server-side OAuth token -> backend must work.
        status_is(context.request.get(base + "/api/cases"), 200, "authenticated cases")
        return page
    except PlaywrightTimeoutError as exc:
        raise Blocked("Auth0 login did not complete: MFA, CAPTCHA or preview callback may need operator setup") from exc


def run_checks(base: str, auth0_host: str, env: dict[str, str]) -> dict[str, object]:
    from playwright.sync_api import sync_playwright

    completed: list[str] = []
    created: list[tuple[object, str]] = []
    headers = {"Origin": base, "Content-Type": "application/json"}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            a = browser.new_context()
            b = browser.new_context()
            page_a = login(a, base, auth0_host, env["E2E_A_EMAIL"], env["E2E_A_PASSWORD"])
            login(b, base, auth0_host, env["E2E_B_EMAIL"], env["E2E_B_PASSWORD"])
            completed.append("distinct real Auth0 browser sessions")

            try:
                created_a = a.request.post(base + "/api/cases", data={}, headers=headers)
                status_is(created_a, 201, "account A creates synthetic case")
                id_a = str(UUID(created_a.json()["id"]))
                created.append((a, id_a))
                status_is(a.request.patch(base + f"/api/cases/{id_a}/scope",
                                          data={"answers": ["yes", "yes", "yes", "no", "yes"]},
                                          headers=headers), 200, "A updates own case")
                completed.append("A creates and updates synthetic case")

                status_is(b.request.get(base + f"/api/cases/{id_a}"), 404, "B cannot read A")
                status_is(b.request.patch(base + f"/api/cases/{id_a}/scope",
                                          data={"answers": ["unsure"]}, headers=headers),
                          404, "B cannot update A")
                status_is(b.request.delete(base + f"/api/cases/{id_a}", headers=headers),
                          404, "B cannot delete A")
                if any(row["id"] == id_a for row in b.request.get(base + "/api/cases").json()):
                    raise Failed("B can list A's case")
                completed.append("B cannot read, update, delete or list A case")

                created_b = b.request.post(base + "/api/cases", data={}, headers=headers)
                status_is(created_b, 201, "account B creates synthetic case")
                id_b = str(UUID(created_b.json()["id"]))
                created.append((b, id_b))
                status_is(a.request.get(base + f"/api/cases/{id_b}"), 404, "A cannot read B")
                if any(row["id"] == id_b for row in a.request.get(base + "/api/cases").json()):
                    raise Failed("A can list B's case")
                completed.append("bidirectional tenant isolation")

                page_a.goto(base + "/cases/saved", wait_until="domcontentloaded")
                page_a.locator(".saved-case-list li").filter(has_text=id_a[:8]).locator("a").first.click(timeout=15000)
                page_a.wait_for_url(base + f"/cases/{id_a}", timeout=15000)
                page_a.reload(wait_until="domcontentloaded")
                status_is(a.request.get(base + f"/api/cases/{id_a}"), 200, "case persists after reload")
                completed.append("browser reload and saved-case resumption")

                # A must be allowlisted reviewer, B an ordinary test user.
                review = a.request.get(base + "/api/knowledge/review/browser-queue")
                if review.status == 404:
                    raise Blocked("Preview reviewer UI/route is not enabled")
                status_is(review, 200, "verified reviewer can read queue")
                status_is(b.request.get(base + "/api/knowledge/review/browser-queue"),
                          403, "ordinary account cannot read reviewer queue")
                queue = review.json()
                if not isinstance(queue, list):
                    raise Failed("Reviewer queue response has unexpected shape")
                completed.append("reviewer-only queue access")
                if not queue:
                    raise Blocked("Reviewer queue is empty; full-text source review cannot be tested")
                version_id = str(UUID(queue[0]["version_id"]))
                preview = a.request.get(base + f"/api/knowledge/review/versions/{version_id}")
                status_is(preview, 200, "reviewer full article")
                captured = preview.json()
                if not captured.get("integrity_verified") or not captured.get("normalized_text"):
                    raise Failed("Full article missing or integrity verification false")
                status_is(b.request.get(base + f"/api/knowledge/review/versions/{version_id}"),
                          403, "ordinary account cannot inspect article")
                completed.append("reviewer full captured article and integrity")
            finally:
                for owner, case_id in reversed(created):
                    cleanup = owner.request.delete(base + f"/api/cases/{case_id}", headers=headers)
                    status_is(cleanup, 204, "synthetic test-case cleanup")
                if created:
                    completed.append("created synthetic cases deleted")
        finally:
            browser.close()
    return {"completed_checks": completed, "approval_performed": False, "llm_called": False}


def main() -> int:
    summary: dict[str, object] = {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
                                   "mode": "opt_in_synthetic_two_account_preview"}
    try:
        env = dict(os.environ)
        if env.get("E2E_ACK_SYNTHETIC_ONLY") != "YES":
            raise Blocked("Explicit synthetic-only acknowledgement is required")
        base = validate_target(env.get("E2E_PREVIEW_BASE_URL", ""),
                               env.get("E2E_ALLOWED_PREVIEW_HOST", ""),
                               env.get("E2E_AUTH0_HOST", ""))
        require_test_accounts(env)
        summary.update(run_checks(base, env["E2E_AUTH0_HOST"], env))
        summary["verdict"] = "pass"
        return_code = 0
    except Blocked as exc:
        summary.update(verdict="blocked", reason=str(exc))
        return_code = 2
    except (Failed, KeyError, ValueError) as exc:
        summary.update(verdict="fail", reason=(str(exc) if isinstance(exc, Failed)
                                                     else "Unexpected API response shape"))
        return_code = 1
    except Exception:
        # No credentials, callback URLs, response data or tokens in errors.
        summary.update(verdict="blocked", reason="Browser or external identity flow failed")
        return_code = 2
    path = Path("audit/results/authenticated_preview_e2e.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return return_code


if __name__ == "__main__":
    sys.exit(main())
