"""Apply the schema, prove the session, then roll it back."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))

import psycopg

HOST = "127.0.0.1"
PORT = "5432"
DBNAME = "paperpilot"
USER = "postgres"


def compose(args, check=True):
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", str(ROOT / "compose.yaml"), *args],
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            cwd=ROOT,
        )
    except FileNotFoundError:
        sys.exit("docker was not found on PATH")
    if check and result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        sys.exit(message or "docker compose failed")
    return result


def daemon_up():
    try:
        return subprocess.run(["docker", "info"], capture_output=True).returncode == 0
    except FileNotFoundError:
        sys.exit("docker was not found on PATH")


def alembic(*args):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT / "backend",
    )
    if result.returncode != 0:
        sys.exit(result.returncode)


def case_absent():
    with psycopg.connect(
        "host=%s port=%s dbname=%s user=%s" % (HOST, PORT, DBNAME, USER)
    ) as conn:
        row = conn.execute("SELECT to_regclass('public.case')").fetchone()
        if row[0] is not None:
            sys.exit("case still exists")


def main():
    if not daemon_up():
        sys.exit("docker is not running")
    try:
        compose(["up", "-d", "--wait", "postgres"])
        alembic("upgrade", "head")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(ROOT / "backend" / "test_auth.py"), str(ROOT / "backend" / "test_case.py"), str(ROOT / "backend" / "test_upload.py"), str(ROOT / "backend" / "test_backend.py"), str(ROOT / "backend" / "test_source.py"), str(ROOT / "backend" / "test_requirement.py"), "-q"],
            cwd=ROOT,
        )
        if result.returncode != 0:
            sys.exit(result.returncode)
        alembic("downgrade", "base")
        case_absent()
        print("auth ok")
    finally:
        compose(["down"], check=False)


if __name__ == "__main__":
    main()
