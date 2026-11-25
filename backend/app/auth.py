import time
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWK

from app.config import get_settings

_CACHE: dict[str, tuple[float, dict]] = {}
UNAUTHORIZED = HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Sign in again."})


def _jwks() -> dict:
    import httpx
    settings = get_settings()
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    cached = _CACHE.get(url)
    now = time.time()
    if cached and now - cached[0] < 600:
        return cached[1]
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    payload = response.json()
    _CACHE[url] = (now, payload)
    return payload


def decode_access_token(token: str, jwks: dict) -> UUID:
    try:
        header = jwt.get_unverified_header(token)
        keys = [item for item in jwks["keys"] if item.get("kid") == header.get("kid")]
        if not keys:
            raise UNAUTHORIZED
        key = PyJWK.from_dict(keys[0]).key
        payload = jwt.decode(token, key, algorithms=[keys[0].get("alg", "RS256")], audience="authenticated")
        return UUID(payload["sub"])
    except HTTPException:
        raise
    except Exception as exc:
        raise UNAUTHORIZED from exc


async def current_user_id(authorization: Annotated[str | None, Header()] = None) -> UUID:
    if not authorization or not authorization.startswith("Bearer "):
        raise UNAUTHORIZED
    token = authorization.removeprefix("Bearer ").strip()
    return decode_access_token(token, _jwks())