# PracticaMIA

**PracticaMIA** is an independent, bilingual (English and Italian) web application that helps people understand and organize Italian administrative procedures. Its first supported workflow focuses on an individual change of registered residence (*cambio di residenza*) in the Comune di Milano.

Instead of offering a generic answer, PracticaMIA guides a person through structured questions, checks the supported procedure against reviewed official-source evidence, and assembles a preparation summary that the person can review before continuing on the official website.

PracticaMIA is **not affiliated with a municipality or the Italian government**. It does not determine legal eligibility, authenticate official documents, or submit applications on a user's behalf.

## How it works

1. **Create a case.** Sign in and start a saved residence-change case.
2. **Describe the situation.** Answer scope questions and explicitly confirm structured case information.
3. **Review guidance.** See the next action, source-backed checklist, and citations to approved official references. Optional AI explanations are separate from the rules that determine the checklist.
4. **Check information.** Where the private-document service has been separately enabled, examine extracted housing and move-date suggestions, correct them, and inspect inconsistencies with the case.
5. **Prepare a document.** Download a PDF summary containing confirmed facts, reviewed actions, citations, outstanding issues, and links to the relevant official services.
6. **Continue on the official service.** The user independently verifies the current instructions and completes any required government submission.

The reviewed first-route rules cover a narrowly defined individual Milan scenario. Unconfirmed, unsupported, or insufficiently sourced situations must not be presented as approved or complete. A downloaded preparation summary is **not** an official application or receipt.

## Key capabilities

- **Account-bound case management:** Auth0 sign-in, saved cases, case ownership, resumable intake, and user-controlled checklist review progress.
- **Official-source knowledge:** controlled acquisition, immutable snapshots, content digests, versioned passages, human review, explicit approval and revocation, and traceable citations.
- **Verified rules:** an independently reviewed and signed administrative ruleset, evaluated against confirmed facts and current source approval; missing or revoked evidence blocks the associated guidance.
- **AI-assisted explanations:** optional case-contextual explanations and an isolated RAG question-answering service. Generated text cannot approve sources, create mandatory requirements, or override the rules engine.
- **Document intelligence:** bounded PDF/image extraction, user-confirmed corrections, and comparison against saved case facts. Private uploads are disabled until their separate privacy, malware-scanning, encryption, and retention controls are ready.
- **Preparation export:** on-demand, non-official PDF drafts that distinguish user-provided facts, approved references, and unresolved issues.
- **Multilingual interface:** English and Italian navigation, with the reviewed administrative source text preserved and cited.

## Architecture

```text
Browser
  │
  ▼
Next.js / React / TypeScript
  ├── Auth0 server-managed session
  ├── Case workspace and source-linked checklist
  └── Same-origin API routes (server-side access tokens)
                │
                ▼
          FastAPI / Python
          ├── JWT verification and case ownership
          ├── Structured intake and workflow state
          ├── Signed rules and citation validation
          ├── Official-source registry and retrieval
          ├── Document review (separately gated)
          └── Preparation PDF generation
                │
                ▼
       PostgreSQL / Neon / pgvector
       ├── Cases and user confirmations
       ├── Source versions, reviews and passages
       └── Encrypted document metadata when enabled
```

The main components are kept separate so AI-generated explanations cannot become administrative decisions. All personal-case API operations require a validated identity, and access is scoped to the case owner.

## Technology

| Layer | Technologies |
| --- | --- |
| Web | Next.js 15, React 19, TypeScript |
| API | Python 3.12, FastAPI, Pydantic |
| Authentication | Auth0, RS256 JWT verification |
| Data | PostgreSQL, SQLAlchemy, Alembic, pgvector |
| Knowledge and AI | Versioned official-source retrieval, LangChain, LangGraph, optional model providers |
| Document processing | PDF parsing, local OCR where available, AES-GCM encrypted review storage |
| Deployment | Vercel frontend and API, Neon PostgreSQL |
| Quality | pytest, Node.js tests, TypeScript, GitHub Actions, Chromium browser acceptance tests |

## Repository layout

```text
frontend/       Next.js application, UI components and frontend tests
backend/        FastAPI services, database models, migrations and tests
requirements/   Reviewed residence-change rule artifacts and public verification key
research/       Source-specific procedure research
evals/          Evaluation fixtures
audit/          Independent security and authenticated-flow checks
docs/           Architecture, source review, operational guides and design decisions
scripts/        Repository governance checks
.github/        CI and acceptance workflows
```

## Development

### Requirements

- Node.js 22 and npm
- Python 3.12
- Docker or a local PostgreSQL database with pgvector
- An OIDC/Auth0 configuration for authenticated case operations

### Start the API

From the repository root:

```bash
docker compose -f backend/compose.yaml up -d db
cd backend
python -m venv .venv
# Activate your virtual environment
python -m pip install -e ".[dev]"
# Export the local settings described in .env.example
python -m alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The health endpoint runs without authenticated case services configured. To use saved cases locally, supply a trusted JWT issuer, audience, JWKS URL, and database connection, and explicitly enable the applicable services. See [backend/.env.example](backend/.env.example) for the environment contract; variables must be present in the process environment.

### Start the web application

In another terminal:

```bash
cd frontend
npm ci
# Configure local server settings from .env.example
npm run dev
```

Visit `http://localhost:3000`. Saved cases require a configured Auth0 application and a reachable API. Secrets belong in local environment configuration, never in Git.

### Run checks

```bash
# Backend
cd backend
python -m pytest -q

# Frontend
cd ../frontend
npm test
npm run typecheck
npm run build
```

GitHub Actions also exercises migrations against disposable PostgreSQL and an isolated Chromium-to-FastAPI acceptance workflow with temporary signed test identities. That automated workflow does not replace live Auth0, document-security, or hosted-environment verification.

## Documentation

The [documentation index](docs/README.md) organizes the product architecture, source-review process, case workflow, security controls, and testing instructions. The [complete project specification](PracticaMIA_Complete_Project_Specification.md) captures the broader product design and planned capabilities.

## Official resources

- [ANPR — Anagrafe Nazionale della Popolazione Residente](https://www.anagrafenazionale.interno.it/)
- [Comune di Milano — Cambio di residenza](https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza)

Always consult the current official service for authoritative requirements, required attachments, deadlines, and submission instructions.

---

PracticaMIA is an independent assistance project, not a public authority or authorized government intermediary.
