# Encrypted payload migration and consistency strategy — M2.5

**Status:** Deferred by project owner; design baseline retained, no further M2.5 review work planned  
**Date:** 23 November 2026  
**Source baseline:** main after M2.4 merge, commit 49abd8ee60be3423516ae2b783d531a0fb6a35eb  
**Depends on:** TASK_CONVERSATION_TARGET_MODEL.md  
**Scope:** Design only. No secret retrieval, schema change, data mutation, key rotation, ciphertext rewrite or deployment change.

## 1. Objective and governing rule

Move case-bound encrypted payloads to the approved task/conversation identity without losing confidentiality, authenticated identity, ownership, review provenance, retention deadlines, run replay or recovery.

Ciphertext and associated data (AAD) are one indivisible record. A foreign-key or identifier update alone is invalid whenever it changes any authenticated AAD dimension. Source rows remain authoritative and intact until the target passes verification and a separate cutover approval is granted.

**Default consistency strategy: a bounded global write fence with staged target writes and an idempotent migration ledger. Do not dual-write.** Current application code has no verified dual-write/outbox/replay contract for these records. Naive dual-write could create a run without its event, an event without its checkpoint, duplicate approval receipts or diverging task revisions.

## 2. Verified encryption inventory

All three encryption families use AES-256-GCM. Stored bytes use a 12-byte nonce followed by AES-GCM ciphertext and authentication tag. Keys are 32-byte values decoded from standard base64 configuration. AAD is authenticated, not encrypted metadata.

| Payload class | Source storage | Key configuration | Source AAD identity | Integrity / format |
|---|---|---|---|---|
| Accepted agent message | agent_run_requests.message_ciphertext | AGENT_PREVIEW_JOURNAL_KEY | JSON array: domain practicamia-agent-request/v1, owner subject, thread ID, run ID, client message ID, nullable case ID, accepted revision | AES-GCM; serialized message JSON; no independent payload digest column identified |
| Agent event | agent_run_events.ciphertext | AGENT_PREVIEW_JOURNAL_KEY | JSON array: domain practicamia-agent-event/v1, owner subject, thread ID, run ID, nullable case ID, event sequence | AES-GCM; typed event JSON; event sequence is part of row identity |
| Agent checkpoint | agent_run_checkpoints.ciphertext | AGENT_PREVIEW_JOURNAL_KEY | JSON array: domain practicamia-agent-checkpoint/v1, owner subject, thread ID, run ID, nullable case ID, checkpoint revision, event sequence | AES-GCM; checkpoint-state JSON; revision and event watermark are persisted |
| Preparation document bytes | case_documents.ciphertext | PREPARATION_DOCUMENT_KEY | UTF-8 string: practicamia-preview-document/v1:{case_id}:{owner_subject}:{document_id} | AES-GCM; content_sha256 verifies decrypted bytes |
| Preparation facts | case_preparations.facts_ciphertext | PREPARATION_DOCUMENT_KEY | UTF-8 string: practicamia-preview-document/v1:{case_id}:{owner_subject}:case-facts | AES-GCM; JSON object; no independent ciphertext digest column identified |
| Preparation document review | case_documents.review_ciphertext | PREPARATION_DOCUMENT_KEY | Same preparation AAD domain, document identity {document_id}:review | AES-GCM; bounded review JSON; empty bytes mean no review payload |
| Preparation guide turn | case_agent_turns.content_ciphertext | PREPARATION_DOCUMENT_KEY | Same preparation AAD domain, turn ID as document identity | AES-GCM; bounded turn JSON; content_sha256 verifies decrypted bytes |
| Private vault document bytes | private_case_documents.ciphertext | PRIVATE_DOCUMENT_KEY | UTF-8 string: practicamia:private-document:v1:{case_id}:{owner_subject}:{document_id} | AES-GCM; content_sha256 verifies decrypted bytes |
| Private vault review metadata | private_case_documents.review_ciphertext | PRIVATE_DOCUMENT_KEY | Same private-document AAD domain, identity {document_id}:review | AES-GCM; bounded versioned review JSON; nullable when absent |

