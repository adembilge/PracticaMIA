"""Prove one supported case on staging, then remove the volume."""
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))

REPORT = ROOT / "docs" / "testing" / "DEPLOY.md"
ENV = ROOT / ".env.staging"
PROJECT = "paperpilot-staging"
API = "http://127.0.0.1:8001"
VOLUME = "paperpilot-staging_paperpilot-staging-pgdata"
S01 = (
    "I'm a Turkish citizen living in Milan. I was registered at Via Padova 10. "
    "Last week I moved to a new apartment at Via Torino 20, Milano. The lease is in my name. "
    "I have SPID, my passport, and a valid permesso di soggiorno. Help me update my registered address."
)


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


def migrate():
    env = os.environ.copy()
    env["PAPERPILOT_DB_PORT"] = "5433"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT / "backend",
        env=env,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)


def opened():
    request = urllib.request.Request(
        API + "/v1/onboarding",
        data=json.dumps({"messages": [S01]}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        body = json.loads(response.read().decode())
        if response.status != 200 or body["case"]["stop"] != "not ready":
            sys.exit("case was not saved")
    return "case: not ready"


def volume_gone():
    listed = subprocess.run(
        ["docker", "volume", "ls", "-q"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if listed.returncode != 0 or VOLUME in listed.stdout.split():
        sys.exit("volume remains")


def main():
    if not daemon_up():
        sys.exit("docker is not running")
    try:
        compose(["up", "-d", "--wait"])
        migrate()
        case = opened()
        backup = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_backup.py")])
        if backup.returncode != 0:
            sys.exit(backup.returncode)
    finally:
        compose(["down", "-v"], check=False)
    volume_gone()
    lines = (
        case,
        "backup ok",
        "tls: none",
        "host: none selected",
        "rollback: volume removed",
        "deploy ok",
    )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Staging deployment\n\n"
        "One supported case is saved on the local staging project. "
        "The volume is removed afterward. No host is selected.\n\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )
    print("deploy ok")


if __name__ == "__main__":
    main()
