"""Send one local file to the source passage route."""
import os
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import httpx

from auth import COOKIE
from ingest import run


def _post(document_id, version_id, passages):
    base = os.environ.get("PAPERPILOT_API", "http://127.0.0.1:8000").rstrip("/")
    url = "%s/v1/source/%s/version/%s/passages" % (
        base,
        quote(document_id, safe=""),
        quote(version_id, safe=""),
    )
    cookie = os.environ.get("PAPERPILOT_SESSION", "")
    try:
        response = httpx.post(
            url,
            json={"passages": passages},
            cookies={COOKIE: cookie} if cookie else {},
            timeout=30.0,
        )
    except httpx.HTTPError:
        return 1
    return response.status_code


def main(argv):
    if len(argv) != 4:
        return 2
    return run(argv[3], argv[1], argv[2], _post)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
