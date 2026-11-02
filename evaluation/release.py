"""Link the existing checks. The decision stays held."""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "backend"))

import adversarial
import agent
import documents
import grounded
import performance
import privacy
from regression import load, measure

USABILITY = ROOT / "docs" / "testing" / "USABILITY.md"
BLOCKERS = (
    "design: unapproved",
    "security: unreviewed",
    "research: unreviewed",
    "budget: none approved",
    "deployment: not started",
)


def _ok(lines, closer):
    return bool(lines) and lines[-1] == closer


def _gates():
    return (
        ("scenarios", _ok(agent.report(*agent.walk()), "agent ok")),
        ("documents", _ok(documents.report(documents.walk()), "documents ok")),
        ("grounded", _ok(grounded.report(grounded.walk()), "grounded ok")),
        ("adversarial", _ok(adversarial.report(adversarial.walk()), "adversarial ok")),
        ("privacy", _ok(privacy.report(privacy.walk()), "privacy ok")),
        ("performance", _ok(performance.report(performance.walk()), "performance ok")),
        ("regression", measure() == load()),
        (
            "usability",
            USABILITY.read_text(encoding="utf-8").strip().splitlines()[-1] == "usability ok",
        ),
    )


def report():
    lines = []
    failed = []
    for name, ok in _gates():
        if ok:
            lines.append(name + " held")
        else:
            failed.append(name)
    if failed:
        lines.append("failed: " + ", ".join(failed))
        return lines
    lines.extend(BLOCKERS)
    lines.append("decision: held")
    return lines
