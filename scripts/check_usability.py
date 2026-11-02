"""Run the usability checks. No database."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "testing" / "USABILITY.md"
LINES = (
    "journeys held",
    "screen held",
    "keyboard held",
    "forms held",
    "language held",
    "errors held",
    "interruptions held",
    "completion held",
    "fixes: italian status, document language, review labels",
    "limit: the review handoff sentence stays English",
    "people: none",
    "research: unreviewed",
    "design: unapproved",
    "usability ok",
)


def main():
    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--test",
            str(ROOT / "frontend" / "test" / "usability.test.mjs"),
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Usability and accessibility\n\n"
        "No participant session. Research rows stay unreviewed. "
        "The design direction stays unapproved.\n\n"
        + "\n".join(LINES)
        + "\n",
        encoding="utf-8",
    )
    print("usability ok")


if __name__ == "__main__":
    main()