### Key configuration and custody findings

- AGENT_PREVIEW_JOURNAL_KEY, PREPARATION_DOCUMENT_KEY and PRIVATE_DOCUMENT_KEY are distinct configuration inputs. The reviewed agent Preview mount checks that the agent journal key differs from the preparation key. Private-vault settings check that the private key differs from the preparation key.
- Current checks do not establish pairwise inequality between all three keys when all three features are enabled. M3 preflight must compare key fingerprints in memory and fail closed if any two active key families are equal. Never print or persist key values or fingerprints in ordinary logs.
- Configuration proves key shape, not the operational key inventory. The repository does not establish deployed secret-manager key versions, custody owners, backup availability, rotation history or recovery access. An authorized operator must attest these independently before a dry run.
- The agent journal key is documented for isolated Preview. Do not assume Preview ciphertext or its key exists in Production. Inventory each environment and database separately; never copy Preview keys or payloads into Production.
- Do not rotate keys as part of the domain migration. Key rotation and identity/AAD migration are separate changes with separate rollback tests.

## 3. Destination cryptographic contract

Use a versioned destination AAD namespace (v2) and task identity wherever the destination model changes the authenticated domain or case identity. Freeze the exact canonical byte encoding in the M3 implementation design before writing code.

The v2 contract must bind, as applicable: owner subject unchanged byte-for-byte; conversation ID and run ID for agent payloads; client message ID and accepted revision for accepted messages; task ID (nullable only for unlinked runs); event sequence or checkpoint revision and event watermark; stable document/turn/record ID and payload purpose (body, facts, review, guide-turn); and an explicit AAD schema/version identifier.

Do not add a task ID to an unlinked run. A null source task link remains null. A linked run must resolve through the exact same-owner conversation/task association before target ciphertext is written.

### Read/write rule

1. Read source bytes only with the source key family and exact source AAD in Section 2.
2. Authenticate AES-GCM before parsing. Reject short blobs, invalid tags, malformed serialization, unexpected schema versions and invalid identities.
3. Validate the decrypted payload against its current typed/schema contract and independent digest where one exists.
4. Construct destination AAD from validated target identity, never client input or a guessed mapping.
5. Encrypt with a fresh cryptographically random 12-byte nonce and approved destination key version.
6. Immediately decrypt the new ciphertext using destination key/AAD and verify digest or canonical semantic equality.
7. Persist target ciphertext and migration-ledger completion in the same database transaction.

If destination retains exactly the same identity dimensions and byte encoding, ciphertext reuse is allowed only after formal equivalence proof and tests. Default is decrypt/re-encrypt; never relabel v1 ciphertext as v2 or reuse it under changed AAD.

## 4. Ownership and mapping preconditions

Before decrypting any row:
- Resolve the source task parent and conversation/run relationship.
- Require each denormalized task-child owner_subject to equal its parent task owner.
- Require conversation and linked task to have the same owner.
- Derive agent message/event/checkpoint owner from the owning conversation/thread, not client input.
- Preserve ownerless task rows as null and inaccessible. Do not infer an owner from a conversation, document, email or neighboring record.
- Quarantine orphans, owner mismatches, missing parents, ambiguous links, invalid nullable-link combinations and unresolvable run/receipt references. Never repair automatically.
- Preserve archived task state and read-only semantics. Migration does not restore or reactivate archived tasks.

A row whose source identity cannot be proven is not decryptable by guessing. Stop that row and record only non-sensitive identifiers, failure category and safe digest in a restricted quarantine report.

## 5. Consistency strategy: write fence, not dual-write

### Why dual-write is rejected

