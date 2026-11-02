"""Run the beta hold. No session is invented. No database."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))

REPORT = ROOT / "docs" / "testing" / "BETA.md"


def main():
    sys.path.insert(0, str(ROOT / "evaluation"))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(ROOT / "evaluation" / "test_beta.py"),
            "-q",
            "--import-mode=importlib",
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    from beta import load, report

    lines = report(load())
    if not lines or lines[-1] != "beta held":
        sys.exit("\n".join(lines))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Private beta\n\n"
        "No session was held. No declaration is filed.\n\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )
    print("beta held")


if __name__ == "__main__":
    main()
