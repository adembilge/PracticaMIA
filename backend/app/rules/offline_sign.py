"""Offline human-review signature utility.

This tool does NOT review administrative law or approve source snapshots.
Run only AFTER an authenticated authorized reviewer has inspected current
source versions and confirmed exact completeness of the narrow procedure.
The Ed25519 private key never leaves the reviewer's own trusted machine.

From backend/:
    python -m app.rules.offline_sign --catalog app/rules/catalog.json \
        --private-key /private/path/reviewer_ed25519.pem \
        --output /private/path/signed_catalog.json \
        --public-key-output /private/path/reviewer_public_key.b64
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.rules.approval import (
    canonical_approval_payload,
    has_valid_human_review_signature,
)
from app.rules.engine import JURISDICTION, PROCEDURE, evaluate_rules, load_catalog

# This is deliberately stricter than read-only catalog loading. The proposal
# format is NOT a signable live ruleset (it contains draft-only metadata).
_SIGNABLE_KEYS = {
    "version", "status", "jurisdiction", "procedure_id",
    "approved_by", "approved_at", "complete_scenario_coverage",
    "rules",
}


def check_signable_catalog(catalog: dict) -> None:
    """Structural preflight only; source and legal completeness need human review."""
    if not isinstance(catalog, dict) or set(catalog) != _SIGNABLE_KEYS:
        raise ValueError("Not the exact final catalog contract; remove proposal-only fields")
    if catalog["status"] != "active":
        raise ValueError("The authorized reviewer must finalize status=active first")
    if catalog["jurisdiction"] != JURISDICTION or catalog["procedure_id"] != PROCEDURE:
        raise ValueError("Wrong jurisdiction or procedure")
    if catalog["complete_scenario_coverage"] is not True:
        raise ValueError("Complete narrow-scenario coverage has not been attested")
    reviewer = catalog["approved_by"]
    if (not isinstance(reviewer, str) or not reviewer.strip()
            or "test" in reviewer.lower() or "synthetic" in reviewer.lower()):
        raise ValueError("Record the real authorized reviewer identity")
    approved_at = catalog["approved_at"]
    try:
        dt = datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError("approved_at must be an ISO-8601 timestamp") from exc
    if dt.tzinfo is None:
        raise ValueError("Approved timestamp requires a timezone")

    # The evidence lambda is a *structural-only* placeholder. NEVER use its
    # outcome as proof that official source versions are actually approved.
    inspection = evaluate_rules(catalog, {}, lambda _: True)
    if inspection.decision == "blocked":
        raise ValueError(
            "Invalid catalog structure: " + ",".join(inspection.blocking_issues)
        )


def sign_reviewed_catalog(catalog: dict, key: Ed25519PrivateKey) -> tuple[dict, str]:
    """Sign the exact reviewed catalog; does not assert source approvals."""
    check_signable_catalog(catalog)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("Ed25519 reviewer key required")
    result = deepcopy(catalog)
    result["review_signature"] = base64.b64encode(
        key.sign(canonical_approval_payload(result)),
    ).decode("ascii")
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pub_b64 = base64.b64encode(public).decode("ascii")
    if not has_valid_human_review_signature(result, pub_b64):
        raise ValueError("Local signature verification failed")
    return result, pub_b64


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sign an independently reviewed final ruleset offline",
    )
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--private-key", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--public-key-output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.resolve() == args.catalog.resolve():
        parser.error("Do not overwrite the reviewed input catalog")
    if args.output.resolve() == args.public_key_output.resolve():
        parser.error("Signed catalog and public key must use different paths")
    original = load_catalog(args.catalog.read_text(encoding="utf-8"))
    check_signable_catalog(original)
    private_bytes = args.private_key.read_bytes()
    key = serialization.load_pem_private_key(private_bytes, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("Reviewer key must be Ed25519 PEM")
    signed, public_key_b64 = sign_reviewed_catalog(original, key)

    # Use exclusive creation; reject overwriting existing output or key paths.
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(signed, output, ensure_ascii=False, indent=2)
        output.write("\n")
    with args.public_key_output.open("x", encoding="utf-8") as output:
        output.write(public_key_b64 + "\n")
    print("Offline catalog signature verified. No database or deployment changes made.")
    print("Human approval of every source version is a separate required gate.")


if __name__ == "__main__":
    main()
