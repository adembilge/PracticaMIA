"""Run the dashboard checks. No database."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    result = subprocess.run(
        ["node", "--experimental-strip-types", "--test", str(ROOT / "frontend" / "test" / "dashboard.test.mjs")],
        cwd=ROOT,
    )
    if result.returncode != 0:
        sys.exit(result.returncode)
    print("dashboard ok")


if __name__ == "__main__":
    main()
