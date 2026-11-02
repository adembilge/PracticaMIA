"""Run the agent evaluation. No model call."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))

REPORT = ROOT / "docs" / "testing" / "AGENT.md"


def main():
    sys.path.insert(0, str(ROOT / "evaluation"))
    sys.path.insert(0, str(ROOT / "backend"))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(ROOT / "evaluation" / "test_agent.py"),
            str(ROOT / "evaluation" / "test_retrieval.py"),
            "-q",
            "--import-mode=importlib",
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    from agent import report, walk

    rows, traces = walk()
    lines = report(rows, traces)
    if traces or "agent ok" not in lines:
        sys.exit("\n".join(lines))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Workflow accuracy\n\n"
        "No threshold is approved. A research row stays unreviewed. The model is not called.\n\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )
    print("agent ok")


if __name__ == "__main__":
    main()
