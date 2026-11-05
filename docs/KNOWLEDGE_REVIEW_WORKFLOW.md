# Reviewer-only government source approval — milestone 45.4

**Status:** Merged into main; production migration and activation still require explicit review.
**Scope:** Human-controlled approval and revocation of one exact source snapshot version.
**Not in scope:** Automated legal decisions, end-user reviewer UI, government submission, vector search, ingestion of real identity documents.

## Trust model

An official-source *candidate* is not a trustworthy basis for RAG. Extraction and SHA-256 hashes prove reproducibility, not that the guidance is legally current or universally applicable.

Only a **trusted JWT principal whose exact subject ID is configured server-side** may inspect review snapshots, approve sources, revoke sources, or read the review audit. Auth0 role claims, client-supplied identity fields, and arbitrary HTTP headers do not grant reviewer access.

Review API configuration is fail-closed:

- `ENABLE_DEMO_CASE_API=1` (existing signed-JWT case API)
- `ENABLE_KNOWLEDGE_CATALOG_API=1`
- `ENABLE_KNOWLEDGE_REVIEW_API=1` — defaults to **disabled**
- `KNOWLEDGE_REVIEWER_SUBJECTS` — comma-separated, verified Auth0 `sub` identifiers; a non-empty allowlist is required to start the review API

**Do not put private tokens or identifiers in the repository.** Provision the reviewer allowlist in protected backend environment settings. Use narrow reviewer membership and periodically review access. Do not infer `sub` from display names, email addresses, or request bodies.

## API

All paths below require `Authorization: Bearer <reviewer-access-token>`, whose RS256 signature, issuer, audience and validity are checked by the existing backend. Non-reviewers receive **403**; no valid bearer means **401**.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/knowledge/review/queue` | List pending review versions and source metadata |
| GET | `/api/v1/knowledge/review/versions/{version_id}` | View verified normalized **plain text**, passages, SHA-256 and official URL |
| POST | `/api/v1/knowledge/review/versions/{version_id}/approve` | Activate the **latest** pending version after hash attestation |
| POST | `/api/v1/knowledge/review/versions/{version_id}/revoke` | Revoke an active version |
| GET | `/api/v1/knowledge/review/sources/{source_id}/history` | Inspect append-only decision and change-invalidation records |

Approval/revocation request body:

```json
{
  "expected_sha256": "<exact lowercase SHA-256 displayed in the reviewed snapshot>",
  "review_note": "I checked the version, official URL, content and relevant applicability."
}
```

The note must be at least 20 characters. Unexpected request fields are rejected. All decision outcomes are transactional. The API does **not** allow uploading a document, choosing an arbitrary URL, bypassing approval, or changing the reviewer identity.

Before approving, the reviewer must independently verify the actual municipal URL, applicable jurisdiction, document meaning and procedural scope. A matching hash confirms only that the *same stored bytes* were reviewed; it does not verify the official publisher or the legal content by itself.

## Approval invariants

Approval requires:

1. The source is a `candidate` with no active version, and the selected source version is `pending_review`.
2. The selected version is the **latest** revision for that source.
3. The supplied hash exactly matches the pending version hash.
4. The stored original HTML bytes, extraction, passage hashes and offsets pass recomputation and integrity verification.
5. The snapshot's recorded official URL exactly matches the registered source URL.
6. The signed reviewer ID comes from the server allowlist, not a request claim/body.
7. One DB transaction sets source/version to `approved`, records reviewer and review time, points `active_version_id` at the approved version, and inserts a decision audit event.

Revocation only applies to the active approved version. The transaction clears the active pointer, marks the source and version `revoked`, and records the reviewer, timestamp, reason, and hash.

If a newer snapshot is ingested, the source changes to `candidate`, the active pointer is removed, and an audit event with action `source_changed` records automatic invalidation. Older approved versions remain historical data, never active evidence.

The source row is locked during reviewer decisions and source ingestion on PostgreSQL, reducing approval/ingest races. A rejected hash, stale revision, invalid snapshot or invalid reviewer fails closed with no audit decision committed.

## Audit records and migration

Alembic migration `20261105_0005` creates `knowledge_review_events` with:

- action (`approved`, `revoked`, `source_changed`)
- source and source-version IDs
- verified actor subject (`system:ingestion` for automated invalidation)
- reason, raw-body SHA-256, before/after source and version states, timestamp

The API exposes **read-only** audit history. Application code does not modify or delete events. This is append-only at the service layer, **not yet an independently tamper-evident log** against database administrator privileges. Database-level immutable audit controls, backup/restore and access review remain production-hardening tasks.

## Staged rollout and operational checklist

- [ ] Review and merge the feature branch after GitHub CI passes.
- [ ] Confirm backups or a tested Neon restore point; test on a disposable Neon branch.
- [ ] Apply migrations `20261104_0003`, `20261105_0004`, then `20261105_0005` in order.
- [ ] Register only curated official candidate metadata and ingest faithful, permitted HTML snapshots after confirming site usage conditions.
- [ ] Test the queue, preview, hash mismatch, reviewer denied, approval, revocation and audit history with *synthetic fixtures*.
- [ ] Provision the exact trusted reviewer Auth0 `sub` allowlist and enable backend flags only after verification.
- [ ] Independently review each acquired official snapshot before approving; no bulk automatic approval.
- [ ] Verify that the user-facing approved catalog contains **zero** sources until actual human approval, and hides changed or revoked sources.
- [ ] Monitor access, audit changes, restore capability, failures and permissions.

Do not run migrations or enable reviewer endpoints in production as part of merging this PR. The production application can continue its synthetic-case workflow without any knowledge flags.

## Follow-up

The follow-up [approved-passage lexical search](APPROVED_PASSAGE_SEARCH.md) adds PostgreSQL full-text indexing, jurisdiction/procedure/version filters and exact resolvable citation IDs. pgvector and hybrid retrieval can follow once human-reviewed evidence fixtures and retrieval evaluations exist.
