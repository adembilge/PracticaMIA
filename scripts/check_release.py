"""Run the release hold. The decision stays held. No database."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))

REPORT = ROOT / "docs" / "testing" / "RELEASE.md"


def main():
    sys.path.insert(0, str(ROOT / "evaluation"))
    sys.path.insert(0, str(ROOT / "backend"))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(ROOT / "evaluation" / "test_release.py"),
            "-q",
            "--import-mode=importlib",
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    from release import report

    lines = report()
    if not lines or lines[-1] != "decision: held" or "go" in lines:
        sys.exit("\n".join(lines))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Release readiness\n\n"
        "The decision is held. Research stays unreviewed. "
        "No declaration is filed.\n\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )
    print("release held")


if __name__ == "__main__":
    main()
