# PracticaMIA — Authenticated Case API (development)

**Status:** Milestone 3.2, code and CI only. Not publicly deployed or connected to the Vercel frontend.

The FastAPI case API now requires **signed JWT access tokens** and isolates stored cases by their verified owner. It handles **synthetic scope answers only**, with no names, addresses, documents or real administrative data. It does not determine official eligibility.

## Security model

- `ENABLE_DEMO_CASE_API` defaults to **off**. The health endpoint stays available.
- To enable the case API, configure trusted `AUTH_ISSUER`, `AUTH_AUDIENCE`, and HTTPS `AUTH_JWKS_URL`. Missing settings fail at startup.
- Every case request must use `Authorization: Bearer <access_token>`. The server validates the RS256 signature, issuer, audience, `exp`, `iat`, and nonempty `sub` against the trusted JWKS.
- A case's `owner_subject` is derived only from the verified subject claim, never from request JSON or an arbitrary identity header.
- Only the owner can list, read, modify or delete a case; other users receive `404` even when they know its ID.
- Previous anonymous demo records have NULL owners after migration and cannot be accessed through the API; decide retention and cleanup before production.
- The owner identifier is omitted from API responses. Case IDs are not proof of ownership.

**Important:** The repository does not yet include a working identity provider, browser login, secure session management, rate limiting, CORS policy, auditing, monitoring, backup or production hosting. Keep the API private until those components are implemented and reviewed.

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

## Decisions pending

1. Choose and configure an OIDC identity provider for frontend login and API access tokens.
2. Implement frontend login, safe token transport, sign-out and session lifecycle.
3. Define data retention, audit logging without token disclosure, abuse protection and production deployment boundaries.
4. Only after authenticated frontend/backend connectivity, extend facts and provenance for reviewed administrative requirements.
