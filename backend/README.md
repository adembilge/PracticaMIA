# PracticaMIA Backend

The Python backend provides the authenticated case-management and administrative-preparation services for PracticaMIA. It uses **FastAPI, SQLAlchemy, PostgreSQL, Alembic, LangGraph, and source-grounded retrieval**.

## Responsibilities

- Validate Auth0-issued RS256 access tokens and enforce per-case ownership.
- Manage cases, intake facts, checklists, workflow progress, and reviewable packages.
- Register versioned official sources, verify their provenance, and require authorized human approval.
- Retrieve approved passages using full-text and vector search, with exact quote and citation checks.
- Evaluate reviewed administrative rules separately from language-model output.
- Support controlled assistant, preparation, document storage, OCR, extraction, and field-review services.

Sensitive routes are **disabled by default** and require the appropriate environment flags, trusted identity configuration, migrated database, and — for document handling — additional privacy and scanning controls. Read the implementation gates in `app/config.py` and `app/main.py` before enabling a service.

## Local setup

Requires Python 3.12 and Docker Compose.

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
docker compose up -d db
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The unprotected `GET /health` endpoint is available with private features disabled. For authenticated APIs, populate the settings documented in `.env.example` with real trusted OIDC values and an isolated database. Apply migrations to the **intended non-production database only** after reviewing them:

```bash
alembic -c alembic.ini upgrade head
```

Setting values in an example file alone does not load them into the process; export them or use a supported environment loader. Never put actual credentials, user identity documents, or private signing keys into Git.

## Validation

```bash
cd backend
python -m pytest -q
```

The test suite covers authenticated access, case state, knowledge provenance, retrieval, document review, and preparation behavior using isolated or synthetic inputs. PostgreSQL integration and browser acceptance workflows are also defined under `.github/workflows/`.

## Project boundaries

The backend does not authenticate with SPID/CIE, submit paperwork to public offices, or issue official eligibility decisions. Approved municipal evidence and deterministic validation take precedence over model output. All consequential case information and prepared artifacts remain subject to user review.

See the [project overview](../README.md), [knowledge-review workflow](../docs/KNOWLEDGE_REVIEW_WORKFLOW.md), [case workflow](../docs/UNIFIED_CASE_WORKFLOW.md), and [document-intelligence design](../docs/PRIVATE_DOCUMENT_INTELLIGENCE.md).