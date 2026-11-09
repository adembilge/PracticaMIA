# PracticaMIA

**AI-assisted preparation for Italian administrative procedures.**

PracticaMIA helps people navigate administrative paperwork in Italy through structured, evidence-backed workflows. It combines a bilingual interface, case management, an AI assistant, official-source retrieval, deterministic requirements, and document review to help users understand what to prepare and what to do next.

The current domain focus is **`cambio di residenza`** (change of registered residence) in **Milano**. PracticaMIA is independent of the Italian government: it prepares and explains information but does **not** authenticate to government services, submit an application, or issue an official decision.

## What PracticaMIA does

- **Guided case intake:** collect relevant facts through focused questions, distinguish known information from unresolved details, and save progress.
- **Case workspace:** organize intake, next actions, checklists, documents, and preparation status in one place.
- **Official-source knowledge:** store versioned municipal material, track its provenance and approval, and retrieve passages using lexical and vector search.
- **AI assistance:** use bounded agent actions and retrieval-augmented answers while checking quoted evidence against approved sources.
- **Requirements and review:** apply deterministic, versioned conditions; flag missing information and contradictions rather than guessing.
- **Document intelligence:** process supported private documents, extract candidate fields, compare them against case facts, and request explicit user confirmation.
- **Application preparation:** assemble reviewable information and PDF artifacts when the supported workflow's evidence and review conditions are satisfied.

The implementation is evolving. Some services are deliberately disabled outside controlled environments until source review, privacy controls, and deployment prerequisites have been satisfied. A feature's presence in the repository does not imply that it is available for public use.

## How the system works

```text
User (English / Italian)
    |
    v
Next.js interface and authenticated case workspace
    |
    v
FastAPI — authentication, case ownership and typed services
    |
    +--> Case intake, checklist and workflow state
    +--> LangGraph assistant and constrained tool selection
    |       +--> Source-grounded retrieval and quote verification
    |       +--> Deterministic administrative rules
    +--> Private document extraction and human review
    +--> Reviewable preparation and PDF output
    |
    v
PostgreSQL — case records, source versions and retrieval indexes
```

**Evidence and control are separate from language generation.** The language model can help interpret a request and explain verified results, but it cannot approve official sources, invent binding procedural requirements, confirm extracted personal information, or mark an application as submitted.

## Technology

| Layer | Stack |
| --- | --- |
| Interface | Next.js 15, React 19, TypeScript, English/Italian localization |
| API | Python 3.12, FastAPI, Pydantic, SQLAlchemy |
| Identity | Auth0 sessions, RS256 access-token validation, owner-scoped API access |
| Agent and language models | LangGraph, LangChain, configurable model provider |
| Knowledge retrieval | PostgreSQL full-text search, pgvector, source and passage provenance |
| Administrative logic | Deterministic Python rules, source/version approval controls |
| Documents | Private storage, PDF processing, OCR, validation, PDF generation |
| Persistence | PostgreSQL, Alembic |
| Quality | pytest, Node.js tests, TypeScript checks, Playwright and GitHub Actions |

The codebase contains deployment configuration for Vercel and PostgreSQL infrastructure. Environment-specific access and privacy-sensitive services are explicitly gated.

## Repository structure

```text
backend/       FastAPI application, domain services, migrations and tests
frontend/      Next.js pages, components, API proxies and tests
requirements/  Reviewed and candidate procedure catalogs and public verification keys
research/      Administrative research and jurisdiction-specific notes
docs/          Architecture, source-review, workflow and governance documentation
evals/         Evaluation inputs and fixtures
audit/         Security and end-to-end audit utilities
scripts/       Repository validation utilities
.github/       Continuous integration workflows
AGENTS.md      Repository development and safety instructions
```

## Local development

**Prerequisites:** Node.js 22, npm, Python 3.12, and Docker for the local PostgreSQL service.

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`. Protected account and case operations require a configured Auth0 application and API connection; see `frontend/.env.example`.

Backend (from the repository root in a separate terminal):

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
docker compose up -d db
uvicorn app.main:app --reload
```

On Windows, activate the environment using `.venv\Scripts\Activate.ps1`. The public `/health` endpoint runs without enabling private APIs. To use protected case, knowledge, or document services, configure the required identity, database, feature flags and migration level as described in `backend/.env.example` and [backend documentation](backend/README.md). Do not copy credentials into the repository.

## Verification

```bash
# Frontend
cd frontend
npm test
npm run typecheck
npm run build

# Backend (in a separate shell)
cd backend
python -m pytest -q

# Roadmap consistency (from repository root)
python scripts/validate_roadmap.py
```

Some integration and browser checks additionally require an isolated PostgreSQL service and their dedicated CI configuration. Automated tests use synthetic fixtures and do not establish that real municipal cases are legally valid.

## Trust and scope

Administrative guidance must be grounded in human-reviewed, versioned official material. Missing, revoked, or conflicting evidence is a reason to stop or request review. User-uploaded information is private; extracted fields are not considered confirmed without the required validation and user action.

PracticaMIA is **not an official municipal service, legal representative, or application-submission channel**. Users remain responsible for reviewing their information and completing any submission through the appropriate government service.

For implementation details, see [system design](docs/UX_INTERFACE_SPEC.md), [case workflow](docs/UNIFIED_CASE_WORKFLOW.md), [official-source review](docs/KNOWLEDGE_REVIEW_WORKFLOW.md), [document processing](docs/PRIVATE_DOCUMENT_INTELLIGENCE.md), and the [full product specification](PracticaMIA_Complete_Project_Specification.md).