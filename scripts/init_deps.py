"""Install the pinned dependencies and run the package scripts."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"


def run(cmd, cwd=None):
    subprocess.check_call(cmd, cwd=cwd)


def main():
    if not PYTHON.is_file():
        run([sys.executable, "-m", "venv", str(VENV)])
    run([
        str(PYTHON), "-m", "pip", "install",
        "-r", str(ROOT / "backend" / "requirements.txt"),
        "-r", str(ROOT / "backend" / "requirements-dev.txt"),
    ])
    npm_name = "npm.cmd" if sys.platform == "win32" else "npm"
    npm = shutil.which(npm_name)
    if npm is None:
        sys.exit("npm is missing")
    frontend = ROOT / "frontend"
    run([npm, "ci"], cwd=frontend)
    run([str(PYTHON), "-c", "import fastapi, langgraph, sqlalchemy, psycopg, pgvector"])
    run([str(PYTHON), "-m", "pytest", "--version"])
    run([npm, "run", "versions"], cwd=frontend)
    print("deps ok")


if __name__ == "__main__":
    main()
