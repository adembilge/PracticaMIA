# PracticaMIA Backend

The backend is a **FastAPI** service for authenticated case management, structured intake, source-backed administrative guidance, document review, and preparation export.

It verifies RS256 access tokens, scopes saved cases to the verified user, and keeps reviewed official evidence separate from AI-generated explanations. It does **not** submit to government services or establish legal eligibility.

## Structure

- `app/cases/` — authenticated cases, intake, checklist, workflow and preparation PDF.
- `app/knowledge/` — official sources, snapshots, review events, approved passage retrieval and optional RAG.
- `app/rules/` — versioned, signed administrative rules and evaluator.
- `app/private_documents/` — separately gated encrypted file and field-review lifecycle.
- `app/preparation/` — isolated preparation and agent orchestration services.
- `migrations/` — Alembic schema history; retain all revisions.
- `tests/` — API, authorization, extraction, knowledge, rules and integration tests.

## Local setup

Requirements: Python 3.12 and PostgreSQL with pgvector.

```bash
# Run at the repository root
docker compose -f backend/compose.yaml up -d db

# Then:
cd backend
python -m venv .venv
# Activate the environment
python -m pip install -e ".[dev]"
# Configure trusted OIDC and database environment settings
python -m alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

See [`.env.example`](.env.example) for the exact environment variables. Copying it to a file does not automatically export its variables to the Python process. With account services disabled, `GET /health` remains available.

## API surface

The available routes depend on server-side release flags.

| Area | Representative endpoints |
| --- | --- |
| Cases | `/api/v1/cases`, `/api/v1/cases/{case_id}` |
| Intake and scope | `/api/v1/cases/{case_id}/scope`, `/intake` |
| Reviewed checklist | `/api/v1/cases/{case_id}/checklist` |
| Case workflow | `/api/v1/cases/{case_id}/workflow` and `/workflow/checklist` |
| Preparation PDF | `/api/v1/cases/{case_id}/package` and `/package/pdf` |
| Approved sources | `/api/v1/knowledge/sources` |
| Optional services | Source search/review, assistant, preparation and private documents |

Swagger/OpenAPI metadata is available from the running application at `/openapi.json`.

**Security boundaries:** Every case operation requires a valid bearer token and owner-scoped authorization; review privileges and private-document processing have additional server-side controls. Source versions must be approved and integrity-checked before they can support a trusted checklist.

## Tests

```bash
cd backend
python -m pytest -q
```

CI also validates PostgreSQL migrations, source integrity, authenticated access, and a synthetic browser-to-API workflow. For runbooks, see [the documentation index](../docs/README.md).
