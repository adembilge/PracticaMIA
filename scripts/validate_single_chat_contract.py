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
    print("PASS: D-010 single-chat contract and Phase 4–10 planning gates")
    print("NOTE: Hosted single-chat UI migration is NOT verified by this planning check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
