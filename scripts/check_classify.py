"""Run the classification checks. No database."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))


def main():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(ROOT / "backend" / "test_classify.py"), "-q"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    print("classify ok")


if __name__ == "__main__":
    main()
