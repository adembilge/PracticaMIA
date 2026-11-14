# Vercel and Neon deployment

PracticaMIA is organized as two deployable services sharing one reviewed Git commit:

| Service | Repository directory | Vercel project | URL |
| --- | --- | --- | --- |
| Web | `frontend/` | `practicamia` | https://practicamia.vercel.app |
| API | `backend/` | `practicamia-api` | https://practicamia-api.vercel.app |

The API runs Python 3.12 and FastAPI. The web app uses Next.js and server-side Auth0 sessions. The API validates RS256 access tokens against the configured issuer, JWKS and audience. Neon PostgreSQL stores owned case records and source provenance.

## Configuration

Use project-scoped, environment-specific variables; never commit or print credentials.

**Web:** Auth0 domain/client ID/client secret/session secret, audience, `APP_BASE_URL`, and HTTPS `BACKEND_API_URL`. Its private-document UI and optional model explanations have independent release flags.

**API:** database URL, OIDC issuer/audience/JWKS URL, authenticated-case feature flag, approved knowledge catalog flag, and any separately authorized reviewer or document-processing settings.

The frontend never passes access tokens to the browser; Next.js API routes call FastAPI with the authenticated user's server-side bearer token.

## Release procedure

1. Confirm the intended team, two project IDs, protected branch, commit SHA, build environment and database target.
2. Verify GitHub Actions (backend tests, frontend tests, TypeScript/build, and isolated browser acceptance). Inspect the exact code to be deployed.
3. Create a restore point and migrate Neon through the repository's Alembic head using reviewed, non-destructive operations. Verify cases, reviewed source versions and table counts before and after.
4. Deploy the **API** at the reviewed SHA, verify `GET /health` and protected routes in `/openapi.json`. Require the correct schema version.
5. Deploy the **web app** at the **same SHA**. Check its environment values and Auth0 callback/redirect allowlist; do not substitute preview secrets for production.
6. Sign in with authorized test accounts and execute the hosted case journey: create, scope, confirm intake, inspect current citations, mark actions read, resume, download PDF, and verify another account cannot access the case.
7. Check no personal-document API became active without separate security approval. Inspect runtime errors, recording evidence, the release SHA and deployment IDs.

**Important:** A successful backend deployment does not imply that the frontend was updated. A Vercel quota failure or pending build must be reported as incomplete rather than silently bypassed. A preview build is not automatically production-compatible.

## Recovery

Keep the last known-good production deployment and Neon recovery plan. Revert or promote an already tested production-compatible deployment only after confirming its environment and database compatibility. Avoid rolling back schema changes by dropping case tables or approved source evidence.

## Security boundaries

The case API and knowledge catalog are distinct from protected reviewer actions. Private documents, local extraction and RAG services are independently gated. Government portal submission is not part of this application.

Further controls: [private document vault release](PRIVATE_DOCUMENT_VAULT_RELEASE.md), [unified case workflow](UNIFIED_CASE_WORKFLOW.md), and [development workflow](DEVELOPMENT_WORKFLOW.md).
