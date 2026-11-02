"""Prove the local PostgreSQL service starts, accepts a connection, and stops."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
if VENV_PYTHON.is_file() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    raise SystemExit(subprocess.call([str(VENV_PYTHON), *sys.argv]))

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
            text=True,
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


def prove():
    with psycopg.connect(
        "host=%s port=%s dbname=%s user=%s" % (HOST, PORT, DBNAME, USER)
    ) as conn:
        one = conn.execute("SELECT 1").fetchone()
        if one[0] != 1:
            sys.exit("database returned %s" % (one[0],))
        ext = conn.execute(
            "SELECT extname FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()
        if ext is None:
            sys.exit("vector extension is missing")
    print("infra ok")


def main():
    if not daemon_up():
        sys.exit("docker is not running")
    try:
        compose(["up", "-d", "--wait"])
        prove()
    finally:
        compose(["down"], check=False)


if __name__ == "__main__":
    main()
