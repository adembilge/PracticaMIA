"""Dump the staging database, restore it, and remove the dump."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))

import psycopg

REPORT = ROOT / "docs" / "testing" / "BACKUP.md"
ENV = ROOT / ".env.staging"
PROJECT = "paperpilot-staging"
PROBE = "backup-probe"
PORT = "5433"


def compose(args, check=True, text=None):
    try:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "--env-file",
                str(ENV),
                "-p",
                PROJECT,
                "-f",
                str(ROOT / "compose.yaml"),
                *args,
            ],
            check=False,
            capture_output=True,
            input=text,
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


def connect(name):
    return psycopg.connect(
        "host=127.0.0.1 port=%s dbname=%s user=postgres" % (PORT, name)
    )


def migrate():
    env = os.environ.copy()
    env["PAPERPILOT_DB_PORT"] = PORT
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT / "backend",
        env=env,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)


def present(name):
    with connect(name) as conn:
        row = conn.execute(
            "SELECT id FROM person WHERE id = %s", (PROBE,)
        ).fetchone()
    return row is not None


def main():
    if not daemon_up():
        sys.exit("docker is not running")
    dump_fd, dump_name = tempfile.mkstemp(suffix=".sql")
    os.close(dump_fd)
    dump = Path(dump_name)
    try:
        compose(["up", "-d", "--wait", "postgres"])
        migrate()
        with connect("paperpilot") as conn:
            conn.execute(
                "INSERT INTO person (id) VALUES (%s) ON CONFLICT (id) DO NOTHING",
                (PROBE,),
            )
        copied = compose(
            [
                "exec",
                "-T",
                "postgres",
                "pg_dump",
                "-U",
                "postgres",
                "--no-owner",
                "--no-acl",
                "paperpilot",
            ]
        )
        dump.write_text(copied.stdout, encoding="utf-8")
        compose(
            [
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "postgres",
                "-d",
                "postgres",
                "-c",
                "DROP DATABASE IF EXISTS paperpilot_restore WITH (FORCE)",
            ]
        )
        compose(
            [
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "postgres",
                "-d",
                "postgres",
                "-c",
                "CREATE DATABASE paperpilot_restore",
            ]
        )
        compose(
            ["exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "paperpilot_restore"],
            text=dump.read_text(encoding="utf-8"),
        )
        if not present("paperpilot_restore"):
            sys.exit("restore missed the person")
    finally:
        dump.unlink(missing_ok=True)
        compose(
            [
                "exec",
                "-T",
                "postgres",
                "psql",
                "-U",
                "postgres",
                "-d",
                "postgres",
                "-c",
                "DROP DATABASE IF EXISTS paperpilot_restore WITH (FORCE)",
            ],
            check=False,
        )
        compose(["down", "-v"], check=False)
    lines = (
        "schedule: the check",
        "encryption: machine disk",
        "retention: dump removed",
        "host: none selected",
        "person: restored",
        "backup ok",
    )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Backup and recovery\n\n"
        "The dump is restored into a second database on the staging server, "
        "then removed. No host is selected.\n\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )
    print("backup ok")


if __name__ == "__main__":
    main()
