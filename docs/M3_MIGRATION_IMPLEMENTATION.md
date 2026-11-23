# M3 — conversation/task migration implementation and recovery plan

**Status:** Disposable migration primitives, PostgreSQL staging harness and synthetic coverage for all nine encrypted payload families implemented; live source-to-target migration is not authorized and remains unexecuted.  
**Date:** 23 November 2026  
**Base:** `main` after M2.5 PR #268 merge, `146a31f7376d8b5e9cd74106e252f9f14c8f2675`  
**Scope:** One coordinated M3 workstream. This document and the harness do not authorize application-schema changes, production/staging access, secret retrieval, data mutation, key rotation, cutover or Phase 5.

## 1. Execution boundary

M3 is treated as one coordinated deliverable rather than five separately approved PRs:

1. Freeze the source/target mapping and migration ordering.
2. Build the disposable PostgreSQL staging and ledger harness.
3. Validate ownership, relationship cardinality and lifecycle preservation.
4. Validate authenticated payload conversion from source AAD to destination AAD v2.
5. Exercise idempotency, interruption, quarantine, retention races and recovery acceptance.

The harness in `backend/app/migration_harness/` is deliberately not imported by application runtime modules. It accepts explicit key bytes and explicit AAD, has no environment-variable or database-URL lookup, and cannot connect to an application database by itself. PostgreSQL tests create a random isolated schema and drop it after the test.

**Not implemented or authorized:** live source-table readers, target application tables, Alembic rename/copy/drop migrations, production or staging key retrieval, a write-fence toggle, worker drain controls, application cutover, source deletion or production execution changes. These require M2.5 approvals and separate explicit environment authorization.

## 2. Frozen source-to-target mapping

Use the M2.4 mapping without changing cardinality or ownership semantics:

| Source | Target | Ordering / invariant |
|---|---|---|
| `agent_threads` | `conversations` | Preserve ID, owner and revision; owner is authoritative for run records |
| `cases` | `tasks` | Preserve ID, procedure, status, scope, archive state and timestamps; nullable owner remains null |
| `agent_thread_cases` | `conversation_tasks` | Preserve composite identity; many-to-many; both owners must match |
| `case_intakes` | `task_intakes` | Preserve confirmed facts, confirmation time, checklist progress and fingerprint; do not merge provisional scope answers |
| `case_preparations` | `task_preparations` | Preserve owner, review digest and update time; re-encrypt facts payload |
| `case_documents` | `task_documents` | Preserve ID, owner, type, media type, checksum and created time; re-encrypt body and review independently |
| `case_agent_turns` | `task_guide_turns` | Preserve ID, owner, checksum and timestamp; re-encrypt each turn |
| `private_case_documents` | `private_task_documents` | Preserve ID, owner, category, media type, checksum, consent, scan/upload times and original expiry; never extend retention |
| `agent_run_requests` | `conversation_runs` | Preserve ID, conversation, status, accepted revision, client-message idempotency, accepted time and lease; nullable task remains null |
| `agent_run_events` | `conversation_run_events` | Preserve run ID and event sequence; verify every event and strict ordering |
| `agent_run_checkpoints` | `conversation_run_checkpoints` | Preserve one-per-run identity, revision and event watermark; watermark must equal the final event sequence |
| `agent_case_operations` | `task_operation_receipts` | Preserve receipt IDs, run/task links, operation/proposal IDs and revision uniqueness |

Knowledge/source registry tables are outside this migration.

## 3. Required migration ordering

The disposable runner must stage parent identities before dependent records:

1. Preflight exact source schema revision, snapshot boundary, target schema, key-family availability and pairwise key distinctness. Stop before reading payloads if any prerequisite fails.
2. Stage `conversations` and `tasks` while preserving identifiers and nullable task owners.
3. Stage `conversation_tasks`; require both parents and exact owner equality.
4. Stage intake, preparation metadata, preparation documents, guide turns and private vault metadata. Preserve every source expiry deadline.
5. Stage `conversation_runs`; null task links remain null. Non-null task links must resolve through the exact same-conversation association.
6. Stage events and checkpoints only after their run. Verify contiguous event sequence, one checkpoint maximum, positive revision and checkpoint watermark equality.
7. Stage operation receipts only after both run and task. Preserve all three unique scopes and the revision-plus-one invariant.
8. Reconcile source counts to target counts plus explicit quarantine and retention exclusions. Do not remove quarantined rows from the denominator.
9. Run owner-isolation, archive/restore, deletion, reconnect/resume and approval-replay acceptance checks before cutover review.

A task must never be synthesized to satisfy a linked-run FK. A null run task link is a valid state.

## 4. Ownership and quarantine rules

- Task owner is authoritative for task-scoped rows.
- Conversation owner is authoritative for runs, events and checkpoints.
- Every denormalized child owner must exactly equal its task owner.
- A conversation/task association is valid only when both parents have the same non-null owner.
- Ownerless legacy tasks remain null, inaccessible and unassigned. They are not repaired by inferring an owner from a conversation or child.
- Missing parents, owner mismatch, ambiguous association, invalid nullable-link combination, orphaned receipt, invalid event sequence and unresolvable checkpoint are quarantined.
- Quarantine output may contain only opaque source identifiers, safe failure category and non-sensitive digest. Never store plaintext, keys, raw owner subjects or message/document text.

The current harness implements fail-closed owner checks and nullable run-link validation. Full table-level quarantine accounting is still a required dry-run acceptance result.

## 5. Encryption contract

The exact source AAD v1 builders are implemented for accepted messages, events, checkpoints, preparation payloads and private-vault payloads. Their compact JSON/string encodings are covered by byte-for-byte tests. The canonical destination AAD v2 tuple implemented in `destination_aad_v2` is UTF-8 JSON with compact separators and this ordered tuple:

