"""Run the shell checks. No database."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    result = subprocess.run(
        ["node", "--experimental-strip-types", "--test", str(ROOT / "frontend" / "test" / "shell.test.mjs")],
        cwd=ROOT,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    print("shell ok")


if __name__ == "__main__":
    main()
