"""Run the performance walk. No database."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))

REPORT = ROOT / "docs" / "testing" / "PERFORMANCE.md"


def main():
    sys.path.insert(0, str(ROOT / "evaluation"))
    sys.path.insert(0, str(ROOT / "backend"))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(ROOT / "evaluation" / "test_performance.py"),
            "-q",
            "--import-mode=importlib",
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    from performance import report, walk

    rows = walk()
    lines = report(rows)
    if not rows or not all(ok for _name, ok, _seconds in rows) or lines[-1] != "performance ok":
        sys.exit("\n".join(lines))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Performance and cost\n\n"
        "No operating budget is approved. The model provider stays local. "
        "The database is not opened.\n\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )
    print("performance ok")


if __name__ == "__main__":
    main()
