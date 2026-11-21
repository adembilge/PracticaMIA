# PracticaMIA

**One conversational AI assistant for Italian administrative questions and preparation.**

**Target product:** A single ChatGPT-style interface. The user sends a natural-language question, and the AI agent handles procedure discovery, clarifying questions, verified evidence, documents, forms, checklists, approvals, progress and return visits **entirely inside the same conversation**. Chat history is the only customer-facing work selector. There is **no case creation, case list, case workspace, separate document center, dashboard or page-based wizard** in the intended UX. Protected source review remains operator-only; external government portals are clearly labelled user-controlled handoffs.

**Important implementation status (21 Nov 2026):** The repository still includes an **older deployed multi-screen MVP** with `/cases/*` routes and legacy `case_id` services. The complete single-chat application is **not yet deployed**. Its isolated agent conversation components and signed API acceptance fixtures are development assets, not proof of hosted readiness. The [binding single-chat contract](docs/SINGLE_CHAT_PRODUCT_CONTRACT.md) and [D-010](docs/DECISIONS.md#d-010--no-user-facing-cases-one-chatgpt-style-conversation-workspace-21-november-2026) govern migration; Phase 5 implementation remains on hold while Phase 4 continues.

Initial reviewed scope remains a narrow individual residence-change scenario in **Milano**; broader requests must receive accurate coverage boundaries. PracticaMIA is independent of the Italian government and does not log in, sign, pay or submit to official services on the user's behalf.

## What the single-chat experience must do

- **Ask anything first:** user can send a message without choosing a procedure, authority, or case.
- **Clarify and route:** one LangGraph specialist identifies the relevant administrative goal and asks only necessary questions in chat.
- **Show official evidence:** expanded approved-source cards appear beside the supported claim and make uncertainty explicit.
- **Handle documents in messages:** authorized uploads, processing, OCR candidates and explicit field confirmation are inline, subject to release gates.
- **Plan and prepare:** requirements, checklists, progress, proposed changes, PDF drafts, reminders and official handoff are conversation actions, not distinct screens.
- **Resume safely:** prior conversations and verified action receipts are available from chat history; internal task records remain private implementation details.

**Current code caveat:** The old Milan case pages, downloadable draft and synthetic browser checks remain implemented for backward compatibility and security testing until replacement. A working legacy feature is not evidence that its in-chat successor exists.

## How the target single-chat system works

```text
User question (English / Italian)
          |
          v
ONE Next.js conversation shell + chat history + composer
          | authenticated server-side API proxy
          v
FastAPI conversation transport and encrypted events
          |
          v
One LangGraph specialist agent
  +-- Intent / municipality / authority clarification
  +-- Official-source RAG and citation checks
  +-- Deterministic requirements, next steps and official handoff
  +-- Owner-scoped internal task facts and approvals
  +-- Private document/OCR and artifact tools (release gated)
          |
          v
PostgreSQL: conversations, internal task state, approvals,
            source versions, private metadata and retrieval indexes
          |
          v
Typed in-chat replies, questions, documents, citations,
checklists, approvals, receipts, downloads and history
```

**Internal state is not a user-facing case.** The earlier backend still has owner-scoped `cases` tables and routes; those need a verified conversation-task migration. The target architecture above is **not fully hosted or released**. Evidence, identity and approval controls remain server-side; language generation cannot approve sources, silently confirm fields or claim a government submission.


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
docs/          Architecture, source-review, research, workflow and governance documentation
evals/         Evaluation inputs and fixtures
audit/         Security and end-to-end audit utilities
scripts/       Repository validation utilities
.github/       Continuous integration workflows
AGENTS.md      Repository development and safety instructions
```

## Local development

**Prerequisites:** Node.js 22, npm, Python 3.12, and Docker if running a local database.

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
uvicorn app.main:app --reload
```

On Windows, activate the environment using `.venv\Scripts\Activate.ps1`. The public `GET /health` endpoint runs without private APIs. For a PostgreSQL-backed local run, set the connection and apply migrations as shown in the backend setup. To use protected case, knowledge, or document services, configure the required identity, database, feature flags and migration level as described in [backend setup](backend/README.md#local-setup) and [backend environment settings](backend/.env.example). Do not copy credentials into the repository.

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

Administrative guidance must be grounded in human-reviewed, versioned official material. Missing, revoked, or conflicting evidence is a reason to stop or request review. Document extraction proposes fields that require explicit user confirmation. The current release does not accept real personal documents.

PracticaMIA is **not an official municipal service, legal representative, or application-submission channel**. Users remain responsible for reviewing their information and completing any submission through the appropriate government service.

For implementation details, see [documentation index](docs/README.md), [legacy case workflow implementation](docs/UNIFIED_CASE_WORKFLOW.md), [official-source review](docs/KNOWLEDGE_REVIEW_WORKFLOW.md), [document processing](docs/PRIVATE_DOCUMENT_INTELLIGENCE.md), and the [full product specification](PracticaMIA_Complete_Project_Specification.md).
