"""Run scenario 01. The account steps stay blocked. No credential is added."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))

REPORT = ROOT / "CHECK" / "01_RESULT.md"
LINES = [
    "pass: empty person create rejects a password field",
    "pass: one supported story saves not ready",
    "pass: the session cookie reads that case",
    "pass: a cleared cookie gets 401",
    "pass: a password in the story saves nothing",
    "blocked: email registration, no email column",
    "blocked: verification token, none exists",
    "blocked: password sign-in, no password is stored",
    "blocked: five wrong passwords, no password sign-in",
    "blocked: expired token, no verification token",
    "blocked: duplicate email, no email",
    "blocked: XSS on a registration form, no registration form",
    "blocked: idempotent retry of an account, there is no account to retry",
    "blocked: landing page has English and Italian links and no login form",
    "research: unreviewed",
    "rule: the Comune URL is not an accepted rule",
    "pp-s01 blocked",
]


def main():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(ROOT / "backend" / "test_pp_s01.py"), "-q"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    REPORT.write_text(
        "# Scenario 01\n\n"
        "The account steps have no product. The status is BLOCKED.\n\n"
        + "\n".join(LINES)
        + "\n",
        encoding="utf-8",
    )
    print("pp-s01 blocked")


if __name__ == "__main__":
    main()
