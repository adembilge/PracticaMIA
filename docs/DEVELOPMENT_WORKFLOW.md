# Development workflow

1. Read [product specification](PRODUCT_SPECIFICATION.md), [active work](ACTIVE_WORK.md), [single-chat contract](SINGLE_CHAT_PRODUCT_CONTRACT.md) and relevant security documentation.
2. Inspect the current repository head, open PRs, exact commit SHAs and required CI checks.
3. Work on an isolated branch. Keep each PR bounded and reviewable.
4. Preserve the one-chat customer surface. Do not reintroduce standalone task, demo, document or account workflows.
5. Keep synthetic evaluation separate from participant, legal, source-review and production evidence.
6. Update [active work](ACTIVE_WORK.md) and [progress](PROGRESS.md) when task state or release limitations change.
7. Verify frontend tests, TypeScript, build and relevant backend/isolated PostgreSQL tests.
8. Report exact check outcomes and any blocked external validation. Do not describe a merge or preview as production release.

## Vercel quota discipline

Avoid unnecessary deployments and repeated commits that only trigger another preview build. Prefer one consolidated PR for a bounded change. Do not modify project settings, billing, quotas, permissions or production aliases without separate authorization.
