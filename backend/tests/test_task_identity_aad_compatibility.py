"""Prove that stable task renames can preserve legacy ciphertext bytes.

These tests use synthetic identifiers and keys only. They do not access an
application database or environment secrets.
"""
import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.migration_harness.crypto import (
    source_agent_checkpoint_aad,
    source_agent_event_aad,
    source_agent_message_aad,
    source_preparation_aad,
    source_private_document_aad,
    task_identity_source_aad_v1,
)


@pytest.mark.parametrize(
    ("payload_kind", "source_aad", "identity"),
    [
        (
            "agent_message",
            source_agent_message_aad(
                owner_subject="owner-fixture", thread_id="conversation-fixture",
                run_id="run-fixture", client_message_id="message-fixture",
                case_id=None, accepted_revision=4,
            ),
            {
                "conversation_id": "conversation-fixture", "task_id": None,
                "record_id": "run-fixture", "client_message_id": "message-fixture",
                "revision": 4,
            },
        ),
        (
            "agent_event",
            source_agent_event_aad(
                owner_subject="owner-fixture", thread_id="conversation-fixture",
                run_id="run-fixture", case_id="task-fixture", event_sequence=5,
            ),
            {
                "conversation_id": "conversation-fixture", "task_id": "task-fixture",
                "record_id": "run-fixture", "sequence": 5,
            },
        ),
        (
            "agent_checkpoint",
            source_agent_checkpoint_aad(
                owner_subject="owner-fixture", thread_id="conversation-fixture",
                run_id="run-fixture", case_id=None, revision=6, event_watermark=5,
            ),
            {
                "conversation_id": "conversation-fixture", "task_id": None,
                "record_id": "run-fixture", "revision": 6, "event_watermark": 5,
            },
        ),
        (
            "preparation_facts",
            source_preparation_aad(
                case_id="task-fixture", owner_subject="owner-fixture",
                record_identity="case-facts",
            ),
            {"conversation_id": None, "task_id": "task-fixture", "record_id": "task-fixture"},
        ),
        (
            "preparation_document",
            source_preparation_aad(
                case_id="task-fixture", owner_subject="owner-fixture",
                record_identity="document-fixture",
            ),
            {"conversation_id": None, "task_id": "task-fixture", "record_id": "document-fixture"},
        ),
        (
            "preparation_review",
            source_preparation_aad(
                case_id="task-fixture", owner_subject="owner-fixture",
                record_identity="document-fixture:review",
            ),
            {"conversation_id": None, "task_id": "task-fixture", "record_id": "document-fixture"},
        ),
        (
            "guide_turn",
            source_preparation_aad(
                case_id="task-fixture", owner_subject="owner-fixture",
                record_identity="turn-fixture",
            ),
            {"conversation_id": None, "task_id": "task-fixture", "record_id": "turn-fixture"},
        ),
        (
            "private_document",
            source_private_document_aad(
                case_id="task-fixture", owner_subject="owner-fixture",
                document_identity="private-document-fixture",
            ),
            {
                "conversation_id": None, "task_id": "task-fixture",
                "record_id": "private-document-fixture",
            },
        ),
        (
            "private_document_review",
            source_private_document_aad(
                case_id="task-fixture", owner_subject="owner-fixture",
                document_identity="private-document-fixture:review",
            ),
            {
                "conversation_id": None, "task_id": "task-fixture",
                "record_id": "private-document-fixture",
            },
        ),
    ],
)
def test_stable_task_identity_reuses_exact_legacy_aad_and_ciphertext(
    payload_kind, source_aad, identity,
):
    """Case ID → same task ID and thread ID → same conversation ID is byte-identical."""
    key = bytes(range(32))
    plaintext = b'{"synthetic":"payload"}'
    nonce = bytes(range(12))
    ciphertext = nonce + AESGCM(key).encrypt(nonce, plaintext, source_aad)

    target_aad = task_identity_source_aad_v1(
        payload_kind=payload_kind,
        owner_subject="owner-fixture",
        **identity,
    )

    assert target_aad == source_aad
    # A staged copy can retain the exact ciphertext; no decrypt/re-encrypt is
    # needed when every authenticated identity dimension is unchanged.
    copied_ciphertext = bytes(ciphertext)
    assert copied_ciphertext == ciphertext
    assert AESGCM(key).decrypt(
        copied_ciphertext[:12], copied_ciphertext[12:], target_aad,
    ) == plaintext


def test_task_identity_compatibility_fails_closed_when_authenticated_identity_changes():
    key = bytes(range(32))
    plaintext = b"synthetic"
    source_aad = source_agent_event_aad(
        owner_subject="owner-fixture", thread_id="conversation-fixture",
        run_id="run-fixture", case_id="task-fixture", event_sequence=5,
    )
    nonce = bytes(range(12))
    ciphertext = nonce + AESGCM(key).encrypt(nonce, plaintext, source_aad)
    changed_aad = task_identity_source_aad_v1(
        payload_kind="agent_event",
        owner_subject="owner-fixture",
        conversation_id="conversation-fixture",
        task_id="different-task",
        record_id="run-fixture",
        sequence=5,
    )

    assert changed_aad != source_aad
    with pytest.raises(InvalidTag):
        AESGCM(key).decrypt(ciphertext[:12], ciphertext[12:], changed_aad)


def test_task_identity_compatibility_rejects_missing_identity_dimensions():
    with pytest.raises(ValueError, match="conversation identity"):
        task_identity_source_aad_v1(
            payload_kind="agent_event", owner_subject="owner-fixture",
            conversation_id=None, task_id="task-fixture",
            record_id="run-fixture", sequence=1,
        )
    with pytest.raises(ValueError, match="Task-owned payloads"):
        task_identity_source_aad_v1(
            payload_kind="private_document", owner_subject="owner-fixture",
            conversation_id=None, task_id=None, record_id="document-fixture",
        )
