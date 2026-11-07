"""Encrypt private synthetic fixture binaries before database persistence.

No plaintext copy is persisted. A 256-bit key must be set in the isolated
preview environment and must never be shared with production.
"""
import base64
from hashlib import sha256
from os import urandom

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def decode_key(encoded: str) -> bytes:
    try:
        key = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("Document key must be a base64-encoded 256-bit key") from exc
    if len(key) != 32:
        raise ValueError("Document key must be a base64-encoded 256-bit key")
    return key


def associated_data(case_id: str, owner_subject: str, document_id: str) -> bytes:
    return (
        f"practicamia-preview-document/v1:{case_id}:{owner_subject}:{document_id}"
    ).encode("utf-8")


def encrypt_blob(raw: bytes, *, key: bytes, case_id: str,
                 owner_subject: str, document_id: str) -> bytes:
    nonce = urandom(12)
    aad = associated_data(case_id, owner_subject, document_id)
    return nonce + AESGCM(key).encrypt(nonce, raw, aad)


def decrypt_blob(encrypted: bytes, *, key: bytes, case_id: str,
                 owner_subject: str, document_id: str, expected_digest: str) -> bytes:
    if len(encrypted) < 29:
        raise ValueError("Encrypted document is corrupted")
    raw = AESGCM(key).decrypt(
        encrypted[:12], encrypted[12:],
        associated_data(case_id, owner_subject, document_id),
    )
    if sha256(raw).hexdigest() != expected_digest:
        raise ValueError("Document checksum mismatch")
    return raw
