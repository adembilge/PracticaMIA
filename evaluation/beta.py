"""Empty beta records. A sentence, a path, or a password is refused."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "beta.json"
LISTS = ("people", "feedback", "issues")
LABELS = (
    "design: unapproved",
    "security: unreviewed",
    "research: unreviewed",
    "host: none selected",
)


def load(path=FIXTURE):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _clean(item):
    text = item if isinstance(item, str) else json.dumps(item)
    if "password" in text.lower() or "/" in text or "\\" in text or " " in text:
        raise ValueError("refused")


def report(data):
    lines = []
    filled = []
    for name in LISTS:
        rows = data[name]
        for item in rows:
            _clean(item)
        if rows:
            filled.append(name)
        else:
            lines.append(name + ": none")
    lines.extend(LABELS)
    if filled:
        lines.append("filled: " + ", ".join(filled))
        return lines
    lines.append("beta held")
    return lines
