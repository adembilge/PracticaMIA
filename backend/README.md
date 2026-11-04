# PracticaMIA — Backend Foundation

**Status:** Milestone 3 development only. Not deployed and not connected to the public frontend.

This FastAPI service persists only **synthetic** Milan residence-change demo scope answers using SQLAlchemy. It does **not** determine legal eligibility, collect addresses, review documents, issue official instructions, or submit government forms.

## Safety and access

- Case API endpoints are **disabled by default**; `/health` remains available.
- Demo case endpoints have **no authentication or authorization**. They are only for local development and controlled CI tests. **Never expose them on a public server.**
- API schemas accept only five yes/no/unsure scope answers and a fixed procedure type. No names, addresses, documents, or other personal information are accepted.
- The frontend is still an in-memory synthetic demonstration. This backend is not wired into Vercel production.

## Run with PostgreSQL locally

Requires Python 3.12, pip, and Docker Compose.

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
docker compose up -d db
export DATABASE_URL='postgresql+psycopg://practicamia:local_development_only@127.0.0.1:5432/practicamia'
export ENABLE_DEMO_CASE_API=1
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Windows PowerShell: activate `.venv\Scripts\Activate.ps1` and set environment variables with `$env:DATABASE_URL='...'` and `$env:ENABLE_DEMO_CASE_API='1'`.

API documentation (local only): http://127.0.0.1:8000/docs

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Basic service health; always available |
| POST | `/api/v1/cases` | Create a draft synthetic demo case (`{}` body) |
| GET | `/api/v1/cases/{id}` | Retrieve one synthetic demo case |
| PATCH | `/api/v1/cases/{id}/scope` | Replace recorded yes/no/unsure answers and recompute demo scope status |
| DELETE | `/api/v1/cases/{id}` | Delete the synthetic demo case |

No listing endpoint, authentication, address collection, uploads, or submission integration are provided.

## Test

```bash
cd backend
python -m pip install -e '.[dev]'
python -m pytest -q
```

Tests use an isolated SQLite database. GitHub Actions additionally starts PostgreSQL 17, applies the initial Alembic migration, and exercises the persisted API against PostgreSQL.

## Domain boundary

Scope values mirror the frontend demonstration (expected answers: `yes, yes, yes, no, yes`). Results are limited to `draft`, `incomplete`, `needs_information`, `unsupported`, and `provisionally_in_scope`. **None is a government eligibility decision.**

## Next steps

1. Review the PostgreSQL migration and backend CI results.
2. Design authentication, case ownership, and retention controls before storing user-provided personal details or deploying the case API publicly.
3. After authentication, persist intake facts with provenance and confirmation; then integrate the frontend.
4. Verify Milan municipal requirements before implementing document or administrative eligibility rules.
