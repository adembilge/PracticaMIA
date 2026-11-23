"""Fail-closed cryptographic primitives for disposable M3 migration tests.

The helpers deliberately accept explicit source and destination AAD. They do
not read environment variables, retrieve secrets, open databases, or mutate
application records.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
from os import urandom
import re
from typing import Callable, Mapping

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import text
from sqlalchemy.engine import Connection


AAD_V2_DOMAIN = "practicamia-task-payload/v2"
PAYLOAD_KINDS = frozenset({
    "agent_message",
    "agent_event",
    "agent_checkpoint",
    "preparation_facts",
    "preparation_document",
    "preparation_review",
    "guide_turn",
    "private_document",
    "private_document_review",
})
_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class MigrationQuarantine(ValueError):
    """Safe, non-sensitive failure category for a row that cannot be migrated."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ReencryptedPayload:
    ciphertext: bytes
    plaintext_sha256: str
    source_ciphertext_sha256: str
    destination_ciphertext_sha256: str


def validate_key_families(keys: Mapping[str, bytes]) -> None:
    """Require 256-bit, pairwise-distinct active keys without emitting fingerprints."""
    if not keys:
        raise ValueError("At least one active key family is required")
    values = list(keys.values())
    if any(not isinstance(value, bytes) or len(value) != 32 for value in values):
        raise ValueError("Every active key family must contain a 256-bit key")
    for index, value in enumerate(values):
        if any(hmac.compare_digest(value, other) for other in values[index + 1:]):
            raise ValueError("Active key families must be pairwise distinct")


def source_agent_message_aad(
    *, owner_subject: str, thread_id: str, run_id: str,
    client_message_id: str, case_id: str | None, accepted_revision: int,
) -> bytes:
    return json.dumps(
        [
            "practicamia-agent-request/v1", owner_subject, thread_id,
            run_id, client_message_id, case_id, accepted_revision,
        ],
        separators=(",", ":"),
    ).encode()


def source_agent_event_aad(
    *, owner_subject: str, thread_id: str, run_id: str,
    case_id: str | None, event_sequence: int,
) -> bytes:
    return json.dumps(
        [
            "practicamia-agent-event/v1", owner_subject, thread_id,
            run_id, case_id, event_sequence,
        ],
        separators=(",", ":"),
    ).encode()


def source_agent_checkpoint_aad(
    *, owner_subject: str, thread_id: str, run_id: str,
    case_id: str | None, revision: int, event_watermark: int,
) -> bytes:
    return json.dumps(
        [
            "practicamia-agent-checkpoint/v1", owner_subject, thread_id,
            run_id, case_id, revision, event_watermark,
        ],
        separators=(",", ":"),
    ).encode()


def source_preparation_aad(*, case_id: str, owner_subject: str, record_identity: str) -> bytes:
    return (
        f"practicamia-preview-document/v1:{case_id}:{owner_subject}:{record_identity}"
    ).encode("utf-8")


def source_private_document_aad(*, case_id: str, owner_subject: str, document_identity: str) -> bytes:
    return (
        f"practicamia:private-document:v1:{case_id}:{owner_subject}:{document_identity}"
    ).encode("utf-8")


