# PracticaMIA — Authenticated Case API (development)

**Status:** Deployed synthetic-case API on Vercel. Auth0 JWT verification and owner-scoped Neon PostgreSQL persistence are active in production; never send real personal information.

The FastAPI case API now requires **signed JWT access tokens** and isolates stored cases by their verified owner. It handles **synthetic scope answers only**, with no names, addresses, documents or real administrative data. It does not determine official eligibility.

## Security model

- `ENABLE_DEMO_CASE_API` defaults to **off**. The health endpoint stays available.
- To enable the case API, configure trusted `AUTH_ISSUER`, `AUTH_AUDIENCE`, and HTTPS `AUTH_JWKS_URL`. Missing settings fail at startup.
- Every case request must use `Authorization: Bearer <access_token>`. The server validates the RS256 signature, issuer, audience, `exp`, `iat`, and nonempty `sub` against the trusted JWKS.
- A case's `owner_subject` is derived only from the verified subject claim, never from request JSON or an arbitrary identity header.
- Only the owner can list, read, modify or delete a case; other users receive `404` even when they know its ID.
- Previous anonymous demo records have NULL owners after migration and cannot be accessed through the API; decide retention and cleanup before production.
- The owner identifier is omitted from API responses. Case IDs are not proof of ownership.

**Important:** Auth0 is now configured for the production Next.js frontend; Vercel hosts the FastAPI API and Neon stores synthetic demo records. Rate limiting, audit events, documented retention and deletion policies, backup/restore exercises and production privacy review remain outstanding. Do not store real personal data.

## Local PostgreSQL development

Requires Python 3.12, Docker Compose, and a trusted OIDC provider capable of issuing RS256 **access tokens** for the API's audience. Provider selection and configuration come next; do not commit credentials, tokens or private keys.

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
docker compose up -d db
export DATABASE_URL='postgresql+psycopg://practicamia:local_development_only@127.0.0.1:5432/practicamia'
export AUTH_ISSUER='https://YOUR-TRUSTED-ISSUER/'
export AUTH_AUDIENCE='YOUR-API-AUDIENCE'
export AUTH_JWKS_URL='https://YOUR-TRUSTED-ISSUER/.well-known/jwks.json'
export ENABLE_DEMO_CASE_API=1
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

These issuer/JWKS values are placeholders, not an operational identity provider. Confirm the provider's actual configuration. To run `/health` without identity setup, leave `ENABLE_DEMO_CASE_API=0`.

Windows PowerShell: activate `.venv\Scripts\Activate.ps1` and set variables with `$env:NAME='value'`.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Health check; no authentication |
| POST | `/api/v1/cases` | Create a new synthetic case for the authenticated owner |
| GET | `/api/v1/cases` | List up to 50 synthetic cases belonging to the owner |
| GET | `/api/v1/cases/{id}` | Read an owned case |
| PATCH | `/api/v1/cases/{id}/scope` | Update an owned case's demo answers |
| DELETE | `/api/v1/cases/{id}` | Delete an owned case |

All case endpoints reject missing or invalid access tokens with `401`. Other owners' and older anonymous cases return `404`. `provisionally_in_scope` means **demo filtering only**, not a legal eligibility decision.

## Automated tests

```bash
cd backend
python -m pip install -e '.[dev]'
python -m pytest -q
```

Tests generate ephemeral RSA keys and locally signed tokens, requiring no external provider. They verify invalid/missing credentials, expiration, signatures, issuer, audience, ownership isolation and persistence. GitHub Actions migrates PostgreSQL from `20261104_0001` to `20261104_0002`, checks that legacy anonymous cases stay inaccessible, and tests authenticated CRUD.

## Next milestones

1. Connect the guided, synthetic scope questionnaire to saved cases through same-origin Next.js server routes (see `docs/CASE_WORKSPACE.md`).
2. Add audit events, rate limiting, retention and deletion rules, and separate production user-isolation smoke tests.
3. Review official Milan/ANPR sources before making any legal requirements executable; keep all user inputs synthetic until a privacy assessment is complete.

