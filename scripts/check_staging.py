"""Start the staging project, prove health, and remove its volume."""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "testing" / "STAGING.md"
ENV = ROOT / ".env.staging"
PROJECT = "paperpilot-staging"
API = "http://127.0.0.1:8001"


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


def isolated(text):
    return (
        "source: paperpilot-staging-pgdata" in text
        and "source: paperpilot-pgdata" not in text
    )


def health():
    rows = []
    for path in ("/health", "/v1/health"):
        with urllib.request.urlopen(API + path) as response:
            body = json.loads(response.read().decode())
            if response.status != 200 or body != {"status": "ok"}:
                sys.exit(path)
        rows.append(path + " ok")
    return rows


def main():
    if not daemon_up():
        sys.exit("docker is not running")
    rendered = compose(["config"])
    if not isolated(rendered.stdout):
        sys.exit("staging volume is not isolated")
    try:
        compose(["up", "-d", "--wait"])
        rows = health()
    finally:
        compose(["down", "-v"], check=False)
    lines = (
        "docker compose --env-file .env.staging -p paperpilot-staging up -d --wait",
        "docker compose --env-file .env.staging -p paperpilot-staging down -v",
        *rows,
        "volume: paperpilot-staging-pgdata",
        "host: none selected",
        "web: not in this compose",
        "research: unreviewed",
        "staging ok",
    )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Staging\n\n"
        "The staging project is local. It does not use the development volume. "
        "No host is selected.\n\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )
    print("staging ok")


if __name__ == "__main__":
    main()
