# Development and release workflow

## Branches and review

Use a short-lived branch for a scoped change and open a pull request to `main`. Keep production and review-only feature flags separate. Do not infer that a GitHub merge automatically updates a live deployment.

## GitHub branch protection

The owner can configure an Active ruleset for the default branch in [repository settings](https://github.com/adembilge/PracticaMIA/settings/rules). Require a pull request, block force pushes and branch deletion, and use unique check names from actual runs. A solo maintainer can set zero required approvals if that matches their review practice. Match path-filtered workflows to the changes that trigger them so an absent check cannot block unrelated PRs. Vercel Preview checks tell you about deployment builds. Review GitHub Actions results and release evidence independently.

## Required checks

- **Backend:** `python -m pytest -q` and PostgreSQL migration smoke checks.
- **Frontend:** `npm test`, `npm run typecheck`, `npm run build`, and built-server HTTP smoke.
- **Browser acceptance:** the dedicated GitHub Actions Chromium job uses the real case UI and FastAPI with a disposable database and test identities.
- **Governance changes:** `python scripts/validate_roadmap.py` plus its negative-control tests.

Review changes to source approvals, rules signatures, authentication, encryption, and data retention independently. A passing unit test is not a replacement for a real reviewer decision or an authenticated hosted-environment check.

## Deployment

1. Verify the intended repository commit, team, frontend and backend projects, and target environment.
2. Verify the target database schema; apply additive migrations through a reviewed release process.
3. Build the backend and frontend from the same reviewed commit.
4. Check runtime health, API route presence, Auth0 callback/session, case isolation, current sources, package export, and blocked/unsupported cases.
5. Confirm release flags. Real personal-document ingestion requires an independently reviewed controller notice, malware scanner, encryption key lifecycle, retention and backup policies, and two-account testing.
6. Record the release commit, deployment IDs, tests, open issues and rollback plan.

Do not enable real personal data or official submission behavior through environment flags or a text-only approval. See [the private-document release guide](PRIVATE_DOCUMENT_VAULT_RELEASE.md) for additional controls.
