# PracticaMIA 2.0 Phase 1 baseline

Recorded on 17 November 2026 for [Phase 1, task 1](phase-01-repo-foundation.md#1-pin-the-existing-release-and-open-the-working-branch).

## Repository and CI

- `main` and the starting point of [`rebuild/phase-01-repo-foundation`](https://github.com/adembilge/PracticaMIA/tree/rebuild/phase-01-repo-foundation) were pinned at [`93f769fff89eb40f12ffd44ebeb63d01b4d8b7d3`](https://github.com/adembilge/PracticaMIA/commit/93f769fff89eb40f12ffd44ebeb63d01b4d8b7d3), the merge of roadmap PR #91. This commit contains 358 tracked files, including 51 Markdown files.
- GitHub showed zero open PRs before the rebuild branch was opened, so there was no open cleanup overlap at the snapshot.
- The published [`archive/practicamia-v1` tag](https://github.com/adembilge/PracticaMIA/tree/archive/practicamia-v1) and the [archive branch](https://github.com/adembilge/PracticaMIA/tree/archive/practicamia-v1-baseline) point to the pinned baseline commit. Verify the tag with `git ls-remote --exit-code --tags origin refs/tags/archive/practicamia-v1`.

| Check at the pinned `main` SHA | Result |
| --- | --- |
| Frontend tests, types, build, and HTTP smoke | [Success](https://github.com/adembilge/PracticaMIA/actions/runs/44063222947) |
| Backend tests and PostgreSQL migrations | [Success](https://github.com/adembilge/PracticaMIA/actions/runs/44063223013) |
| Chromium, signed test JWTs, FastAPI, and disposable PostgreSQL | [Success](https://github.com/adembilge/PracticaMIA/actions/runs/44063222890) |

## Live deployments and schema

Vercel alias lookups and deployment metadata identified the deployments below. Separate read-only `SELECT version_num FROM public.alembic_version ORDER BY version_num` queries returned `20261116_0017` on both Neon branches of the `practicamia` project. The production API health endpoint returned HTTP 200 with `status: ok`.

| Surface | Active alias | Vercel deployment ID | Deployed commit |
| --- | --- | --- | --- |
| Production web | `practicamia.vercel.app` | `dpl_J9PzL9jDPN9cx3DUXehhYApMEH9X` | [`e8d92fc`](https://github.com/adembilge/PracticaMIA/commit/e8d92fc001f373dc16ada2b0ee2ace8bfdc29794) |
| Production API | `practicamia-api.vercel.app` | `dpl_B6dZ2Q6x8113V78nJ5EcjM43abPi` | [`b3922df`](https://github.com/adembilge/PracticaMIA/commit/b3922df4f83b00fd1502495c81c107f3df14bace) |
| Protected staging web | `practicamia-git-preview-auth-review-d32a00-firatadembilge-4729.vercel.app` | `dpl_5bwPhAnyjV4z6PZ2MFH74qoYtXJR` | [`74208a0`](https://github.com/adembilge/PracticaMIA/commit/74208a0d1f62dfcb7633112f45a1d66c53f9501f) |
| Protected staging API | `practicamia-api-git-preview-auth-rev-599637-firatadembilge-4729.vercel.app` | `dpl_45ahA4PQoyXHhEa1YML2Qktf7WMw` | [`74208a0`](https://github.com/adembilge/PracticaMIA/commit/74208a0d1f62dfcb7633112f45a1d66c53f9501f) |

| Database target | Neon branch | Observed Alembic revision |
| --- | --- | --- |
| Production | `main` | `20261116_0017` |
| Protected staging | `preview-preparation-mvp-20261107` | `20261116_0017` |

Both production projects report `READY` and each has one verified project domain, shown above. Production recovery should use the recorded web and API deployment IDs as a pair and recheck compatibility with the target database revision before promotion. The Git archive preserves the repository baseline, including the old plans and source records.

## Vercel environment variable inventory

Names observed across production and preview on 17 November 2026, grouped by scope. Preview-specific entries refer to `preview/auth-review-isolated` unless a broader scope is shown.

| Project | Scope | Names |
| --- | --- | --- |
| Web | Production and protected staging | `APP_BASE_URL`, `AUTH0_AUDIENCE`, `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET`, `AUTH0_DOMAIN`, `AUTH0_SECRET` |
| Web | Production and preview | `BACKEND_API_URL` (includes a protected staging override) |
| Web | Production | `ENABLE_PUBLIC_SYNTHETIC_AI`, `ENABLE_PUBLIC_SYNTHETIC_DEMO`, `OPENROUTER_API_KEY` |
| Web | Protected staging | `ENABLE_ASSISTANT_UI`, `ENABLE_PREPARATION_UI`, `ENABLE_REVIEW_UI` |
| API | Production and protected staging | `AUTH_AUDIENCE`, `AUTH_ISSUER`, `AUTH_JWKS_URL`, `DATABASE_URL`, `ENABLE_KNOWLEDGE_CATALOG_API` (also present on the knowledge staging branch) |
| API | Production and preview | `ENABLE_DEMO_CASE_API` (includes branch-scoped preview overrides) |
| API | Protected staging | `ASSISTANT_CHAT_MODEL`, `ASSISTANT_DAILY_LIMIT`, `ASSISTANT_LLM_PROVIDER`, `ASSISTANT_USAGE_HASH_KEY`, `ENABLE_ASSISTANT_API`, `ENABLE_KNOWLEDGE_REVIEW_API`, `ENABLE_KNOWLEDGE_SEARCH_API`, `ENABLE_PREPARATION_API`, `KNOWLEDGE_REVIEWER_SUBJECTS`, `OPENROUTER_API_KEY`, `OPENROUTER_SMOKE_TOKEN`, `PREPARATION_DATABASE_FINGERPRINT`, `PREPARATION_DOCUMENT_KEY`, `PREPARATION_RULE_REVIEW_PUBLIC_KEY`, `PREPARATION_TARGET` |

`ENABLE_KNOWLEDGE_SEARCH_API` is also present on `feature/knowledge-staging-rollout`.

## Rebuild branch and test environment

Phase 1.4 verification on 17 November 2026. The GitHub branch [`rebuild/phase-01-repo-foundation`](https://github.com/adembilge/PracticaMIA/tree/rebuild/phase-01-repo-foundation) points to [`aeba1d1`](https://github.com/adembilge/PracticaMIA/commit/aeba1d126a71916e470c2d8582bcfba7a5e9fdf2). Its immediate parent is `93f769f`, the commit referenced by `archive/practicamia-v1`. The only changes on the branch since that parent are the Phase 1 baseline document and its roadmap link. The workflow and test harness files, and both `vercel.json` files, match `main` at `0ba991e`.

| Surface | Trigger and verified evidence |
| --- | --- |
| Frontend CI | PRs targeting `main`, pushes to `main` and manual dispatch. The branch's [PR run](https://github.com/adembilge/PracticaMIA/actions/runs/44066215540) passed unit tests, TypeScript, a production build and an HTTP smoke test against Next.js on localhost. |
| Backend CI | Same triggers. The branch's [PR run](https://github.com/adembilge/PracticaMIA/actions/runs/44066215335) passed API and authentication tests and upgraded a runner-local `practicamia_test` PostgreSQL service with pgvector. |
| Synthetic Chromium acceptance | Same triggers. The branch's [PR run](https://github.com/adembilge/PracticaMIA/actions/runs/44066215331) passed the local two-account FastAPI suite and logical dump/restore on the disposable `practicamia_acceptance` PostgreSQL service. |
| Authenticated hosted Preview | Manual dispatch uses the protected `preview-e2e` environment and an explicitly selected synthetic-only target. Matching PR path changes run the offline guard tests. See the [opt-in workflow](../../.github/workflows/authenticated-preview-e2e.yml). |
| Vercel Git Preview | Both projects suppress automatic Git deploys for `main` and `test/private-document-e2e`. Vercel recorded Git-triggered Preview builds from `rebuild/phase-01-repo-foundation` at `aeba1d1`. The web deployment `dpl_82zvirU59TEarHxymGNbjgw3NWPV` and API deployment `dpl_CsuagVHvKUcGUFqqTtAEiJASRSWT` both reported `READY`. |

Use the disposable GitHub Actions stack for routine rebuild tests. The browser harness requires `PRACTICAMIA_E2E_LOCAL_ONLY=1`, an HTTP loopback server and the named local acceptance database. Its two identities are temporary signed test JWTs. These checks exercised the real FastAPI routes and React components with synthetic data.

Vercel lists no branch-specific environment variables for `rebuild/phase-01-repo-foundation`. The generic Preview scope exposes a web `BACKEND_API_URL` setting and an API `ENABLE_DEMO_CASE_API` setting. The separate `preview/auth-review-isolated` branch has its own scoped web identity/backend settings and API identity/database settings. The `READY` states establish that the builds completed. Hosted authentication and the data path belong to the separately configured staging workflow.
