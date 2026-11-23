# PracticaMIA

**One conversational assistant for Italian administrative procedures.**

PracticaMIA is an independent English–Italian assistant. The customer experience is one conversation at `/`: users write a question, receive focused clarifications, review cited information and confirm supported actions in the same transcript. Conversation history is the only customer-facing navigation.

## Current status

- The root route renders the single-chat interface; legacy customer case, account and demo pages have been removed.
- The public product surface is single-chat only. Backend case-named storage and API compatibility are still under migration and are not considered cleaned up.
- The conversation API and worker remain restricted to isolated development/Preview infrastructure. **Production chat execution is not enabled.**
- Phase 4 agent and conversation-engine work remains active. Phase 5 is paused.
- The initial reviewed scope is an individual residence-change scenario in Milano. Broader or unsupported requests must be handled with explicit scope boundaries.
- Real personal-document upload, OCR processing and government submission are not enabled.

A merged UI change or successful build does not establish a production-ready assistant. See [active work](docs/ACTIVE_WORK.md), [product specification](docs/PRODUCT_SPECIFICATION.md), and [acceptance status](docs/ACCEPTANCE_TESTING.md).

## Product rules

- One chat shell at `/`; no separate customer workspaces, task dashboards, document portals or procedure wizards.
- Internal workflow state is private implementation detail and is never a customer-facing selector.
- Only current, provenance-preserving, human-reviewed official material may support trusted administrative statements.
- Missing, stale or conflicting evidence must produce uncertainty or a request for review.
- Extracted or inferred information is a proposal until the user explicitly confirms it.
- PracticaMIA does not sign in to government portals, use SPID/CIE credentials, pay fees or submit applications.
- Users complete any required official action themselves through the verified government service.

## Architecture

```text
One chat shell and conversation history
             |
             v
Next.js server-side authenticated API proxy
             |
             v
FastAPI conversation transport
             |
             v
LangGraph specialist agent
  - intent and scope
  - clarification and resumption
  - approved-source retrieval and citations
  - deterministic rules and permissions
  - user-confirmed proposals
             |
             v
PostgreSQL
  - owner-scoped conversations and events
  - private internal task state
  - approved source versions and passages
  - audit and approval records
```

Internal storage identifiers and some backend routes still retain historical case terminology. They are technical debt under the migration plan in [LEGACY_MIGRATION_PLAN.md](docs/LEGACY_MIGRATION_PLAN.md), not customer-facing workflows. Existing records must not be deleted or reassigned as part of source-code cleanup.

## Repository

- `backend/` — FastAPI, agent runtime, knowledge retrieval, rules, migrations and tests.
- `frontend/` — Next.js single-chat application, authenticated API proxy and UI tests.
- `docs/` — current product, security, operations and active Phase 4 documentation.
- `docs/phase-4/` — active Phase 4 engineering contracts and pilot references.
- `docs/research/phase-02-03/` — source material referenced by synthetic evaluation provenance.
- `evals/` — offline synthetic evaluation inputs and scoring utilities.
- `requirements/` — reviewed and candidate Milan procedure material.
- `.github/workflows/` — CI and isolated integration checks.

## Local development

Requirements: Node.js 22, Python 3.12 and PostgreSQL for database-backed checks.

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

Backend:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
uvicorn app.main:app --reload
```

On Windows, activate the environment with `.venv\\Scripts\\Activate.ps1`. Configure local credentials and database values in ignored environment files. Never commit secrets or copy production credentials into development.

## Verification

```bash
cd frontend
npm test
npm run typecheck
npm run build

cd ../backend
python -m pytest -q
```

PostgreSQL-backed and browser integration checks run in their dedicated GitHub Actions workflows. Synthetic results are engineering evidence only; they do not establish legal correctness, participant validation or production acceptance.

## Trust and safety

Administrative guidance must be grounded in reviewed, current official evidence. Do not invent eligibility conditions, required documents, fees, deadlines or submission status. Keep source approval, user confirmation, internal authorization and government confirmation as separate states.

PracticaMIA is not a government authority or legal representative.
