# PracticaMIA

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
| Saved-case workspace | In this milestone | Link to a saved case, answer five synthetic scope questions, save/resume, edit and delete |
| Official knowledge and rules | Research draft | No approved production eligibility rules or authoritative personalized checklist |
| LangGraph/RAG | Not implemented | Planned bounded agent and reviewed-source retrieval |
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
- [Development workflow](docs/DEVELOPMENT_WORKFLOW.md)
- [Milan residence-change research](research/milan_residence_change.md)
- [Complete original project specification](PracticaMIA_Complete_Project_Specification.md)

The original specification's 94-task roadmap is reference material, **not** the current completion status. Subsequent milestones are approved official sources, a versioned knowledge registry, deterministic requirements, RAG, LangGraph orchestration, and reviewed application preparation. Security work still includes live multi-user isolation checks, audit/retention policies, rate limiting, monitoring and backups.

**PracticaMIA does not represent or act on behalf of a municipality or the Italian government.**
