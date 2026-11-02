"""Run the fixture, the rules, and the trusted-version search."""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))

sys.path.insert(0, str(ROOT / "evaluation"))

from knowledge import summarize

CHECKS = (
    ("rag", "check_rag.py"),
    ("rules", "check_rules.py"),
    ("retrieval", "check_retrieval.py"),
)


def main():
    summary = subprocess.run(
        [sys.executable, "-m", "pytest", str(ROOT / "evaluation" / "test_knowledge.py"), "-q"],
        cwd=ROOT,
    )
    if summary.returncode != 0:
        sys.exit(summary.returncode)
    rows = []
    for name, script in CHECKS:
        started = time.perf_counter()
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT)
        rows.append((name, result.returncode == 0, time.perf_counter() - started))
        if result.returncode != 0:
            for line in summarize(rows):
                print(line)
            sys.exit(result.returncode)
    for line in summarize(rows):
        print(line)


if __name__ == "__main__":
    main()