Production configuration is managed in Vercel, not committed to Git. Required backend keys: `DATABASE_URL`, `ENABLE_DEMO_CASE_API=1`, `AUTH_ISSUER`, `AUTH_AUDIENCE`, and `AUTH_JWKS_URL`.

## Official government source registry (feature milestone)

A new read-only, authenticated knowledge catalog is staged behind `ENABLE_KNOWLEDGE_CATALOG_API=0` by default. Revision `20261104_0003` introduces official-source and source-version metadata tables **without altering existing cases**. No automatic source approval or legal rules exist. Review [the source registry design](../docs/OFFICIAL_SOURCE_REGISTRY.md) before migrating or enabling this API.

After the migration has been reviewed and applied in the target database, source candidates can be validated with `python -m app.knowledge.seed_candidates` or inserted with explicit `--apply`. Import only creates pending candidate metadata; it never activates an approved source. Once the schema exists, enabling `ENABLE_KNOWLEDGE_CATALOG_API=1` exposes `GET /api/v1/knowledge/sources` to authenticated callers; an empty, unreviewed registry deliberately returns `insufficient_evidence`.

## Controlled official HTML snapshots (merged foundation)

The source ingestion milestone adds revision `20261105_0004` with two additional tables for bounded HTML snapshots and exact-offset, content-hashed passages. No automated crawling, approval, or public ingest API is enabled. `httpx` supports explicit operator-only single-URL fetching with HTTPS host allowlisting and redirect refusal. A changed source is returned to `candidate` state and its active approval is cleared until separately reviewed.

See [controlled source snapshots](../docs/CONTROLLED_SOURCE_SNAPSHOTS.md) for dry-run commands, a local HTML ingestion example, security boundaries and migration prerequisites. Production Neon is currently at migration `20261104_0002`; PRs 9 and the snapshot PR require separate review of additive migrations `0003` and `0004` before any knowledge-API flag is enabled.

## Reviewer-only knowledge source approval (merged foundation)

Milestone 45.4 adds authenticated reviewer operations and append-only audit events. The review API is **disabled by default** and requires `ENABLE_KNOWLEDGE_REVIEW_API=1`, `ENABLE_KNOWLEDGE_CATALOG_API=1`, and a non-empty server-side `KNOWLEDGE_REVIEWER_SUBJECTS` allowlist of exact Auth0 subject IDs. Requests must use valid bearer access tokens; normal signed-in users are **not** reviewers. See [reviewer permissions, approvals and audit](../docs/KNOWLEDGE_REVIEW_WORKFLOW.md).

New additive migration: `20261105_0005`, on top of `20261105_0004`. No reviewer API or knowledge source is activated by merging. Do **not** apply production migrations or enable flags without reviewing backups, database target and source provenance. A hash-matched reviewed snapshot can be approved or revoked atomically, with a recorded actor and reason. Source changes invalidate active approval and append a system audit event.

## Approved-passage lexical search (feature PR)

Milestone 50.4 foundation adds feature-gated `GET /api/v1/knowledge/search` and `GET /api/v1/knowledge/passages/{citation_id}`. Query inputs must include verified jurisdiction, procedure and language; only latest, active, hash-verified and reviewed passages with a matching approval audit event are returned. Missing evidence explicitly returns `insufficient_evidence`; changed or revoked citations return `404`. Query syntax is normalized to plain words and bounded to a maximum of 10 passages. This feature does **not** provide RAG/embeddings, administrative rule evaluation or government submission.

The new migration `20261105_0006` creates a PostgreSQL GIN index on `to_tsvector('simple', content)`. Search is **disabled by default** with `ENABLE_KNOWLEDGE_SEARCH_API=0`; enable only after the source registry is migrated and a reviewed corpus is available. `ENABLE_KNOWLEDGE_CATALOG_API=1` and the existing authenticated case API are required. See [approved-passage search contracts and tests](../docs/APPROVED_PASSAGE_SEARCH.md). **Production Neon remains at `20261104_0002` until a reviewed knowledge rollout.**