```text
[
  "practicamia-task-payload/v2",
  payload_kind,
  owner_subject,
  conversation_id,
  task_id_or_null,
  stable_record_id,
  payload_purpose,
  event_sequence_or_null,
  checkpoint_revision_or_null,
  checkpoint_event_watermark_or_null
]
```

The supported payload kinds are explicit in the harness. Agent messages/events/checkpoints and each document/facts/review/guide-turn payload use distinct kinds and purposes. Unlinked runs retain JSON null for task identity.

For every non-empty payload:

1. Decrypt with its exact source key family and exact source AAD.
2. Authenticate before parsing; reject short ciphertext and invalid tags.
3. Validate the typed/schema payload and any existing plaintext digest.
4. Construct destination AAD from validated database identities only.
5. Encrypt with a fresh 12-byte nonce and the approved destination key.
6. Immediately decrypt destination ciphertext and compare canonical plaintext/digest.
7. Persist target ciphertext and its verified ledger entry in one transaction.

Null and explicitly empty optional review payloads remain null/empty. They are not converted into encrypted representations. No source ciphertext may be relabeled as v2.

The harness checks 256-bit key length and pairwise inequality of all active key families in memory. It never logs or persists key values or fingerprints. Production secret versions, custody and recovery availability are not established by repository code and remain operator evidence.

## 6. Staging ledger and retry semantics

The disposable PostgreSQL harness uses a minimal ledger shape:

| Field | Meaning |
|---|---|
| `source_id` | Opaque source row key; unique within a migration run |
| `target_id` | Target row key |
| `source_ciphertext_sha256` | Digest of source ciphertext, not plaintext |
| `target_ciphertext_sha256` | Digest of verified target ciphertext |
| `aad_version` | Destination AAD version |
| `status` | `verified` only after destination verification |
| `attempt_count` | Bounded retry accounting |

No plaintext or owner subject is stored. Target row and verified ledger entry are inserted in the caller's single transaction. Retry rechecks the target ciphertext digest and calls a destination decrypt verifier. A target without a verified ledger is a hard stop; a mismatched ledger is not overwritten.

This is a disposable harness contract, not an approved production ledger schema. The final production ledger schema, access policy and migration-run partitioning require engineering/security review.

## 7. Retention, interruption and recovery

- Private vault expiry remains seven days; the existing authorized purge process remains active and bounded to 500 rows per batch.
- Preserve `expires_at` exactly. Re-check source existence and expiry before final reconciliation.
- If a source expires or is purged before cutover, remove/exclude its staged target copy. Never resurrect it.
- Interruption resumes only from a verified ledger row after target revalidation.
- Target-without-ledger, ledger-without-target, digest mismatch, invalid tag, owner mismatch, missing parent or uniqueness conflict stops that row/batch for reconciliation.
- Before target writers resume, rollback means keep the write fence and route reads to unchanged source.
- After target writers resume, source is stale; a configuration flip is not rollback. A separately approved reverse migration/replay or target recovery is required.
- Logical deletion does not imply immediate expiry from database backups/PITR.

The current PostgreSQL harness exercises atomic target+ledger writes, retry revalidation, orphan-target rejection and transaction rollback. Synthetic round-trip tests cover all nine encrypted payload families in PR #271. Full worker-drain, retention-purge race, backup restore and post-cutover recovery drills remain unexecuted.

## 8. Implemented tests and remaining acceptance evidence

Implemented in this branch:

- Pure tests for pairwise key checks, byte-for-byte source AAD v1 builders, canonical AAD v2 identity, source authentication, digest validation, destination decrypt verification, owner mismatch, ownerless rows, nullable run links and retention timestamp behavior.
- Disposable PostgreSQL test using a random schema for target/ledger atomicity, retry/revalidation, orphan-target rejection and rollback.
- Backend CI invokes the PostgreSQL harness in its existing disposable PostgreSQL phase.

Still required before M3 can be declared fully accepted:

- Full-table source/target counts and FK/cardinality reconciliation on a representative disposable snapshot.
- Fixture coverage for every encrypted payload family using the exact source AAD builders and typed validators.
- Event/checkpoint/receipt consistency and resume/reconnect/approval journey tests across the staged target.
- Private-vault purge racing with staging and expiry recheck.
- Process interruption at each batch boundary and idempotent resume.
- Pre-migration backup restore drill and approved source-key recovery drill.
- Engineering/security/operator approval, per-environment key inventory and custody evidence.
- Explicit authorization for any non-disposable environment.

## 9. Alembic and rollback boundary

No Alembic revision is added in this workstream. The current source schema remains authoritative, and the target schema has not been approved for application use. Introducing target application tables before schema review would prematurely commit a physical contract and could create a second writable domain.

Once prerequisites are approved, a separately reviewed Alembic revision may create target tables additively. Its downgrade may remove only empty/disposable target structures after verifying no application reads or writes have been enabled. It must never drop or rename source tables. Source removal belongs to a later cleanup milestone after an approved recovery window and a separate explicit authorization.

## 10. Go/no-go

M3 is not complete for live data until every source row is either verified in target or explicitly quarantined/excluded under approved policy, all relationship and encrypted payload checks pass, and recovery evidence is accepted. Any unexplained count difference, owner mismatch, undecryptable payload, missing key version, invalid digest, event gap, checkpoint watermark mismatch, expired-document resurrection or unverified approval receipt is a hard stop.

**Current result:** the safe disposable cryptographic and transaction harness plus synthetic round-trip coverage for all nine encrypted payload families are implemented. Live data migration, application schema migration and cutover are not authorized and have not been executed. M2.5 review work is deferred by project-owner decision. No production or staging data or keys have been accessed or changed.
