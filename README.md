# PracticaMIA
> **Independent system audit (6 November 2026):** [production GET smoke, adversarial authorization, provenance integrity, quota concurrency, and release blockers](docs/audits/INDEPENDENT_SYSTEM_AUDIT_2026_11_06.md). Experimental demo only; not yet suitable for public administrative advice.


PracticaMIA is an independent English–Italian administrative-guidance prototype, initially focused on selected individual changes of registered residence within Milan (`cambio di residenza`). It helps users organize preparation steps; **it is not a government service and cannot submit an official application**.

- **Frontend:** [practicamia.vercel.app](https://practicamia.vercel.app) — Next.js.
- **Backend:** [practicamia-api.vercel.app](https://practicamia-api.vercel.app) — FastAPI.
- **Source:** [github.com/adembilge/PracticaMIA](https://github.com/adembilge/PracticaMIA).

## Current functionality (November 2026)

| Area | Status | What works |
| --- | --- | --- |
| Bilingual frontend | Implemented | English/Italian demo, guided scope questions, illustrative checklist and review |
| Authentication | Deployed | Auth0 Regular Web Application, server-side Next.js session, login/logout |
| Case API | Deployed | JWT-verified FastAPI, per-user authorization, synthetic case CRUD |
| Database | Deployed | Neon PostgreSQL, SQLAlchemy, Alembic schema at `20261104_0002` |
| Frontend–backend bridge | Deployed | Same-origin Next.js routes fetch Auth0 access tokens server-side; browser never receives API tokens |
| Saved-case workspace | Implemented and deployed | Link to a saved case, answer five synthetic scope questions, save/resume, edit and delete |
| Official-source registry | Merged, disabled pending migration | Versioned municipal source candidates, approval-gated read API; no approved evidence yet |
| Official HTML and PDF snapshots | PDF support merged, production-disabled | Controlled original-byte acquisition, versioned snapshots and hash-linked passages |
| Reviewer-only source approval | Merged, not production-enabled | Verified reviewer allowlist, hash-confirmed approval/revocation and audit records |
| Approved passage lexical search | Merged, production-disabled | PostgreSQL full-text ranking, jurisdiction/procedure filters, versioned citations and integrity gates |
| Neon knowledge staging | Isolated, validated | Branch `staging-knowledge-0003-0006-2026-11-05` migrated to `0008` with pgvector 0.8.0 and a daily-model-usage table; 17 source candidates, one historical PDF pending review, zero approved sources or embeddings |
| Official knowledge and rules | Research draft | No approved production eligibility rules or authoritative personalized checklist |
| LangChain/RAG foundation | Development code, disabled in production | Approved-only pgvector hybrid retrieval and LangChain two-step answer tests; no public RAG endpoint or configured model |
| Authenticated assistant Q&A preview | Implemented, disabled by default | Case-bound FastAPI route and Next.js preview UI with exact-source quote validation and pseudonymous daily model budget; no model configured |
| Documents and submission | Not implemented | No real personal data, document uploads, ANPR login or government submission |

The current scope check is **only a synthetic product filter**, not a determination of legal eligibility. Do not enter real names, addresses, identity documents, or SPID/CIE credentials.

## Product journey

1. Sign in at `/account` using Auth0.
2. Create a synthetic case under `/cases/saved`.
3. Open `/cases/{id}` to answer the five demo scope questions.
4. Save each answer, leave, and resume the same case later. Editing an earlier answer clears dependent later answers.
5. Inspect the saved summary, return to the case list, or delete the synthetic case.

The unauthenticated `/cases/new` and `/cases/demo` experience remains a separate, in-memory demonstration. Real-world intake fields and official administrative rules are **not** stored in the authenticated workflow.

## Architecture

```text
Browser — HTTPS — Next.js (Auth0 encrypted session)
                     |
                     | same-origin /api/cases/* server routes
                     | server-side Auth0 audience access token
                     v
                   FastAPI (RS256 JWKS, issuer, audience, case ownership)
                     |
                     v
                  Neon PostgreSQL (synthetic cases and scope answers)
```

The backend refuses case API startup unless trusted OIDC settings, a database URL and `ENABLE_DEMO_CASE_API=1` are configured. Missing or invalid bearer tokens return `401`; access to another user's case returns `404`. Mutating frontend proxy routes check the request Origin. Credentials live in Vercel environment variables; **do not commit secrets or copy them into issues**.

## Local development

```bash
cd frontend
npm ci
npm test
npm run typecheck
npm run dev
```

Frontend preview: `http://localhost:3000`. Without the required Auth0 server-side configuration, account operations are intentionally unavailable; the anonymous demonstration works independently.

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
docker compose up -d db
python -m pytest -q
```

See [backend/README.md](backend/README.md) for PostgreSQL, Alembic, OIDC configuration and API endpoints. On Windows, activate `.venv\Scripts\Activate.ps1`.

## Quality and release workflow

Work on a feature branch and open a pull request to protected `main`. GitHub Actions runs:

- **Backend CI:** pytest; a PostgreSQL migration from the legacy schema; authenticated CRUD, ownership and migration smoke tests.
- **Frontend CI:** unit tests, TypeScript typecheck and production Next.js build.

Review the Vercel preview deployment before merging. The saved-case milestone and its acceptance criteria are documented in [docs/CASE_WORKSPACE.md](docs/CASE_WORKSPACE.md). Environment variables are managed separately for production and preview; do not automatically enable Auth0 or real data on untrusted previews.

## Documentation

- [First user journey](docs/FIRST_USER_JOURNEY.md)
- [UX interface specification](docs/UX_INTERFACE_SPEC.md)
- [Authentication integration](docs/AUTHENTICATION_INTEGRATION.md)
- [Case workspace milestone](docs/CASE_WORKSPACE.md)
- [Official-source registry design](docs/OFFICIAL_SOURCE_REGISTRY.md)
- [Controlled official HTML snapshots](docs/CONTROLLED_SOURCE_SNAPSHOTS.md)
- [Knowledge review and audit workflow](docs/KNOWLEDGE_REVIEW_WORKFLOW.md)
- [Approved passage lexical search](docs/APPROVED_PASSAGE_SEARCH.md)
- [Synthetic retrieval evaluation and quality gates](docs/RETRIEVAL_EVALUATION.md)
- [LangChain + pgvector development foundation](docs/LANGCHAIN_PGVECTOR_FOUNDATION.md)
- [Authenticated RAG Q&A preview, controls and release gates](docs/AUTHENTICATED_RAG_PREVIEW.md)
- [Verified 5 November 2026 release and evidence blockers](docs/RELEASE_BLOCKERS_2026_11_05.md)
- [Official-source acquisition queue, validated batch import and review](docs/OFFICIAL_SOURCE_INTAKE.md)
- [5 November 2026: 14 official webpage requests, all HTTP 403](docs/OFFICIAL_HTML_ACCESS_AUDIT_2026_11_05.md)
- [Browser-rendered municipal pages: labeled provenance and human review](docs/BROWSER_CAPTURE_EVIDENCE.md)
- [Preview-only mobile browser-source review workflow](docs/MOBILE_BROWSER_SOURCE_REVIEW.md)
- [Approved-only staging embedding indexer: dry-run, explicit transfer, rollback](docs/APPROVED_EMBEDDING_INDEXING.md)
- [Knowledge staging migration and source acquisition report](docs/KNOWLEDGE_STAGING_ROLLOUT.md)
- [Milan official-source acquisition inventory (17 unapproved candidates)](docs/MILAN_OFFICIAL_SOURCE_ACQUISITION.md)
- [Manual PDF and HTML source ingestion](docs/PDF_SOURCE_INGESTION.md)
- [User-uploaded non-EU Allegato A: staging import and review caveats](docs/ALLEGATO_A_STAGING_INGESTION.md)
- [New original-file download leads and acquisition queue](docs/OFFICIAL_DOCUMENT_DOWNLOAD_QUEUE.md)
- [Development workflow](docs/DEVELOPMENT_WORKFLOW.md)
- [Milan residence-change research](research/milan_residence_change.md)
- [Complete original project specification](PracticaMIA_Complete_Project_Specification.md)

Production Neon is intentionally at migration `20261104_0002`; the isolated knowledge staging branch has migrated to `20261105_0008` with pgvector 0.8.0 and persistent model-call quota tracking. The staging vector index exists, but no embeddings have been generated. The backend's Production and staging Preview `DATABASE_URL` variables are now separated; staging credentials are restricted to the trusted `feature/knowledge-staging-rollout` preview branch, so other previews receive no database URL. The original specification's 94-task roadmap is reference material, **not** the current completion status. Next milestones are authentic reviewed-source acquisition, representative hybrid retrieval evaluation, controlled embedding-model selection, deterministic administrative rules, and an authenticated, evidence-gated LangChain RAG endpoint. Security work still includes live multi-user isolation checks, audit/retention policies, rate limiting, monitoring and backups.

**PracticaMIA does not represent or act on behalf of a municipality or the Italian government.**
