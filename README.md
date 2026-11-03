# PracticaMIA

PracticaMIA is a planned English–Italian administrative guidance application, initially focused on preparation for selected Milan residence-change scenarios.

## Current project state

- **Implemented:** Frontend-only Next.js demonstration, guided intake, illustrative checklist, bilingual UI and flow tests, based on synthetic data.
- **Documented:** Initial procedure research, first user journey, UX interface specification.
- **Not implemented:** Backend, authentication, persistence, LangGraph agent, RAG, OCR, real application preparation, government submission.
- **Administrative requirements:** Research is a draft and **must be reviewed** before being used as production rules.

## Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. A standalone `frontend/preview.html` is also provided.

## Documentation

- [Initial procedure research](research/milan_residence_change.md)
- [First user journey](docs/FIRST_USER_JOURNEY.md)
- [UX specification](docs/UX_INTERFACE_SPEC.md)
- [Complete original specification](PracticaMIA_Complete_Project_Specification.md)

The complete original specification is reference material; its original 94-task roadmap is **not** the current development plan. Work proceeds incrementally by validated milestones.

This repository was refreshed from the PracticaMIA Google Drive project with a history-preserving commit. Previous iterations remain visible in Git history.

PracticaMIA is not affiliated with the Italian government and does not submit applications on the user's behalf.
