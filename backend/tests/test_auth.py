import time
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.auth import decode_access_token

def _jwks_for(private_key, kid="test-key"):
    public = private_key.public_key().public_numbers()
    e = public.e.to_bytes(3, "big")
    n = public.n.to_bytes((public.n.bit_length() + 7) // 8, "big")
    def b64(raw: bytes) -> str:
        import base64
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    return {"keys": [{"kty": "RSA", "kid": kid, "use": "sig", "alg": "RS256", "n": b64(n), "e": b64(e)}]}

def test_decode_returns_sub():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    user_id = str(uuid4())
    token = jwt.encode(
        {"sub": user_id, "aud": "authenticated", "exp": int(time.time()) + 60},
        key, algorithm="RS256", headers={"kid": "test-key"},
    )
    assert str(decode_access_token(token, _jwks_for(key))) == user_id

def test_decode_rejects_other_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(
        {"sub": str(uuid4()), "aud": "authenticated", "exp": int(time.time()) + 60},
        other, algorithm="RS256", headers={"kid": "test-key"},
    )
    with pytest.raises(HTTPException) as caught:
        decode_access_token(token, _jwks_for(key))
    assert caught.value.status_code == 401

def test_missing_header_is_401():
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from app.auth import current_user_id
    from app.main import http_exception_handler

    application = FastAPI()
    application.add_exception_handler(HTTPException, http_exception_handler)

    @application.get("/who")
    async def who():
        return {"id": str(await current_user_id(authorization=None))}

    response = TestClient(application).get("/who")
    assert response.status_code == 401
    assert response.json() == {"code": "unauthorized", "message": "Sign in again."}