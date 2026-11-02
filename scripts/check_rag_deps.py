"""Prove the local embedding provider, pgvector, and keyword search."""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PYTHON = ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
if VENV_PYTHON.is_file() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    raise SystemExit(subprocess.call([str(VENV_PYTHON), *sys.argv]))

sys.path.insert(0, str(ROOT / "backend"))

import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector

from embeddings import DIM, embed

NAME = "paperpilot-rag-check"
PORT = "54329"
IMAGE = "pgvector/pgvector:pg16"
ENGINE = Path(r"C:\Program Files\Docker\Docker\resources\com.docker.backend.exe")


def docker(args, check=True):
    return subprocess.run(["docker", *args], check=check, capture_output=True, text=True)


def daemon_up():
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


def wait_until(probe, seconds, message):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if probe():
            return
        time.sleep(2)
    sys.exit(message)


def ensure_docker():
    if daemon_up():
        return
    if not ENGINE.is_file():
        sys.exit("docker is not running and the Docker engine was not found")
    # shortcut: Docker Desktop.exe does not launch on this install, start the engine directly
    subprocess.Popen(
        [str(ENGINE), "-with-frontend=false", "-unattended", "-accept-license"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    wait_until(daemon_up, 180, "docker did not start")


def postgres_ready():
    result = subprocess.run(
        ["docker", "exec", NAME, "pg_isready", "-U", "postgres"],
        capture_output=True,
    )
    return result.returncode == 0


def prove():
    nearer = embed("residence permit office")
    other = embed("tax payment desk")
    query = embed("residence permit")
    if len(nearer) != DIM or len(query) != DIM:
        sys.exit("embedding length is not %s" % DIM)
    with psycopg.connect("host=127.0.0.1 port=%s dbname=postgres user=postgres" % PORT) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()
        register_vector(conn)
        conn.execute("DROP TABLE IF EXISTS rag_probe")
        conn.execute(
            "CREATE TABLE rag_probe (id int PRIMARY KEY, body text NOT NULL, embedding vector(%s))" % DIM
        )
        conn.execute(
            "INSERT INTO rag_probe (id, body, embedding) VALUES (%s, %s, %s), (%s, %s, %s)",
            (1, "residence permit office", Vector(nearer), 2, "tax payment desk", Vector(other)),
        )
        rank = conn.execute(
            "SELECT id FROM rag_probe ORDER BY embedding <=> %s LIMIT 1",
            (Vector(query),),
        ).fetchone()
        if rank[0] != 1:
            sys.exit("similarity query ranked %s first" % rank[0])
        hit = conn.execute(
            "SELECT id FROM rag_probe WHERE to_tsvector('simple', body) @@ plainto_tsquery('simple', %s)",
            ("permit",),
        ).fetchall()
        if [row[0] for row in hit] != [1]:
            sys.exit("keyword query returned %s" % hit)
    print("rag deps ok")


def main():
    ensure_docker()
    docker(["rm", "-f", NAME], check=False)
    docker([
        "run", "-d", "--name", NAME,
        "-e", "POSTGRES_HOST_AUTH_METHOD=trust",
        "-e", "POSTGRES_PASSWORD=rag",
        "-p", "%s:5432" % PORT,
        IMAGE,
    ])
    try:
        wait_until(postgres_ready, 120, "postgres did not become ready")
        prove()
    finally:
        docker(["rm", "-f", NAME], check=False)


if __name__ == "__main__":
    main()
