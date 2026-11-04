"""Signed, local-only identity fixtures; isolated SQLite database per API test."""
from datetime import datetime, timedelta, timezone
import json

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt import PyJWKClient

from app.cases import model  # noqa: F401 - register SQLAlchemy models
from app.config import Settings
from app.database import Base
from app.main import create_app

ISSUER = "https://identity.example.test/"
AUDIENCE = "https://api.practicamia.example.test"
JWKS_URL = "https://identity.example.test/.well-known/jwks.json"


@pytest.fixture
def token_factory(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk["kid"] = "unit-test-rsa-key"

    # Exercise real JWT signature/claim verification without contacting a provider.
    monkeypatch.setattr(PyJWKClient, "fetch_data", lambda self: {"keys": [jwk]})

    def issue(subject="alice", overrides=None, signing_key=None, algorithm="RS256"):
        now = datetime.now(timezone.utc)
        claims = {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": subject,
            "iat": now,
            "exp": now + timedelta(minutes=5),
        }
        if overrides:
            claims.update(overrides)
        key = private_key if signing_key is None else signing_key
        return jwt.encode(
            claims,
            key,
            algorithm=algorithm,
            headers={"kid": "unit-test-rsa-key"},
        )

    return issue


@pytest.fixture
def auth_headers(token_factory):
    def headers(subject="alice", overrides=None):
        return {"Authorization": f"Bearer {token_factory(subject, overrides)}"}

    return headers


@pytest.fixture
def client(tmp_path, token_factory):
    db_url = f"sqlite+pysqlite:///{tmp_path / 'cases.sqlite3'}"
    api = create_app(
        Settings(
            database_url=db_url,
            enable_demo_case_api=True,
            enable_knowledge_catalog_api=True,
            auth_issuer=ISSUER,
            auth_audience=AUDIENCE,
            auth_jwks_url=JWKS_URL,
        )
    )
    Base.metadata.create_all(api.state.engine)
    with TestClient(api) as http:
        yield http
    api.state.engine.dispose()
