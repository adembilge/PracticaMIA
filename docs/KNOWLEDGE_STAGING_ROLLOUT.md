# Knowledge Staging Rollout — 5 November 2026

**Status:** Schema and source-candidate registration completed on a separate Neon staging branch. Official HTML snapshots are **not** ingested or approved. Production remains on revision `20261104_0002`.

## Targets and separation

| Resource | Environment | Current state |
| --- | --- | --- |
| Neon `practicamia` branch `main` | Production | `20261104_0002`, unchanged |
| Neon branch `staging-knowledge-0003-0006-2026-11-05` | Staging | `20261105_0006`, five knowledge tables and PostgreSQL GIN index present |
| Vercel backend `DATABASE_URL` | Production | Production-only secret |
| Vercel backend `DATABASE_URL` | Trusted staging preview branch only | Separate, branch-scoped sensitive Neon staging credential; other preview branches have no database URL |
| Vercel backend branch `feature/knowledge-staging-rollout` | Preview | Case API, knowledge catalog and search enabled with verified Auth0 JWT checks |
| Review/approval API | All previews | Disabled unless explicitly configured; do not enable without a reviewer authorization test |

The Neon staging branch was cloned from production, retaining two existing **synthetic** case records and their authenticated owner identifiers. Because the cloned branch is not an empty test fixture, its database credential is scoped only to the trusted `feature/knowledge-staging-rollout` preview branch, not all pull-request previews. Do not treat its contents as fresh anonymous test data or publish its connection credentials. Do not direct production traffic to this branch.

## Migration evidence

On staging, the SQL equivalent of the Alembic migrations below was applied in four individual transactions, maintaining `alembic_version` after each successful transaction:

- `20261104_0003`: source registry and versions, constraints and indexes
- `20261105_0004`: raw snapshot and extracted passage tables
- `20261105_0005`: review and change-invalidation audit table
- `20261105_0006`: `ix_knowledge_passages_fts_simple` PostgreSQL GIN index

Database inspection confirms all five tables, the GIN index, and head revision `0006`. GitHub Actions additionally runs the **actual Alembic upgrade** from legacy revision `0001` to head on disposable PostgreSQL; this remains the authoritative code-path integration test. We did not directly execute the Alembic CLI against Neon staging.

Recheck staging without changing data:

```sql
SELECT version_num FROM alembic_version;

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_name LIKE 'knowledge_%'
ORDER BY table_name;

SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname = 'ix_knowledge_passages_fts_simple';

SELECT id, status, active_version_id
FROM knowledge_sources ORDER BY id;

SELECT COUNT(*) FROM knowledge_source_versions;
SELECT COUNT(*) FROM knowledge_review_events;
```

## Curated candidate registration

Four source metadata records were inserted with `status = 'candidate'` and no active version:

| Source ID | Municipality page |
| --- | --- |
| `milano-residence-change` | `https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza` |
| `milano-residence-faq` | `https://servizicrm.comune.milano.it/centro-supporto/KA-00330/` |
| `milano-foreign-rental-documents` | `https://servizicrm.comune.milano.it/centro-supporto/KA-00329/Residenza-stranieri-in-affitto-documenti-immobile` |
| `milano-foreign-resident-change` | `https://servizicrm.comune.milano.it/centro-supporto/KA-00597/Cambio-residenza-per-stranieri-gia-in-Italia` |

Municipality search results independently corroborate these URLs and titles as of 5 November 2026. The legal notes page indicates the municipal website generally uses Creative Commons terms unless otherwise specified, with source attribution and original links required; verify the precise page's terms before reuse.

**Important acquisition blocker:** Direct attempts to retrieve these municipal pages via the available automated source-opening service returned HTTP 403. Search result excerpts are **not the original HTML bytes** and must never be used to manufacture a hash-bound snapshot, fake an approval, or claim that the source is current. No first source was honestly approvable in this session.

## Completing official snapshot acquisition and approval

1. Independently open the official page in a normal browser, verify page identity, publication/revision date and applicable reuse terms. Do not bypass a site block or scrape behind authentication.
2. Obtain a faithful UTF-8 HTML snapshot through a permitted download, without modifying the text. Save the exact bytes to a local HTML file; do not upload private user data or credentials.
3. Set `DATABASE_URL` in a secure local environment to the **staging branch connection string**, never production; do not commit or print it.
4. Run `python -m app.knowledge.ingest_source --source-id milano-residence-change --file <local-official-snapshot.html>` for a dry run, then repeat with `--apply` after checking the source and extraction.
5. Verify the new version is `pending_review`, the stored raw-byte SHA-256 matches the acquired HTML, passages reproduce faithfully, and the official URL matches. A text summary is insufficient.
6. Enable `ENABLE_KNOWLEDGE_REVIEW_API=1` **only in an isolated reviewer-authorized environment**, with a precisely configured `KNOWLEDGE_REVIEWER_SUBJECTS` allowlist of verified Auth0 subject IDs.
7. A human reviewer independently compares the exact original page, plain-text extraction, legal context and coverage. The reviewer submits the hash and a substantive review note through the review API.
8. Confirm an `approved` audit event is stored and a real authenticated search returns the reviewed passage with a resolvable citation. Test revocation and source-change invalidation before enabling any AI output.

**Do not approve a synthetic fixture or reconstructed content while presenting it as official municipal evidence.** If the site does not permit direct HTML acquisition, keep the candidate pending and use an officially obtainable document or request permission instead.

## Current CI and deployment audit

The historical failed backend CI on feature commit `66a21af94c` was caused by two snapshot tests manually marking versions `approved` without the new required review-audit event. Commit `06a9284034` corrected those tests to use the real reviewer approval service. Both feature CI workflows and the final merged `main` workflows passed.

All current inspected production and recent feature deployments showed `READY`. The backend and frontend Vercel runtime-error summaries showed **no errors in the selected three-hour window**. Failed historical GitHub check runs remain visible for audit purposes.

Before merging this runbook PR, check the new branch's backend preview reports `200 /health`, `401` for an unauthenticated knowledge query, and no review API exposure. Production flags and database remain unchanged.

## Production rollout gate

Do not advance production Neon to `0006` until the team verifies backup/restore procedures, a tested staging migration, the source-review permissions and audit checks, and the source acquisition method. The production database has no approved official evidence, so the user-facing app should continue returning demo-only guidance.
