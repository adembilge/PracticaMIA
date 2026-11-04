"""Verify signed API access tokens using a configured, trusted JWKS.

The server accepts only RS256. Issuer, audience and required time claims are
validated; the unverified JWT header never chooses an algorithm or JWKS URL.
"""
from dataclasses import dataclass
from urllib.parse import urlparse

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError, PyJWKClientError

from app.config import Settings

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    subject: str


class TokenVerifier:
    def __init__(self, settings: Settings):
        for name in ("auth_issuer", "auth_audience", "auth_jwks_url"):
            if not getattr(settings, name):
                raise ValueError(f"{name.upper()} must be configured for case API access")
        for name in ("auth_issuer", "auth_jwks_url"):
            url = urlparse(getattr(settings, name))
            if url.scheme != "https" or not url.netloc or url.username or url.password:
                raise ValueError(f"{name.upper()} must use a trusted HTTPS URL")
        self.issuer = settings.auth_issuer
        self.audience = settings.auth_audience
        # JWK sets are cached; keys are resolved by kid with automatic refresh.
        self.jwks = PyJWKClient(settings.auth_jwks_url, timeout=5, lifespan=300)

    def verify(self, encoded: str) -> Principal:
        if len(encoded) > 8192:
            raise jwt.InvalidTokenError("Token exceeds size limit")
        signing_key = self.jwks.get_signing_key_from_jwt(encoded)
        claims = jwt.decode(
            encoded,
            signing_key.key,
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.issuer,
            options={"require": ["sub", "iss", "aud", "iat", "exp"]},
        )
        subject = claims["sub"]
        if not isinstance(subject, str) or not subject.strip() or len(subject) > 255:
            raise jwt.InvalidTokenError("Invalid subject claim")
        return Principal(subject=subject)


def get_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    challenge = {"WWW-Authenticate": "Bearer"}
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Authentication required", headers=challenge)
    try:
        return request.app.state.token_verifier.verify(credentials.credentials)
    except (PyJWTError, PyJWKClientError, ValueError, TypeError):
        raise HTTPException(401, "Invalid access token", headers=challenge) from None
