"""Apply the schema, prove retrieval, then roll it back."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))

import check_auth


def main():
    if not check_auth.daemon_up():
        sys.exit("docker is not running")
    try:
        check_auth.compose(["up", "-d", "--wait", "postgres"])
        check_auth.alembic("upgrade", "head")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(ROOT / "backend" / "test_retrieval.py"), "-x", "-q"],
            cwd=ROOT,
        )
        if result.returncode != 0:
            sys.exit(result.returncode)
        check_auth.alembic("downgrade", "base")
        check_auth.case_absent()
        print("retrieval ok")
    finally:
        check_auth.compose(["down"], check=False)


if __name__ == "__main__":
    main()