Related state is written through multiple API and worker transactions. Run events advance status; checkpoints carry an event watermark; approvals write receipts and append events; archive/delete operations serialize through task-before-run locks. No existing outbox or replay protocol proves atomic equivalence across old and new tables. Naive dual-write can produce partial runs, event gaps, duplicate receipts or divergent task revisions.

Do not introduce dual-write unless a separate design proves transaction boundaries, idempotency, ordering, conflict resolution, replay and rollback.

### Required write-fence protocol

1. **Preflight:** confirm target schema, mapping, keys/key versions, AAD v2 encoding, capacity, backup/restore evidence and approved window.
2. **Fence writes:** stop task/intake/preparation/document-review mutations, new linked run acceptance, event/checkpoint writes, approval operations, archive/restore/delete transitions and worker claims/commits for the migration scope.
3. **Drain workers:** wait for active run leases to finish or be safely fenced. Confirm no worker can commit after the snapshot boundary. Preserve task-before-run lock ordering from PR #265.
4. **Establish a consistent source boundary:** record database snapshot/transaction boundary and source counts. No ordinary application writes may cross it.
5. **Stage target records:** write bounded batches. Parent identities and conversation/task associations precede dependent runs and encrypted children. Incomplete target rows remain unavailable to normal application reads.
6. **Commit per batch:** target rows, source-to-target mapping ledger and verified completion marker commit atomically. Source rows remain unchanged.
7. **Verify:** reconcile every source row to a target row or explicit quarantine/retention exclusion. Validate counts, relationships, ownership, ciphertext authentication, digests, event order, checkpoint watermarks, receipts and representative journeys.
8. **Cut over under the fence:** switch reads to the verified target and run negative/owner-isolation checks while writes remain disabled.
9. **Resume writes:** enable target writers only after explicit cutover approval. Keep source tables read-only and intact through the approved recovery window.

### Migration ledger and retries

M3 should introduce a restricted migration ledger (exact schema to be approved in M3) containing only migration run/version, source table and primary key, destination primary key, source and destination ciphertext digests, AAD version identifiers, status (pending, verified, quarantined, excluded-by-retention), attempt count, timestamps and non-sensitive failure code.

The ledger must not contain plaintext, raw keys, document/message text or full owner subjects. Store only the minimum owner-safe reference required for access-controlled reconciliation; prefer a keyed/pseudonymous owner reference where sufficient.

Retries must be idempotent. A completed ledger row is not blindly trusted: re-check target identity, ciphertext digest and decryptability. If a target row exists without a matching verified ledger entry, stop and reconcile; never overwrite or skip it silently.

## 6. Private-document retention during migration

The private vault has a 7-day expiry policy and an authorized bounded purge process (up to 500 rows per batch). Migration must not pause or extend this policy for convenience.

- Preserve consent_version, consented_at, scanned_at, uploaded_at, expires_at, category, media type, checksum and document identity.
- Never reset expires_at during copy or re-encryption.
- Keep the authorized source retention purge active during staging. Re-check source existence and expiry before final target reconciliation.
- If a source document is purged or expires before cutover, delete/exclude its staged target copy; never resurrect it from the snapshot.
- At cutover, target retention must be ready and verified before document reads/writes resume. Preserve expiry semantics and batch bound.
- Logical deletion does not guarantee immediate removal from database backups/PITR.

## 7. Failure, quarantine and recovery behavior

| Failure | Required behavior |
|---|---|
| Missing/invalid key or unknown key version | Abort before processing that key family; do not try another key |
| AES-GCM invalid tag/authentication failure | Quarantine row; no parse, repair, fallback AAD or plaintext logging |
| Missing parent, owner mismatch or ambiguous mapping | Quarantine; no owner inference or reassignment |
| Digest mismatch / invalid typed payload | Quarantine; do not write target ciphertext |
| Destination encrypt/decrypt verification failure | Roll back batch transaction; source remains intact |
| Process interruption | Resume from verified ledger state after revalidating target records |
| Target FK/uniqueness conflict | Stop and reconcile; never drop a constraint or choose a winner automatically |
| Retention purge/expiry race | Source purge remains authoritative; remove staged copy during reconciliation |
| Cutover acceptance failure | Keep write fence; route reads back to unchanged source; repair or abandon staging |
| Failure after target writes resume | Do not simply point to stale source. Use separately approved reverse migration/replay or target recovery |

