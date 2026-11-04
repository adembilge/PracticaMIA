# PracticaMIA — Vercel FastAPI + Neon rollout

**Purpose:** Host FastAPI on a separate Vercel project and PostgreSQL on Neon's free plan. Do not expose the case API until authentication and database access have both been verified.

## Architecture

- Existing Vercel project `practicamia`: Next.js frontend, unchanged.
- New Vercel project `practicamia-api`: Python 3.12 FastAPI with root directory `backend`, using `backend/index.py`.
- Neon Postgres: provision a free project in an EU region if available. Use its **pooled** connection string for serverless runtime and a suitable direct connection for controlled migrations.
- Auth0: the authenticated case API requires an RS256 JWT with the configured issuer, audience and signing keys. The public frontend login is a separate workstream.

## Initial deployment safety

The backend uses `ENABLE_DEMO_CASE_API=0` by default. In that state only `/health` and FastAPI's metadata/documentation routes are present. Do not turn on case routes without verifying all requirements below.

## Phase A — Vercel backend project

1. Create Vercel project `practicamia-api` linked to GitHub repository `adembilge/PracticaMIA`, with Root Directory **`backend`** and framework **FastAPI**.
2. Choose function region Frankfurt (`fra1`) to be close to EU-hosted PostgreSQL.
3. Deploy the feature branch before promoting to production. Check `GET /health` returns `{"status":"ok","service":"practicamia-backend"}`.
4. The existing frontend project and domain must not be modified during this step.

## Phase B — Neon Postgres

1. Provision Neon Free in a European region and create a database for PracticaMIA.
2. Attach Neon to the backend Vercel project or set a **sensitive** `DATABASE_URL` on that project only. Never commit or log its value.
3. SQLAlchemy uses the `psycopg` v3 driver; connection URLs must use the prefix `postgresql+psycopg://`. Keep TLS enabled (`sslmode=require`).
4. For serverless functions, prefer Neon's pooled URL to reduce connection exhaustion. Run database migrations using a direct connection under a controlled process.
5. Apply Alembic migrations **before** enabling case endpoints. From `backend/`, with a temporary direct-connection `DATABASE_URL` provided securely, run `python -m alembic -c alembic.ini upgrade head`.
6. Test schema version, network reachability and owner isolation. Never run migrations from every Vercel function invocation.

## Phase C — Auth0 and backend activation

Configure sensitive backend-only variables:

| Variable | Required value |
| --- | --- |
| `ENABLE_DEMO_CASE_API` | `1` only after all other prerequisites pass |
| `DATABASE_URL` | Neon PostgreSQL pooled URL using SQLAlchemy's `postgresql+psycopg://` scheme and TLS |
| `AUTH_ISSUER` | Exact Auth0 issuer URL with trailing slash |
| `AUTH_AUDIENCE` | Auth0 API identifier matching the frontend's requested audience |
| `AUTH_JWKS_URL` | Auth0 JWKS HTTPS endpoint |

After checking Auth0 token signature and per-user access, set `BACKEND_API_URL` only on the **frontend Vercel project**, pointing to this backend's stable HTTPS domain. Frontend access tokens must remain server-side.

## Important limits

- The Vercel FastAPI runtime is serverless: do not rely on persistent process memory, background threads or local filesystem data surviving requests.
- PostgreSQL is separate; data persists independently of function instances. Avoid long-lived global sessions and connection leaks.
- Synthetic demo cases only. No real personal addresses or documents until a privacy/security review and an actual end-to-end login test.
- Neon Free resource limits and Vercel Hobby function limits apply. Database inactivity and cold starts can increase latency.
- Keep Neon and the function in nearby EU regions, and evaluate data processing, backups, logs, retention and regulatory obligations before real user data.

## Verification

Backend CI tests the Python entrypoint, API auth and PostgreSQL migrations. Vercel deployment must separately pass its Python build and a live `/health` request.

References: https://vercel.com/docs/frameworks/backend/fastapi and https://vercel.com/marketplace/neon
