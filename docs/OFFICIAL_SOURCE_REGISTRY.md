# Official-source registry — milestone 44

**Status:** Feature PR. The core registry is implemented behind a disabled-by-default feature flag. It is **not** a RAG system, approved requirements catalog, or government submission service.

## Why this exists

Milan residence-change guidance must cite the exact institution, jurisdiction, source document, version, and review date. Sources discovered online are not automatically trusted administrative rules. The original research in `research/milan_residence_change.md` remains a draft; its procedure descriptions must not silently become binding decisions.

## Candidate inventory

Four manually curated Comune di Milano URL references are bundled in `backend/app/knowledge/candidate_sources.json`:

| ID | Subject |
| --- | --- |
| `milano-residence-change` | Main municipal change-of-residence service |
| `milano-residence-faq` | General Milan residence-change FAQ |
| `milano-foreign-rental-documents` | Foreign rental housing document FAQ |
| `milano-foreign-resident-change` | Change for foreign residents already in Italy |

**All four are candidates, not reviewed or approved.** The URLs originate from the 3 November research document and were cross-checked against municipal search results on 4 November 2026. Automated direct fetching of some municipal help-center pages was blocked; no text snapshot or content hash is asserted for these candidates.

## Schema and source status

Alembic revision `20261104_0003` adds:

- `knowledge_sources`: stable source ID, institution, jurisdiction, procedure, language, title, official URL, document type, discovery timestamp, review state, active version ID.
- `knowledge_source_versions`: immutable-intended version number, SHA-256 hash of a future verified snapshot, retrieval timestamp, review timestamp and reviewer, approval state.

A source is **never** eligible for trusted retrieval unless:

1. the source status is `approved`;
2. its `active_version_id` points to a version owned by that same source;
3. that version status is `approved`;
4. both `reviewed_at` and `reviewed_by` are set;
5. the snapshot hash is a lowercase 64-character SHA-256 digest.

The registry currently has **no** user-facing approval operation, no automatic activation, and no text snapshots. Human review, snapshot immutability, approval authentication, content extraction, and provenance-preserving passage storage are deliberately deferred to subsequent PRs.

## Safe migration / rollout

Development / CI:

```bash
cd backend
python -m alembic -c alembic.ini upgrade head
python -m app.knowledge.seed_candidates
# Prints candidate count without writing.
python -m app.knowledge.seed_candidates --apply
# Explicitly registers only missing candidate metadata.
```

**Production order requires human review/approval:**

1. Back up or verify restore capability for Neon.
2. Run migration `20261104_0003` against the intended Neon branch/database.
3. Optionally run candidate seeding with `--apply`. It is idempotent and never modifies existing sources, their approvals, or their versions.
4. Only once migrated, configure backend `ENABLE_KNOWLEDGE_CATALOG_API=1` in the intended environment and redeploy.
5. With no reviewed versions, a signed-in request to `GET /api/v1/knowledge/sources` returns `{"status":"insufficient_evidence","sources":[]}`. This is the correct initial result.

The feature flag defaults to **off**. Merging this code alone does not require an immediate production database migration and does not affect existing authenticated case CRUD.

## API

`GET /api/v1/knowledge/sources` is available only when both `ENABLE_DEMO_CASE_API=1` and `ENABLE_KNOWLEDGE_CATALOG_API=1`, with valid Auth0 bearer authentication. It exposes metadata for approved active versions, not their text. Pending, revoked, superseded, mislinked or unreviewed versions are absent.

**Never use this endpoint to answer legal questions unless approved snapshots and passage-level citations have been implemented.** An empty result is not a negative legal determination.

## Next work

1. Implement controlled manual acquisition with allowlisted domains, rate limits, and source-usage compliance.
2. Create verifiable immutable HTML/PDF snapshots, extract passages and provenance, calculate hashes, and record changes.
3. Create a reviewer-only approve/revoke workflow with audit records and stale-source invalidation.
4. Implement approved-passage indexing and hybrid lexical/vector retrieval, with deterministic tests.
5. Establish linked, human-reviewed administrative rules and citation resolution; only then connect the knowledge tool to LangGraph.

## Security boundaries

- No arbitrary client URL ingestion; candidate URLs require HTTPS, official allowlisted hosts, a valid Milan procedure/jurisdiction, and no credentials/query strings.
- No raw user documents or Auth0 identifiers are stored in the shared knowledge corpus.
- No external requests occur when validating or seeding candidates.
- Never infer user eligibility from mere source metadata.
