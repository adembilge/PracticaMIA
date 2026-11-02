"""Run the functional suite on a throwaway database."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))

import psycopg

HOST = os.environ.get("PAPERPILOT_DB_HOST", "127.0.0.1")
PORT = os.environ.get("PAPERPILOT_DB_PORT", "5432")
ADMIN = os.environ.get("PAPERPILOT_DB_NAME", "paperpilot")
USER = os.environ.get("PAPERPILOT_DB_USER", "postgres")
NAME = "paperpilot_functional"
REPORT = ROOT / "docs" / "testing" / "FUNCTIONAL.md"
AREAS = """# Functional coverage

The suite runs on `paperpilot_functional` and drops that database. It does not migrate `paperpilot`.

- Authentication: backend/test_auth.py
- Case, intake, checklist, review: backend/test_case.py, backend/test_onboard.py, backend/test_list.py, backend/test_case_review.py, backend/test_backend.py
- Sources and retrieval: backend/test_source.py, backend/test_ingest.py, backend/test_retrieval.py, evaluation/test_retrieval.py
- Rules: backend/test_rules.py, backend/test_procedure.py, backend/test_checklist.py, backend/test_prepare.py
- Agent state: backend/test_session.py, backend/test_graph.py, backend/test_plan.py, backend/test_chat.py, evaluation/test_agent.py
- Documents: backend/test_upload.py, backend/test_papers.py, evaluation/test_documents.py
- Frontend loaders: frontend/test
"""


def connect(dbname):
    return psycopg.connect(
        "host=%s port=%s dbname=%s user=%s" % (HOST, PORT, dbname, USER),
        autocommit=True,
    )


def drop():
    with connect(ADMIN) as conn:
        conn.execute("DROP DATABASE IF EXISTS %s WITH (FORCE)" % NAME)


def create():
    drop()
    with connect(ADMIN) as conn:
        conn.execute("CREATE DATABASE %s" % NAME)
    with connect(NAME) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")


def run(args, env, cwd):
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result


def pytest_summary(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        if "passed" in line or "failed" in line or "error" in line:
            return line
    return lines[-1] if lines else "no output"


def node_summary(text):
    found = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# tests ") or stripped.startswith("# pass ") or stripped.startswith("# fail "):
            found.append(stripped.lstrip("# ").strip())
    if found:
        return ", ".join(found)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else "no output"


def main():
    if ADMIN == NAME:
        sys.exit("refusing to replace the admin database")
    env = os.environ.copy()
    env["PAPERPILOT_DB_HOST"] = HOST
    env["PAPERPILOT_DB_PORT"] = PORT
    env["PAPERPILOT_DB_USER"] = USER
    env["PAPERPILOT_DB_NAME"] = NAME
    try:
        if REPORT.is_file():
            REPORT.unlink()
        create()
        upgraded = run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            env,
            ROOT / "backend",
        )
        if upgraded.returncode != 0:
            sys.exit(upgraded.returncode)
        pytest_args = [
            sys.executable,
            "-m",
            "pytest",
            str(ROOT / "backend"),
            str(ROOT / "evaluation"),
            "-q",
            "--import-mode=importlib",
        ]
        tested = run(pytest_args, env, ROOT)
        if tested.returncode != 0:
            sys.exit(tested.returncode)
        files = sorted(str(path) for path in (ROOT / "frontend" / "test").glob("*.mjs"))
        node = run(
            ["node", "--experimental-strip-types", "--test", *files],
            env,
            ROOT,
        )
        if node.returncode != 0:
            sys.exit(node.returncode)
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(
            AREAS + "\npytest: %s\nnode: %s\n" % (pytest_summary(tested.stdout), node_summary(node.stdout)),
            encoding="utf-8",
        )
        print("functional ok")
    finally:
        drop()


if __name__ == "__main__":
    main()
