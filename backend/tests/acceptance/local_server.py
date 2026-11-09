"""Localhost-only synthetic browser acceptance bridge.

Serves the real compiled React UI and forwards browser /api requests into the
actual FastAPI application using independently signed, short-lived RS256 test
tokens. Only the Auth0 browser session/BFF is replaced by this CI harness;
the backend verifies JWT issuer, signature, audience, and owner permissions.

This is NEVER a production route, mock login, production data import or a
Vercel deployment. Source evidence is an explicit synthetic *resolver*
fixture; separate integration tests verify actual source snapshots/reviews.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
from threading import RLock
from types import SimpleNamespace
from urllib.parse import urlsplit

# The standalone script is launched from backend/ but lives in tests/.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt import PyJWKClient
from sqlalchemy.engine import make_url

from app.cases import checklist_service
from app.config import Settings
from app.main import create_app

HOST = "127.0.0.1"
ISSUER = "https://acceptance-identity.invalid/"
AUDIENCE = "https://acceptance-api.invalid/"
JWKS_URL = ISSUER + ".well-known/jwks.json"
LOCK = RLock()
STATE = {"approved": True, "review_date": "2026-11-08"}


def validate_environment() -> str:
    if os.environ.get("PRACTICAMIA_E2E_LOCAL_ONLY") != "1":
        raise SystemExit("Explicit synthetic localhost acceptance opt-in required")
    value = os.environ.get("PRACTICAMIA_ACCEPTANCE_DATABASE_URL", "")
    url = make_url(value)
    if (url.drivername != "postgresql+psycopg" or
            url.host not in {"localhost", "127.0.0.1"} or
            url.database != "practicamia_acceptance"):
        raise SystemExit("Refusing non-local/non-disposable acceptance database")
    return value


def synthetic_evidence(_db, *, citation_id, jurisdiction, procedure_id, language):
    with LOCK:
        approved = STATE["approved"]
        review_date = STATE["review_date"]
    if not approved or jurisdiction != "IT-MI-MILANO" or (
        procedure_id != "milan_residence_change" or language != "it"
    ):
        return None
    source = next(
        (name for name, details in checklist_service.PINNED_SOURCE_VERSIONS.items()
         if citation_id.startswith(details[0] + ":")),
        None,
    )
    if not source:
        return None
    version, official_url, _archived = checklist_service.PINNED_SOURCE_VERSIONS[source]
    return SimpleNamespace(
        citation_id=citation_id, source_id=source, source_version_id=version,
        official_url=official_url,
        title="Synthetic reviewed source fixture",
        institution="Local CI acceptance fixture",
        reviewed_at=datetime.fromisoformat(review_date).replace(tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )


def run(port: int, assets: Path):
    database_url = validate_environment()
    if not assets.is_dir() or not (assets / "acceptance.js").is_file():
        raise SystemExit("Compiled browser acceptance assets missing")

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk["kid"] = "acceptance-rs256-ephemeral"
    original_jwks = PyJWKClient.fetch_data
    original_resolver = checklist_service.resolve_approved_passage
    PyJWKClient.fetch_data = lambda self: {"keys": [public_jwk]}
    checklist_service.resolve_approved_passage = synthetic_evidence

    settings = Settings(
        database_url=database_url, enable_demo_case_api=True,
        enable_knowledge_catalog_api=True,
        auth_issuer=ISSUER, auth_audience=AUDIENCE, auth_jwks_url=JWKS_URL,
    )
    api = create_app(settings)
    client = TestClient(api)
    client.__enter__()

    def token(subject: str) -> str:
        now = datetime.now(timezone.utc)
        return jwt.encode({
            "iss": ISSUER, "aud": AUDIENCE, "sub": subject,
            "iat": now, "exp": now + timedelta(minutes=10),
        }, private_key, algorithm="RS256", headers={"kid": public_jwk["kid"]})

    tokens = {subject: token(subject) for subject in ("alice", "bob")}

    class Handler(BaseHTTPRequestHandler):
        server_version = "PracticaMIA-Acceptance-Only"

        def log_message(self, format, *args):
            # Do not log request bodies, credentials or document information.
            if os.environ.get("PRACTICAMIA_ACCEPTANCE_VERBOSE") == "1":
                print("ACCEPTANCE_HTTP " + format % args, flush=True)

        def reply(self, code, data: bytes, media: str, extra=None):
            self.send_response(code)
            self.send_header("Content-Type", media)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(data)))
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(data)

        def json_reply(self, code, obj):
            self.reply(code, json.dumps(obj).encode(), "application/json")

        def subject(self):
            cookie = SimpleCookie()
            try:
                cookie.load(self.headers.get("Cookie", ""))
                subject = cookie["acceptance_subject"].value
            except (KeyError, ValueError):
                return None
            return subject if subject in tokens else None

        def handle_request(self):
            path = urlsplit(self.path).path
            if path == "/__acceptance/health":
                self.json_reply(200, {"status": "ready", "synthetic": True})
                return
            if path in {
                "/__acceptance/sources/revoke", "/__acceptance/sources/restore",
            }:
                if self.command != "POST" or self.subject() != "alice":
                    self.json_reply(403, {"error": "Synthetic owner control only"})
                    return
                with LOCK:
                    STATE["approved"] = path.endswith("restore")
                    if STATE["approved"]:
                        STATE["review_date"] = "2026-11-09"
                self.json_reply(200, {"approved": STATE["approved"]})
                return

            if path == "/acceptance.js" and self.command == "GET":
                self.reply(200, (assets / "acceptance.js").read_bytes(),
                           "text/javascript; charset=utf-8")
                return
            if path == "/acceptance.css" and self.command == "GET":
                css = Path(__file__).resolve().parents[3] / (
                    "frontend/src/app/globals.css"
                )
                self.reply(200, css.read_bytes(), "text/css; charset=utf-8")
                return
            if (path in {"/", "/cases/saved"} or
                (path.startswith("/cases/") and len(path) < 120)) and (
                self.command == "GET"
            ):
                self.reply(200, (assets / "index.html").read_bytes(),
                           "text/html; charset=utf-8")
                return
            if path.startswith("/api/cases") or path.startswith("/api/knowledge"):
                self.forward_api()
                return
            self.json_reply(404, {"error": "Local acceptance route not found"})

        def forward_api(self):
            mapped = "/api/v1" + self.path[4:]
            subject = self.subject()
            headers = {}
            if subject:
                headers["Authorization"] = "Bearer " + tokens[subject]
            media = self.headers.get("Content-Type")
            if media:
                headers["Content-Type"] = media
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 2_100_000:
                self.json_reply(413, {"error": "Request too large"})
                return
            body = self.rfile.read(length) if length else None
            try:
                with LOCK:
                    response = client.request(
                        self.command, mapped, headers=headers, content=body,
                    )
                forward_headers = {
                    "Cache-Control": "private, no-store",
                }
                if response.headers.get("content-disposition"):
                    forward_headers["Content-Disposition"] = response.headers[
                        "content-disposition"
                    ]
                self.reply(
                    response.status_code, response.content,
                    response.headers.get("content-type", "application/json"),
                    forward_headers,
                )
            except Exception:
                # Fail closed, and do not expose Python exception text in response.
                self.json_reply(502, {"error": "Acceptance backend unavailable"})

        def do_GET(self):
            self.handle_request()

        def do_POST(self):
            self.handle_request()

        def do_PUT(self):
            self.handle_request()

        def do_PATCH(self):
            self.handle_request()

        def do_DELETE(self):
            self.handle_request()

    try:
        server = ThreadingHTTPServer((HOST, port), Handler)
        print(f"ACCEPTANCE_READY http://{HOST}:{server.server_port}", flush=True)
        server.serve_forever(poll_interval=0.15)
    finally:
        client.__exit__(None, None, None)
        api.state.engine.dispose()
        PyJWKClient.fetch_data = original_jwks
        checklist_service.resolve_approved_passage = original_resolver


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--assets", type=Path, required=True)
    args = parser.parse_args()
    run(args.port, args.assets.resolve())
