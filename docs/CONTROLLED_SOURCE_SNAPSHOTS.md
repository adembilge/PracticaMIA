# Controlled HTML snapshots — milestone 45.1–45.3

**Status:** Feature branch, awaiting CI and review. Nothing ingested into production automatically.

## Purpose

Turn curated municipal **source candidates** into reproducible, versioned, reviewable HTML snapshots and exact-offset text passages. The output remains **untrusted pending human review**: it is not yet RAG, an approved knowledge base, or an administrative rules engine.

Source registry milestone 44 already provides source/version provenance and a disabled-by-default read-only approved-source metadata endpoint. This task adds snapshot storage, manual acquisition, deterministic extraction, and change invalidation.

## Data model

The additive Alembic migration `20261105_0004` creates:

- `knowledge_source_snapshots`: source-version primary key, fetched URL, media type, original bounded UTF-8 HTML bytes, byte count, extraction version, and normalized text.
- `knowledge_source_passages`: stable version-scoped passage identifier, ordinal, heading/section label, exact character start/end offsets into normalized text, and passage SHA-256.

These records are linked to `knowledge_source_versions`, which already carries source ID, revision, retrieved timestamp, raw-body SHA-256, and review state.

**Data flow:**

```text
Curated municipal URL / manually saved HTML file
             |
     validate ID, HTTPS host, size, MIME, UTF-8
             |
     parse HTML with navigation/scripts excluded
             |
     preserve original bytes + normalized text
             |
     create exact-offset, hashed passages
             |
   compare raw SHA-256 to latest version
       |                         |
   unchanged                 changed
       |                         |
   no DB write            new pending_review version
                                 |
                  invalidate active approval if any
                                 |
                    human source review (future PR)
                                 |
                    indexed retrieval (future PR)
```

## Operator workflow — development database only

1. Apply both catalog and snapshot revisions with Alembic on a **disposable development database** (production migration requires a separate review).
2. Validate and register the existing candidate sources.
3. Obtain one HTML file through a permitted manual process, or explicitly opt in to a single URL fetch after reviewing the municipality's terms and `robots.txt`. Do not bypass access controls.
4. Dry-run extraction before writing. Review source validity and extracted passage integrity.

```bash
cd backend
python -m alembic -c alembic.ini upgrade head

# Candidate registration (only when needed)
python -m app.knowledge.seed_candidates --apply

# Local/manual HTML file: validation only, no database write
python -m app.knowledge.ingest_source \
  --source-id milano-residence-change --file ./sample-official.html

# Explicit write to current DATABASE_URL (no automatic approval)
python -m app.knowledge.ingest_source \
  --source-id milano-residence-change --file ./sample-official.html --apply

# Optional exact-URL fetch, after terms/robots/access review:
python -m app.knowledge.ingest_source \
  --source-id milano-residence-change --fetch
```

The operator's HTML file must be a faithful snapshot of the official page. Never import a sample/test HTML file into production as government evidence. Never commit collected page snapshots, or raw user documents, to the repository.

## Security and correctness boundaries

- Only exact curated source IDs and official HTTPS hostnames on the allowlist; no arbitrary user-selected URL.
- The remote fetch has no redirects, retries, proxy-environment inheritance, or crawling. It uses connect/overall timeouts and a maximum of **512 KiB decompressed HTML** per request; PDFs and other media are rejected.
- UTF-8 is mandatory; potentially corrupted text is rejected rather than silently replaced.
- Parser excludes `script`, `style`, `nav`, `form`, and related regions; extraction has a bounded number of passages. Complex tables and script-rendered content may be incomplete and require review.
- Every passage's span and SHA-256 are verified against stored normalized text. Snapshot bytes must match the registered version's SHA-256 before a source is exposed as trusted metadata.
- The first snapshot is revision 1 and `pending_review`. Identical bytes are idempotent; changed bytes produce revision N+1. Previous raw bytes and approved history stay intact.
- A changed source automatically clears its active approval and requires human re-review; pending versions never become approved automatically.
- The approved-source API remains disabled by default through `ENABLE_KNOWLEDGE_CATALOG_API`. No new ingest route is exposed to browsers.
- Hashing and versioning detect changes but do **not** establish legal correctness, authenticity of off-site copies, or permission to reproduce content.

## Test and rollout evidence

GitHub CI runs unit tests with synthetic HTML and a mocked network transport, including rejection of redirects/oversized pages/invalid media, exact-span integrity, idempotency, change invalidation, and tampering. PostgreSQL migration smoke confirms the new tables exist.

**Production deployment remains intentionally deferred:** check Neon backup and migration strategy, apply versions `0003` and `0004` on a reviewed database/branch, and only then consider candidate registration. Do not turn on the approved-source API without a reviewer-authenticated approval workflow and verified official snapshots.

## Next milestone

Build an authenticated reviewer-only approval/revocation service with audit events and a hash-bound manual review step, then implement review-filtered lexical retrieval and vector embeddings with evaluation fixtures. No verified administrative requirement or government decision can be inferred merely from extracted text.
