"""Pure tests for fail-closed M3 migration primitives; no database or secrets."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.migration_harness.crypto import (
    MigrationQuarantine,
    destination_aad_v2,
    is_expired,
    reencrypt_payload,
    validate_conversation_task_owner,
    validate_key_families,
    validate_run_task_link,
    validate_task_child_owner,
)


def _source_blob(plaintext: bytes, key: bytes, aad: bytes) -> bytes:
    nonce = bytes(range(12))
    return nonce + AESGCM(key).encrypt(nonce, plaintext, aad)


def test_key_preflight_requires_256_bit_pairwise_distinct_families():
    validate_key_families({"agent": bytes(range(32)), "preparation": bytes(range(32, 64))})
    with pytest.raises(ValueError, match="pairwise distinct"):
        validate_key_families({"agent": bytes(range(32)), "private": bytes(range(32))})
    with pytest.raises(ValueError, match="256-bit"):
        validate_key_families({"agent": b"short"})


def test_aad_v2_binds_conversation_task_payload_identity_and_watermarks():
    base = destination_aad_v2(
        payload_kind="agent_checkpoint", owner_subject="owner-fixture",
        conversation_id="conversation-fixture", task_id=None, record_id="run-fixture",
        purpose="checkpoint", revision=3, event_watermark=7,
    )
    linked = destination_aad_v2(
        payload_kind="agent_checkpoint", owner_subject="owner-fixture",
        conversation_id="conversation-fixture", task_id="task-fixture", record_id="run-fixture",
        purpose="checkpoint", revision=3, event_watermark=7,
    )
    changed_watermark = destination_aad_v2(
        payload_kind="agent_checkpoint", owner_subject="owner-fixture",
        conversation_id="conversation-fixture", task_id=None, record_id="run-fixture",
        purpose="checkpoint", revision=3, event_watermark=8,
    )
    assert base != linked
    assert base != changed_watermark
    assert b'"practicamia-task-payload/v2"' in base


def test_reencrypt_authenticates_source_validates_digest_and_verifies_destination():
    source_key, destination_key = bytes(range(32)), bytes(range(32, 64))
    source_aad = b"source-v1-fixture-aad"
    destination_aad = b"destination-v2-fixture-aad"
    plaintext = b'{"fixture":"synthetic"}'
    source = _source_blob(plaintext, source_key, source_aad)
    migrated = reencrypt_payload(
        source, source_key=source_key, destination_key=destination_key,
        source_aad=source_aad, destination_aad=destination_aad,
        expected_plaintext_sha256=sha256(plaintext).hexdigest(),
        validate_plaintext=lambda value: None if value.startswith(b"{") else (_ for _ in ()).throw(ValueError()),
    )
    assert migrated is not None
    assert AESGCM(destination_key).decrypt(
        migrated.ciphertext[:12], migrated.ciphertext[12:], destination_aad,
    ) == plaintext
    assert migrated.plaintext_sha256 == sha256(plaintext).hexdigest()
    assert migrated.source_ciphertext_sha256 == sha256(source).hexdigest()
    assert migrated.destination_ciphertext_sha256 == sha256(migrated.ciphertext).hexdigest()


def test_reencrypt_quarantines_invalid_tag_wrong_aad_and_digest_mismatch():
    key_a, key_b = bytes(range(32)), bytes(range(32, 64))
    source = _source_blob(b"payload", key_a, b"right-aad")
    args = dict(source_key=key_a, destination_key=key_b, destination_aad=b"target-aad")
    with pytest.raises(MigrationQuarantine) as invalid_tag:
        reencrypt_payload(source[:-1] + bytes([source[-1] ^ 1]), source_aad=b"right-aad", **args)
    assert invalid_tag.value.code == "source_authentication_failed"
    with pytest.raises(MigrationQuarantine) as wrong_aad:
        reencrypt_payload(source, source_aad=b"wrong-aad", **args)
    assert wrong_aad.value.code == "source_authentication_failed"
    with pytest.raises(MigrationQuarantine) as digest:
        reencrypt_payload(source, source_aad=b"right-aad", expected_plaintext_sha256="0" * 64, **args)
    assert digest.value.code == "source_plaintext_digest_mismatch"


def test_optional_empty_payload_and_null_payload_are_preserved_without_encryption():
    key_a, key_b = bytes(range(32)), bytes(range(32, 64))
    assert reencrypt_payload(None, source_key=key_a, destination_key=key_b,
                             source_aad=b"a", destination_aad=b"b") is None
    empty = reencrypt_payload(b"", source_key=key_a, destination_key=key_b,
                              source_aad=b"a", destination_aad=b"b", allow_empty=True)
    assert empty is not None and empty.ciphertext == b""


def test_owner_and_relationship_checks_quarantine_without_reassignment():
    validate_task_child_owner(task_owner="owner-a", child_owner="owner-a")
    with pytest.raises(MigrationQuarantine) as ownerless:
        validate_task_child_owner(task_owner=None, child_owner="owner-a")
    assert ownerless.value.code == "ownerless_task"
    with pytest.raises(MigrationQuarantine) as mismatch:
        validate_task_child_owner(task_owner="owner-a", child_owner="owner-b")
    assert mismatch.value.code == "task_child_owner_mismatch"
    validate_conversation_task_owner(conversation_owner="owner-a", task_owner="owner-a")
    with pytest.raises(MigrationQuarantine):
        validate_conversation_task_owner(conversation_owner="owner-a", task_owner="owner-b")
    assert validate_run_task_link(task_id=None, conversation_task_ids=set()) is None
    assert validate_run_task_link(task_id="task-a", conversation_task_ids={"task-a"}) == "task-a"
    with pytest.raises(MigrationQuarantine) as unlinked:
        validate_run_task_link(task_id="task-b", conversation_task_ids={"task-a"})
    assert unlinked.value.code == "run_task_association_missing"


def test_retention_deadline_is_never_extended_by_harness():
    now = datetime(2026, 11, 23, tzinfo=timezone.utc)
    assert is_expired(expires_at=now - timedelta(seconds=1), now=now)
    assert not is_expired(expires_at=now + timedelta(days=1), now=now)
