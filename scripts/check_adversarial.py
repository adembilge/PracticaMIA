"""Run the adversarial evaluation. No live model."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))

REPORT = ROOT / "docs" / "testing" / "ADVERSARIAL.md"


def main():
    sys.path.insert(0, str(ROOT / "evaluation"))
    sys.path.insert(0, str(ROOT / "backend"))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(ROOT / "evaluation" / "test_adversarial.py"),
            str(ROOT / "backend" / "test_tools.py"),
            str(ROOT / "backend" / "test_model.py"),
            "-q",
            "--import-mode=importlib",
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    from adversarial import report, walk

    rows = walk()
    lines = report(rows)
    if not rows or not all(ok for _name, ok, _seconds in rows) or lines[-1] != "adversarial ok":
        sys.exit("\n".join(lines))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Adversarial inputs\n\n"
        "No threshold is approved. Untrusted text is not a stop, a tool, "
        "or another person's case.\n\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )
    print("adversarial ok")


if __name__ == "__main__":
    main()
