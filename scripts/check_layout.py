"""Check the repository roots and the session links."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOTS = ("backend", "frontend", "database", "evaluation", "scripts", "docs")
FILES = (
    ROOT / "backend" / "README.md",
    ROOT / "frontend" / "README.md",
    ROOT / "database" / "README.md",
    ROOT / "evaluation" / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "docs" / "PROGRESS.md",
    ROOT / "docs" / "DECISIONS.md",
)
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def main():
    missing = [name for name in ROOTS if not (ROOT / name).is_dir()]
    if missing:
        sys.exit("missing roots: " + ", ".join(missing))
    broken = []
    for path in FILES:
        if not path.is_file():
            broken.append(str(path.relative_to(ROOT)))
            continue
        text = path.read_text(encoding="utf-8")
        for match in LINK.finditer(text):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://")):
                continue
            target = target.split("#", 1)[0].strip()
            if not target:
                continue
            if not (path.parent / target).is_file():
                broken.append("%s -> %s" % (path.relative_to(ROOT), match.group(1)))
    if broken:
        sys.exit("broken links: " + "; ".join(broken))
    print("layout ok")


if __name__ == "__main__":
    main()
