# PracticaMIA

PracticaMIA is a planned English–Italian administrative guidance application, initially focused on preparation for selected Milan residence-change scenarios.

## Current project state

- **Implemented:** Frontend-only Next.js demonstration, guided intake, illustrative checklist, bilingual UI and flow tests, based on synthetic data.
- **Documented:** Initial procedure research, first user journey, UX interface specification.
- **In development (not deployed):** FastAPI backend and SQLAlchemy persistence for synthetic scope answers only, with PostgreSQL migration and API tests.
- **In development:** Signed-token authentication and per-user ownership of synthetic cases (no login provider configured).
- **Not implemented:** Real user login, production auth integration, personal-data storage, frontend-backend integration, LangGraph agent, RAG, OCR, real application preparation, government submission.
- **Administrative requirements:** Research is a draft and **must be reviewed** before being used as production rules.

## Start the frontend

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000. A standalone `frontend/preview.html` is also provided.

## Development and preview deployments

Source code is maintained in GitHub. Work on a feature branch, open a pull request, wait for the **Frontend CI** result and the Vercel Preview Deployment, then review before merging into `main`.

- [Development workflow](docs/DEVELOPMENT_WORKFLOW.md)
- [Vercel production site](https://practicamia.vercel.app)
- The active `Protect main` ruleset requires pull requests and the `Tests, types, and build` check. Consider additionally requiring `Backend tests and PostgreSQL migration` after this milestone is merged.
- Frontend dependencies are pinned through `frontend/package-lock.json`; CI uses `npm ci`.

## Backend foundation (in development)

The FastAPI and SQLAlchemy case persistence foundation is in `main`; authenticated case ownership is under development on a feature branch. It uses PostgreSQL migrations and synthetic scope answers only. The API is disabled by default and is **not deployed** or connected to the Vercel frontend. See [backend/README.md](backend/README.md) for local setup and safety limits.

## Documentation

- [Initial procedure research](research/milan_residence_change.md)
- [First user journey](docs/FIRST_USER_JOURNEY.md)
- [UX specification](docs/UX_INTERFACE_SPEC.md)
- [Complete original specification](PracticaMIA_Complete_Project_Specification.md)

The complete original specification is reference material; its original 94-task roadmap is **not** the current development plan. Work proceeds incrementally by validated milestones.

This repository was refreshed from the PracticaMIA Google Drive project with a history-preserving commit. Previous iterations remain visible in Git history.

PracticaMIA is not affiliated with the Italian government and does not submit applications on the user's behalf.

## Authentication integration (in development)

An optional Auth0-backed account and saved-cases interface is being developed on a feature branch. The public demo remains anonymous and independent; **no real login provider or public case backend is configured yet**. See [authentication integration](docs/AUTHENTICATION_INTEGRATION.md) and [backend security](backend/README.md).