### Rollback boundary

Before target writes resume, rollback means returning reads to unchanged source while keeping the write fence. After target writes resume, source is stale by design; rollback is no longer a configuration flip. Post-cutover rollback requires a separately designed reverse migration or target recovery procedure.

## 8. Dry-run evidence and acceptance gates

A dry run must execute against a disposable PostgreSQL snapshot with matching schema revision and representative encrypted fixture classes. It must not access production secrets or mutate production/staging records.

Required evidence:
- source/target counts by table and disposition (migrated, quarantined, excluded by retention);
- complete FK/association integrity, including nullable unlinked runs;
- owner equality and proof ownerless rows remain inaccessible;
- successful source decrypt using exact source key/AAD for every payload class;
- destination decrypt after re-encryption and digest/canonical semantic equality;
- preservation of run status, accepted revision, idempotency keys, event sequence, checkpoint revision/watermark, lease state and approval receipts;
- preservation of document checksums, consent provenance and original expiry deadlines;
- archive/read-only and restore/write behavior;
- owner-isolation negative tests, invalid-tag/missing-key tests, interrupted-batch/retry tests and retention-race tests;
- resume/reconnect and approval journeys across the migration boundary;
- restore drill from pre-migration backup and recovery of source key material from approved secret custody.

No plaintext may appear in CI logs, migration logs, ledger rows, metrics, exception text, quarantine reports or artifacts. Reports use counts, opaque fixture IDs and safe failure categories only.

**Go/no-go:** every required class must be migrated and verified or explicitly quarantined/excluded under approved policy. Any unexplained count difference, owner mismatch, undecryptable payload, missing key version, invalid digest, event gap, checkpoint watermark mismatch or unverified approval receipt is a hard stop. Do not claim 100% success by excluding failures from the denominator.

## 9. M3 implementation prerequisites

M3 must not begin until approved and evidenced:
1. Product/engineering approval of M2.4 target schema and deletion/retention contract.
2. Operator key inventory per environment: secret reference, version/identifier, custody owner, availability, backup/recovery evidence and permitted use. Never place secret values in repository docs.
3. Pairwise distinct active key-family fingerprints, checked without logging key material.
4. Frozen AAD v2 byte encoding and explicit payload schema versions.
5. Exact treatment for ownerless, archived, orphaned, expired and malformed records.
6. Approved write-fence duration, worker drain, retention race handling and cutover owner.
7. Disposable PostgreSQL dry-run and restore-drill results meeting Section 8.
8. Approved pre-cutover rollback and post-cutover recovery plans.
9. Explicit authorization for any non-disposable environment. This document authorizes no production or staging mutation.

## 10. M2.5 acceptance checklist

- [x] Inventory encrypted payload classes and source key configuration.
- [x] Record source AAD dimensions and serialization/integrity checks.
- [x] Define destination AAD versioning and decrypt/validate/re-encrypt/verify sequence.
- [x] Select write-fence strategy and reject unproven dual-write.
- [x] Define idempotent staging ledger, retry and quarantine behavior.
- [x] Define private-document retention and purge race handling.
- [x] Define dry-run evidence, cutover boundary and pre/post-cutover recovery.
- [x] Record missing operator evidence: deployed key versions/custody and pairwise key distinctness.
- [ ] Obtain engineering/security/operator review and approval before M3.

## 11. Explicit non-goals

This document authorizes no schema/runtime change, migration table creation, secret access/rotation, ciphertext re-encryption, production/staging data mutation, retention/deployment change, production agent execution, owner reassignment, table deletion or Phase 5 work.
