"""Verify an external human-review signature before activating a rule catalog.

The private signing key is never present in the app; only a 32-byte Ed25519
public verification key may be supplied via PREPARATION_RULE_REVIEW_PUBLIC_KEY.
Approving a catalog also still requires separately approved current sources.
"""
import base64
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature


def canonical_approval_payload(catalog: dict) -> bytes:
    stripped = {key: value for key, value in catalog.items() if key != "review_signature"}
    return json.dumps(
        stripped, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def has_valid_human_review_signature(catalog: dict, public_key_base64: str) -> bool:
    if catalog.get("status") != "active" or not public_key_base64:
        return False
    try:
        pubkey = base64.b64decode(public_key_base64, validate=True)
        signature = base64.b64decode(catalog["review_signature"], validate=True)
        if len(pubkey) != 32 or len(signature) != 64:
            return False
        Ed25519PublicKey.from_public_bytes(pubkey).verify(
            signature, canonical_approval_payload(catalog),
        )
        return True
    except (ValueError, KeyError, TypeError, InvalidSignature):
        return False
