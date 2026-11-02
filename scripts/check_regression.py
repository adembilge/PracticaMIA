"""Run the RAG regression pin. A drift fails. No database."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / "backend" / ".venv"
PYTHON = VENV / "Scripts" / "python.exe" if sys.platform == "win32" else VENV / "bin" / "python"
if PYTHON.is_file() and Path(sys.executable).resolve() != PYTHON.resolve():
    raise SystemExit(subprocess.call([str(PYTHON), *sys.argv]))

REPORT = ROOT / "docs" / "testing" / "REGRESSION.md"


def main():
    sys.path.insert(0, str(ROOT / "evaluation"))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(ROOT / "evaluation" / "test_regression.py"),
            "-q",
            "--import-mode=importlib",
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    from regression import load

    pinned = load()
    lines = (
        "version: %s" % pinned["version"],
        "retrieval held",
        "rules held",
        "embedding held",
        "metadata held",
        "research: unreviewed",
        "regression ok",
    )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# RAG regression\n\n"
        "Version %s is the pin. A changed citation, embedding, review status, "
        "or rule result fails the check. Research rows stay unreviewed.\n\n"
        % pinned["version"]
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )
    print("regression ok")


if __name__ == "__main__":
    main()
