"""Start the production project, prove the locked ports, and remove its volume."""
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "testing" / "PRODUCTION.md"
ENV = ROOT / ".env.production"
PROJECT = "paperpilot-production"
API = "http://127.0.0.1:8002"


def compose(args, check=True):
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
                "-f",
                str(ROOT / "compose.production.yaml"),
                *args,
            ],
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


def locked(text, env_text):
    api, postgres = text.split("\n  postgres:\n", 1)
    return (
        "source: paperpilot-production-pgdata" in postgres
        and "source: paperpilot-pgdata" not in text
        and "published:" not in postgres
        and "PAPERPILOT_ENV: production" in api
        and "password" not in env_text.lower()
        and "password" not in text.lower()
    )


def status(path):
    try:
        with urllib.request.urlopen(API + path) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def prove():
    rows = []
    for path in ("/health", "/v1/health"):
        code, body = status(path)
        if code != 200 or json.loads(body.decode()) != {"status": "ok"}:
            sys.exit(path)
        rows.append(path + " ok")
    for path in ("/docs", "/redoc", "/openapi.json"):
        code, _body = status(path)
        if code != 404:
            sys.exit(path)
        rows.append(path + " hidden")
    return rows


def main():
    if not daemon_up():
        sys.exit("docker is not running")
    env_text = ENV.read_text(encoding="utf-8")
    rendered = compose(["config"])
    if not locked(rendered.stdout, env_text):
        sys.exit("production project is not locked")
    try:
        compose(["up", "-d", "--build", "--wait"])
        rows = prove()
    finally:
        compose(["down", "-v"], check=False)
    lines = (
        "docker compose --env-file .env.production -p paperpilot-production -f compose.yaml -f compose.production.yaml up -d --build --wait",
        "docker compose --env-file .env.production -p paperpilot-production -f compose.yaml -f compose.production.yaml down -v",
        *rows,
        "volume: paperpilot-production-pgdata",
        "host: none selected",
        "tls: none",
        "firewall: none",
        "password: none",
        "administrators: none",
        "research: unreviewed",
        "production ok",
    )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Production security\n\n"
        "The production project is local. Postgres has no host port. "
        "The docs routes are hidden. No host is selected.\n\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )
    print("production ok")


if __name__ == "__main__":
    main()
