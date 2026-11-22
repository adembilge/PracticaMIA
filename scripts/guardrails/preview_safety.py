"""Offline checks for exact Preview targeting and synthetic identity boundaries."""
from __future__ import annotations

import re
from urllib.parse import urlsplit


class Blocked(RuntimeError):
    """External preview configuration or identity is not safely available."""


class Failed(RuntimeError):
    """A configured preview or ownership check violated its contract."""


_PREVIEW_HOST = re.compile(r"^practicamia-[a-z0-9-]+-firatadembilge-4729\.vercel\.app$")


def validate_target(base_url: str, allowed_host: str, auth0_host: str) -> str:
    parsed = urlsplit(base_url)
    host = parsed.hostname or ""
    if (
        parsed.scheme != "https" or parsed.username or parsed.password or parsed.port
        or parsed.path not in ("", "/") or parsed.query or parsed.fragment
        or not _PREVIEW_HOST.fullmatch(host)
        or host.startswith("practicamia-git-main-")
        or host != allowed_host
    ):
        raise Blocked("Target is not an exact allowlisted frontend preview")
    if (
        not auth0_host or auth0_host.lower() != auth0_host
        or not re.fullmatch(r"[a-z0-9.-]+\.auth0\.com", auth0_host)
    ):
        raise Blocked("Auth0 identity host is missing or invalid")
    return "https://" + host


def assert_identity_origin(url: str, auth0_host: str) -> None:
    target = urlsplit(url)
    if (
        target.scheme != "https" or target.hostname != auth0_host
        or target.username or target.password or target.port
    ):
        raise Blocked("Login page is not hosted on the expected Auth0 domain")


def require_test_accounts(env: dict[str, str]) -> None:
    fields = ("E2E_A_EMAIL", "E2E_A_PASSWORD", "E2E_B_EMAIL", "E2E_B_PASSWORD")
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


def assert_owner_state_unchanged(response, expected_state, label: str) -> None:
    status_is(response, 200, label)
    saved = response.json()
    if saved.get("state") != expected_state or saved.get("archived") is True:
        raise Failed(f"{label}: foreign mutation changed owner-scoped state")
