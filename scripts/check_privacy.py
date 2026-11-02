"""Run the privacy verification. No database."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))

REPORT = ROOT / "docs" / "testing" / "PRIVACY.md"


def main():
    sys.path.insert(0, str(ROOT / "evaluation"))
    sys.path.insert(0, str(ROOT / "backend"))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(ROOT / "evaluation" / "test_privacy.py"),
            "-q",
            "--import-mode=importlib",
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    from privacy import report, walk

    rows = walk()
    lines = report(rows)
    if not rows or not all(ok for _name, ok, _seconds in rows) or lines[-1] != "privacy ok":
        sys.exit("\n".join(lines))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Privacy and security\n\n"
        "No threshold is approved. A legal or specialist review is separate. "
        "The database is not opened.\n\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )
    print("privacy ok")


if __name__ == "__main__":
    main()
