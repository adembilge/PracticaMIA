"""Run the monitor check. Names only. No database."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))

REPORT = ROOT / "docs" / "testing" / "MONITOR.md"


def main():
    sys.path.insert(0, str(ROOT / "evaluation"))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(ROOT / "evaluation" / "test_monitor.py"),
            "-q",
            "--import-mode=importlib",
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    from monitor import NAMES, alert

    lines = alert("retrieval")
    if lines != ["alert: retrieval"]:
        sys.exit("\n".join(lines))
    written = [name + " held" for name in NAMES]
    written.extend(lines)
    written.extend(["research: unreviewed", "monitor ok"])
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# RAG and agent monitoring\n\n"
        "The recorder stores an event name. A body, a path, or a password is refused.\n\n"
        + "\n".join(written)
        + "\n",
        encoding="utf-8",
    )
    print("monitor ok")


if __name__ == "__main__":
    main()