def destination_aad_v2(
    *,
    payload_kind: str,
    owner_subject: str,
    conversation_id: str,
    task_id: str | None,
    record_id: str,
    purpose: str,
    sequence: int | None = None,
    revision: int | None = None,
    event_watermark: int | None = None,
) -> bytes:
    """Build the frozen, canonical UTF-8 AAD v2 tuple for one payload identity."""
    if payload_kind not in PAYLOAD_KINDS:
        raise ValueError("Unsupported payload kind")
    if not owner_subject or not conversation_id or not record_id or not purpose:
        raise ValueError("AAD identity fields must be non-empty")
    if task_id is not None and not task_id:
        raise ValueError("A non-null task identity must be non-empty")
    for value in (sequence, revision, event_watermark):
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("AAD sequence and revision fields must be non-negative integers")
    if payload_kind == "agent_message" and revision is None:
        raise ValueError("Agent messages require an accepted revision")
    if payload_kind == "agent_event" and sequence is None:
        raise ValueError("Agent events require an event sequence")
    if payload_kind == "agent_checkpoint" and (revision is None or event_watermark is None):
        raise ValueError("Agent checkpoints require revision and event watermark")
    return json.dumps(
        [
            AAD_V2_DOMAIN,
            payload_kind,
            owner_subject,
            conversation_id,
            task_id,
            record_id,
            purpose,
            sequence,
            revision,
            event_watermark,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def reencrypt_payload(
    source_ciphertext: bytes | None,
    *,
    source_key: bytes,
    destination_key: bytes,
    source_aad: bytes,
    destination_aad: bytes,
    expected_plaintext_sha256: str | None = None,
    validate_plaintext: Callable[[bytes], None] | None = None,
    allow_empty: bool = False,
) -> ReencryptedPayload | None:
    """Authenticate, validate, re-encrypt with a fresh nonce, then verify destination.

    Empty optional review payloads remain empty. A missing value remains missing.
    All failure messages are safe categories; plaintext, keys and AAD are omitted.
    """
    if source_ciphertext is None:
        return None
    if source_ciphertext == b"" and allow_empty:
        return ReencryptedPayload(b"", sha256(b"").hexdigest(), sha256(b"").hexdigest(), sha256(b"").hexdigest())
    if len(source_key) != 32 or len(destination_key) != 32:
        raise MigrationQuarantine("invalid_key_material")
    if len(source_ciphertext) < 29:
        raise MigrationQuarantine("invalid_source_ciphertext_length")
    try:
        plaintext = AESGCM(source_key).decrypt(
            source_ciphertext[:12], source_ciphertext[12:], source_aad,
        )
    except InvalidTag:
        raise MigrationQuarantine("source_authentication_failed") from None
    except Exception:
        raise MigrationQuarantine("source_decryption_failed") from None

    plain_digest = sha256(plaintext).hexdigest()
    if expected_plaintext_sha256 is not None and not hmac.compare_digest(
        plain_digest, expected_plaintext_sha256,
    ):
        raise MigrationQuarantine("source_plaintext_digest_mismatch")
    if validate_plaintext is not None:
        try:
            validate_plaintext(plaintext)
        except Exception:
            raise MigrationQuarantine("source_payload_validation_failed") from None

    nonce = urandom(12)
    destination_ciphertext = nonce + AESGCM(destination_key).encrypt(
        nonce, plaintext, destination_aad,
    )
    try:
        verified = AESGCM(destination_key).decrypt(
            destination_ciphertext[:12], destination_ciphertext[12:], destination_aad,
        )
    except InvalidTag:
        raise MigrationQuarantine("destination_authentication_failed") from None
    if not hmac.compare_digest(verified, plaintext):
        raise MigrationQuarantine("destination_semantic_verification_failed")

    return ReencryptedPayload(
        ciphertext=destination_ciphertext,
        plaintext_sha256=plain_digest,
        source_ciphertext_sha256=sha256(source_ciphertext).hexdigest(),
        destination_ciphertext_sha256=sha256(destination_ciphertext).hexdigest(),
    )


def validate_task_child_owner(*, task_owner: str | None, child_owner: str) -> None:
    if task_owner is None:
        raise MigrationQuarantine("ownerless_task")
    if not task_owner or child_owner != task_owner:
        raise MigrationQuarantine("task_child_owner_mismatch")


def validate_conversation_task_owner(*, conversation_owner: str, task_owner: str | None) -> None:
    if task_owner is None:
        raise MigrationQuarantine("ownerless_linked_task")
    if not conversation_owner or conversation_owner != task_owner:
        raise MigrationQuarantine("conversation_task_owner_mismatch")


def validate_run_task_link(
    *,
    task_id: str | None,
    conversation_task_ids: set[str],
) -> str | None:
    """Preserve null as a first-class unlinked-chat state; reject unproven links."""
    if task_id is None:
        return None
    if task_id not in conversation_task_ids:
        raise MigrationQuarantine("run_task_association_missing")
    return task_id


def is_expired(*, expires_at, now) -> bool:
    """Evaluate the existing expiry deadline without extending or normalizing it."""
    if expires_at.tzinfo is None or now.tzinfo is None:
        raise ValueError("Retention timestamps must be timezone-aware")
    return expires_at <= now


def _qualified_table(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError("Invalid harness table identifier")
    return ".".join(f'"{part}"' for part in value.split("."))


def _verified(ciphertext: bytes, verifier: Callable[[bytes], bool]) -> bool:
    try:
        return verifier(ciphertext) is True
    except Exception:
        return False


def stage_verified_record(
    connection: Connection,
    *,
    target_table: str,
    ledger_table: str,
    source_id: str,
    target_id: str,
    ciphertext: bytes,
    source_ciphertext_sha256: str,
    aad_version: str,
    verify_existing: Callable[[bytes], bool],
) -> str:
    """Atomically stage one verified target and its minimal idempotency ledger row.

    The caller owns the transaction. Target and ledger tables must be disposable
    harness tables with the documented columns; this function is not wired to
    application tables or the runtime database.
    """
    target = _qualified_table(target_table)
    ledger = _qualified_table(ledger_table)
    if not _SHA256.fullmatch(source_ciphertext_sha256):
        raise MigrationQuarantine("invalid_source_ciphertext_digest")
    if aad_version != "v2":
        raise MigrationQuarantine("unsupported_destination_aad_version")
    existing = connection.execute(
        text(
            f"SELECT target_id, source_ciphertext_sha256, target_ciphertext_sha256, aad_version, status "
            f"FROM {ledger} WHERE source_id=:source_id"
        ),
        {"source_id": source_id},
    ).mappings().one_or_none()
    if existing is not None:
        if (
            existing["status"] != "verified"
            or existing["target_id"] != target_id
            or existing["source_ciphertext_sha256"] != source_ciphertext_sha256
            or existing["aad_version"] != aad_version
        ):
            raise MigrationQuarantine("ledger_reconciliation_required")
        target_digest = existing["target_ciphertext_sha256"]
        row = connection.execute(
            text(f"SELECT ciphertext, content_sha256 FROM {target} WHERE id=:target_id"),
            {"target_id": target_id},
        ).mappings().one_or_none()
        if (
            row is None
            or row["content_sha256"] != target_digest
            or not hmac.compare_digest(sha256(row["ciphertext"]).hexdigest(), target_digest)
            or not _verified(row["ciphertext"], verify_existing)
        ):
            raise MigrationQuarantine("verified_target_revalidation_failed")
        connection.execute(
            text(f"UPDATE {ledger} SET attempt_count=attempt_count+1 WHERE source_id=:source_id"),
            {"source_id": source_id},
        )
        return "already_verified"

    if not _verified(ciphertext, verify_existing):
        raise MigrationQuarantine("target_payload_verification_failed")
    target_digest = sha256(ciphertext).hexdigest()
    existing_target = connection.execute(
        text(f"SELECT id FROM {target} WHERE id=:target_id"),
        {"target_id": target_id},
    ).first()
    if existing_target is not None:
        raise MigrationQuarantine("target_without_verified_ledger")

    connection.execute(
        text(f"INSERT INTO {target} (id, ciphertext, content_sha256) VALUES (:id, :ciphertext, :digest)"),
        {"id": target_id, "ciphertext": ciphertext, "digest": target_digest},
    )
    connection.execute(
        text(
            f"INSERT INTO {ledger} "
            "(source_id, target_id, source_ciphertext_sha256, target_ciphertext_sha256, aad_version, status, attempt_count) "
            "VALUES (:source_id, :target_id, :source_digest, :target_digest, :aad_version, 'verified', 1)"
        ),
        {
            "source_id": source_id,
            "target_id": target_id,
            "source_digest": source_ciphertext_sha256,
            "target_digest": target_digest,
            "aad_version": aad_version,
        },
    )
    return "staged"
