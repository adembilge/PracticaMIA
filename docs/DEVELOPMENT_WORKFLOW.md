# PracticaMIA — Development and Preview Workflow

**Status:** Initial development workflow, 4 November 2026.  
**Applies to:** `adembilge/PracticaMIA`; frontend lives in `frontend/`.

## Branches and environments

- `main` is the production branch. A push to `main` triggers a production deployment.
- Work on a short-lived feature branch, such as `feature/case-persistence` or `chore/frontend-quality-gates`.
- Vercel builds preview deployments for eligible non-production Git pushes and pull requests. Review the URL shown on the PR; do **not** assume that the production URL has changed.
- The application is currently a **synthetic-data demonstration**. Do not enter real personal documents or addresses.

## Before merging

1. Describe the change and expected behavior in the pull request.
2. Confirm GitHub Actions **Frontend CI** completed: `npm ci`, `npm test`, `npm run typecheck`, `npm run build`.
3. Open the Vercel preview and check navigation, desktop/mobile layout, language toggle, and relevant user flows.
4. Check that the application still distinguishes *demo-scope matching* from real administrative eligibility and does not claim a case has been submitted.
5. Merge to `main` only after reviewing the preview; check the production deployment afterward.

## Local commands

```bash
cd frontend
npm ci
npm test
npm run typecheck
npm run build
npm run dev
```

****Reproducible installs:** `frontend/package-lock.json` is committed; use `npm ci` locally and in CI. Update dependencies with `npm install` and commit both `package.json` and `package-lock.json` in the same PR.

## Protection and approvals

A successful GitHub Actions check and a successful Vercel build are **not** the same as a required merge gate. Configure repository branch protection or a ruleset separately to require the checks and PR review. Until then, repository write permissions can still allow direct updates to `main`.

## Next product milestones

After the frontend workflow is verified, validate the live prototype UX and official-source assumptions, then implement a FastAPI backend and persistent case management. Do not turn draft administrative research into executable requirements before review.
