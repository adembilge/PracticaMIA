"""Configurable embedding provider. The default stays on this machine."""
import hashlib
import os
import re

DIM = 32


def embed(text):
    provider = os.environ.get("PAPERPILOT_EMBEDDING", "local")
    if provider != "local":
        raise ValueError("unknown embedding provider: %s" % provider)
    return _local(text)


def _local(text):
    # shortcut: overlap hashes, not a semantic model, upgrade when retrieval quality is measured
    vector = [0.0] * DIM
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        digest = hashlib.sha256(token.encode()).digest()
        bucket = int.from_bytes(digest[:4], "big") % DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign
    norm = sum(value * value for value in vector) ** 0.5
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]
