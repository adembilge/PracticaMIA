"""Disposable PostgreSQL staging/ledger harness for M3.

Runs only in the existing CI PostgreSQL smoke phase. It creates an isolated,
random schema and drops it afterwards. It never touches application tables.
"""
from hashlib import sha256
import os
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import create_engine, text

from app.migration_harness.crypto import (
    MigrationQuarantine,
    destination_aad_v2,
    reencrypt_payload,
    stage_verified_record,
)

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_SMOKE") != "1",
    reason="requires the disposable CI PostgreSQL database",
)


def test_postgres_stage_ledger_atomicity_retry_and_revalidation():
    engine = create_engine(os.environ["DATABASE_URL"])
    schema = f"m3_harness_{uuid4().hex}"
    source_key, destination_key = bytes(range(32)), bytes(range(32, 64))
    source_aad = b"practicamia-agent-request/v1:synthetic-source"
    destination_aad = destination_aad_v2(
        payload_kind="agent_message", owner_subject="synthetic-owner",
        conversation_id="synthetic-conversation", task_id=None,
        record_id="synthetic-run", purpose="accepted-message", revision=2,
    )
    plaintext = b'{"message":"synthetic only","language":"en"}'
    nonce = bytes(range(12))
    source_ciphertext = nonce + AESGCM(source_key).encrypt(nonce, plaintext, source_aad)
    migrated = reencrypt_payload(
        source_ciphertext, source_key=source_key, destination_key=destination_key,
        source_aad=source_aad, destination_aad=destination_aad,
        expected_plaintext_sha256=sha256(plaintext).hexdigest(),
    )
    assert migrated is not None

    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(
                f'CREATE TABLE "{schema}".target_payloads ('
                "id TEXT PRIMARY KEY, ciphertext BYTEA NOT NULL, content_sha256 TEXT NOT NULL)"
            ))
            connection.execute(text(
                f'CREATE TABLE "{schema}".migration_ledger ('
                "source_id TEXT PRIMARY KEY, target_id TEXT NOT NULL, "
                "source_ciphertext_sha256 TEXT NOT NULL, target_ciphertext_sha256 TEXT NOT NULL, "
                "aad_version TEXT NOT NULL, status TEXT NOT NULL, attempt_count INTEGER NOT NULL)"
            ))

        with engine.begin() as connection:
            outcome = stage_verified_record(
                connection, target_table=f"{schema}.target_payloads",
                ledger_table=f"{schema}.migration_ledger", source_id="source-1",
                target_id="target-1", ciphertext=migrated.ciphertext,
                source_ciphertext_sha256=migrated.source_ciphertext_sha256,
                aad_version="v2",
                verify_existing=lambda value: AESGCM(destination_key).decrypt(
                    value[:12], value[12:], destination_aad,
                ) == plaintext,
            )
            assert outcome == "staged"

        with engine.begin() as connection:
            outcome = stage_verified_record(
                connection, target_table=f"{schema}.target_payloads",
                ledger_table=f"{schema}.migration_ledger", source_id="source-1",
                target_id="target-1", ciphertext=migrated.ciphertext,
                source_ciphertext_sha256=migrated.source_ciphertext_sha256,
                aad_version="v2",
                verify_existing=lambda value: AESGCM(destination_key).decrypt(
                    value[:12], value[12:], destination_aad,
                ) == plaintext,
            )
            assert outcome == "already_verified"

        with engine.connect() as connection:
            assert connection.execute(text(
                f'SELECT count(*) FROM "{schema}".target_payloads'
            )).scalar_one() == 1
            assert connection.execute(text(
                f'SELECT count(*) FROM "{schema}".migration_ledger'
            )).scalar_one() == 1
            assert connection.execute(
                text(f'SELECT attempt_count FROM "{schema}".migration_ledger WHERE source_id=:source_id'),
                {"source_id": "source-1"},
            ).scalar_one() == 2

        # A target row without a verified ledger is never silently adopted.
        with engine.begin() as connection:
            connection.execute(text(
                f'INSERT INTO "{schema}".target_payloads (id, ciphertext, content_sha256) '
                "VALUES ('orphan-target', :ciphertext, :digest)"
            ), {"ciphertext": migrated.ciphertext, "digest": migrated.destination_ciphertext_sha256})
        with engine.begin() as connection:
            with pytest.raises(MigrationQuarantine) as orphan:
                stage_verified_record(
                    connection, target_table=f"{schema}.target_payloads",
                    ledger_table=f"{schema}.migration_ledger", source_id="source-orphan",
                    target_id="orphan-target", ciphertext=migrated.ciphertext,
                    source_ciphertext_sha256=migrated.source_ciphertext_sha256,
                    aad_version="v2", verify_existing=lambda _: True,
                )
            assert orphan.value.code == "target_without_verified_ledger"

        # Target and ledger insertion are in the caller's transaction together.
        with pytest.raises(RuntimeError):
            with engine.begin() as connection:
                stage_verified_record(
                    connection, target_table=f"{schema}.target_payloads",
                    ledger_table=f"{schema}.migration_ledger", source_id="source-rollback",
                    target_id="target-rollback", ciphertext=migrated.ciphertext,
                    source_ciphertext_sha256=migrated.source_ciphertext_sha256,
                    aad_version="v2", verify_existing=lambda _: True,
                )
                raise RuntimeError("synthetic rollback")
        with engine.connect() as connection:
            assert connection.execute(text(
                f'SELECT count(*) FROM "{schema}".target_payloads WHERE id=\'target-rollback\''
            )).scalar_one() == 0
            assert connection.execute(text(
                f'SELECT count(*) FROM "{schema}".migration_ledger WHERE source_id=\'source-rollback\''
            )).scalar_one() == 0
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
