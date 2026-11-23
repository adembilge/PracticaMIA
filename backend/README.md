# PracticaMIA Backend

The Python backend provides authenticated conversation/task services and controlled administrative preparation for PracticaMIA. It uses **FastAPI, SQLAlchemy, PostgreSQL, Alembic, LangGraph, and source-grounded retrieval**.

## Responsibilities

- Validate Auth0-issued RS256 access tokens and enforce per-case ownership.
- Manage cases, intake facts, checklists, workflow progress, and reviewable packages.
- Register versioned official sources, verify their provenance, and require authorized human approval.
- Retrieve approved passages using full-text and vector search, with exact quote and citation checks.
- Evaluate reviewed administrative rules separately from language-model output.
- Support controlled assistant, preparation, document storage, OCR, extraction, and field-review services.

Sensitive routes are **disabled by default** and require the appropriate environment flags, trusted identity configuration, migrated database, and — for document handling — additional privacy and scanning controls. Read the implementation gates in `app/config.py` and `app/main.py` before enabling a service.

## Local setup

Requires Python 3.12. Docker is used for the optional local PostgreSQL database.

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The unprotected `GET /health` endpoint starts with private features disabled and needs no database. For a disposable local database with the full migration chain, use the same pgvector image as CI. The plain PostgreSQL service in `compose.yaml` lacks the vector extension required by revision `20261105_0007`. Run the following from `backend/` with local port 5432 free.

```bash
docker run --rm -d --name practicamia-local-db -p 127.0.0.1:5432:5432 \
  -e POSTGRES_DB=practicamia -e POSTGRES_USER=practicamia \
  -e POSTGRES_PASSWORD=local_development_only pgvector/pgvector:pg17
docker exec practicamia-local-db pg_isready -U practicamia -d practicamia
export DATABASE_URL='postgresql+psycopg://practicamia:local_development_only@127.0.0.1:5432/practicamia'
python -m alembic -c alembic.ini upgrade head
```

Wait for PostgreSQL readiness before migrating. To run authenticated task APIs, set `ENABLE_TASK_API=1` and configure the trusted OIDC settings from [`.env.example`](.env.example), then start the API in the configured shell.

Use `docker stop practicamia-local-db` when you no longer need the disposable database. Keep credentials, identity documents and private signing keys out of Git.

## Validation

```bash
cd backend
python -m pytest -q
```

The test suite covers authenticated access, case state, knowledge provenance, retrieval, document review, and preparation. The [acceptance workflow](../docs/ACCEPTANCE_TESTING.md) uses disposable PostgreSQL with pgvector. Local image OCR uses a Tesseract executable with `ita` and `eng` language data. The isolated Vercel preview bundles those languages at build time via `build_ocr.py` and runs Tesseract through the Linux `tesserocr` wheel. PostgreSQL integration and browser acceptance workflows are also defined under `.github/workflows/`.

## Project boundaries

The backend does not authenticate with SPID/CIE, submit paperwork to public offices, or issue official eligibility decisions. Approved municipal evidence and deterministic validation take precedence over model output. All consequential case information and prepared artifacts remain subject to user review.

See the [project overview](../README.md), [knowledge-review workflow](../docs/KNOWLEDGE_REVIEW_WORKFLOW.md), [case workflow](../docs/UNIFIED_CASE_WORKFLOW.md), and [document-intelligence design](../docs/PRIVATE_DOCUMENT_INTELLIGENCE.md).
