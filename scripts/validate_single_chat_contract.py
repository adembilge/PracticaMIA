"""Offline product-governance gate: the customer UX is chat-only (D-010).

This validates binding planning documents, NOT that the hosted product has
already migrated. Legacy case routes remain until a separately verified release.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PHASES = tuple(
    f"planning/practicamia-2/phase-{n:02d}-" for n in range(4, 11)
)
FILES = (
    "docs/SINGLE_CHAT_PRODUCT_CONTRACT.md",
    "docs/SINGLE_CHAT_GAP_AUDIT.md",
    "docs/DECISIONS.md",
    "AGENTS.md",
    "README.md",
    "PracticaMIA_Complete_Project_Specification.md",
)
PHASE_FILES = (
    "planning/practicamia-2/phase-04-agent-and-conversation-engine.md",
    "planning/practicamia-2/phase-05-single-ui-and-chat-workspace.md",
    "planning/practicamia-2/phase-06-document-upload-ocr-and-verification.md",
    "planning/practicamia-2/phase-07-requirements-forms-and-official-handoff.md",
    "planning/practicamia-2/phase-08-case-management-and-tracking.md",
    "planning/practicamia-2/phase-09-privacy-security-and-quality-evaluation.md",
    "planning/practicamia-2/phase-10-pilot-release-and-nationwide-growth.md",
)
# Customer-facing legacy routes are retained only to protect prior records and
# synthetic regression coverage during migration. Report them on every CI run.
# The strict release gate must fail until they have been retired safely.
LEGACY_CUSTOMER_ROUTES = (
    "frontend/src/app/cases/new/page.tsx",
    "frontend/src/app/cases/saved/page.tsx",
    "frontend/src/app/cases/[id]/page.tsx",
    "frontend/src/app/cases/[id]/documents/page.tsx",
    "frontend/src/app/cases/[id]/preparation/page.tsx",
    "frontend/src/app/cases/[id]/assistant/page.tsx",
    "frontend/src/app/cases/demo/page.tsx",
    "frontend/src/app/cases/demo/review/page.tsx",
    "frontend/src/app/demo/synthetic/page.tsx",
    "frontend/src/app/account/page.tsx",
)
CHAT_FIXTURE = "frontend/tests/acceptance/agent-reconnect.tsx"
FORBIDDEN_VISIBLE_CHAT = (
    "Cases in this conversation",
    "Open saved case task",
    "<strong>Saved case:</strong>",
    "No linked cases.",
)


def unregistered_customer_pages(root: Path) -> list[str]:
    """Reject new separate case/demo customer routes before Phase 5 migration."""
    app = root / "frontend/src/app"
    registered = set(LEGACY_CUSTOMER_ROUTES)
    found: list[str] = []
    for folder in ("cases", "demo"):
        if (app / folder).is_dir():
            for page in (app / folder).rglob("page.tsx"):
                path = page.relative_to(root).as_posix()
                if path not in registered:
                    found.append(path)
    return sorted(found)


def runtime_legacy_inventory(root: Path) -> list[str]:
    """Outstanding old customer routes; never remove stored data in this audit."""
    issues = [
        f"Legacy customer page: {path}"
        for path in LEGACY_CUSTOMER_ROUTES if (root / path).is_file()
    ]
    main = root / "frontend/src/app/page.tsx"
    if main.is_file() and "HomeView" in main.read_text(encoding="utf-8"):
        issues.append("Root still renders the editorial HomeView, not a chat shell")
    nav = root / "frontend/src/components/SiteHeader.tsx"
    if nav.is_file() and ('href="/cases/new"' in nav.read_text(encoding="utf-8")):
        issues.append("Site header still links to old case creation")
    return issues


def validate_visible_chat_fixture(content: str) -> list[str]:
    return [
        f"Chat fixture still exposes legacy case navigation: {marker}"
        for marker in FORBIDDEN_VISIBLE_CHAT if marker in content
    ]


REQUIRED = {
    "docs/SINGLE_CHAT_PRODUCT_CONTRACT.md": ("There is no user-facing case", "one ChatGPT-style", "Phase 5 is not"),
    "docs/SINGLE_CHAT_GAP_AUDIT.md": ("Not D-010-compliant yet", "legacy"),
    "docs/DECISIONS.md": ("## D-010", "no user-facing cases"),
    "AGENTS.md": ("Non-negotiable single-chat", "do not implement Phase 5"),
    "README.md": ("single-chat", "not yet deployed"),
    "PracticaMIA_Complete_Project_Specification.md": ("Current architecture amendment", "single-chat only"),
}


def validate_texts(contents: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for name, tokens in REQUIRED.items():
        value = contents.get(name)
        if value is None:
            errors.append(f"Missing single-chat contract source: {name}")
            continue
        for token in tokens:
            if token.lower() not in value.lower():
                errors.append(f"{name}: missing contract marker {token!r}")
    for name in PHASE_FILES:
        value = contents.get(name)
        if value is None or "D-010 binding product contract" not in value:
            errors.append(f"{name}: binding one-chat requirement is missing")
    phase5 = contents.get(PHASE_FILES[1], "")
    phase8 = contents.get(PHASE_FILES[4], "")
    prohibited = {
        "Phase 5 permits a case switcher": "a compact conversation/case switcher may live",
        "Phase 5 shows selectable cases": "show name, status, last update, and next action. selecting a case",
        "Phase 8 requires a case switcher": "in-chat conversation/case switcher",
    }
    for label, text in prohibited.items():
        document = phase8 if label.startswith("Phase 8") else phase5
        if text in document.lower():
            errors.append(label)
    return errors


def main(root: Path = ROOT) -> int:
    sources: dict[str, str] = {}
    missing = []
    for name in (*FILES, *PHASE_FILES):
        try:
            sources[name] = (root / name).read_text(encoding="utf-8")
        except OSError:
            missing.append(name)
    errors = [f"Missing file: {name}" for name in missing] + validate_texts(sources)
    if errors:
        for error in errors:
            print("ERROR: " + error, file=sys.stderr)
        return 1
    fixture = root / CHAT_FIXTURE
    if not fixture.is_file():
        print(f"ERROR: Missing chat fixture: {CHAT_FIXTURE}", file=sys.stderr)
        return 1
    visible_errors = validate_visible_chat_fixture(fixture.read_text(encoding="utf-8"))
    new_routes = unregistered_customer_pages(root)
    visible_errors.extend(
        f"Unapproved standalone customer page: {path}" for path in new_routes
    )
    if visible_errors:
        for error in visible_errors:
            print("ERROR: " + error, file=sys.stderr)
        return 1
    legacy = runtime_legacy_inventory(root)
    for item in legacy:
        print("LEGACY MIGRATION BLOCKER: " + item)
    if "--require-migrated" in sys.argv and legacy:
        print("FAIL: legacy customer routes or landing remain in the release candidate")
        return 1
    print("PASS: D-010 planning contract and chat-fixture no-case surface")
    print(f"NOTE: Hosted chat migration is {'NOT complete' if legacy else 'not yet live-verified'}; legacy blockers: {len(legacy)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
