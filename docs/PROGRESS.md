# PracticaMIA — implementation and release evidence

**Recorded:** 9 November 2026. This is a dated engineering snapshot, not certification of the project specification's full task roadmap.

## Verified engineering evidence

| Item | Evidence | Important limitation |
| --- | --- | --- |
| Saved case, intake and workflow | PRs [#64](https://github.com/adembilge/PracticaMIA/pull/64) and [#67](https://github.com/adembilge/PracticaMIA/pull/67) | User-read marks do not establish that official administrative steps are complete |
| Private document review | [PR #65](https://github.com/adembilge/PracticaMIA/pull/65) | Production personal-document upload remains disabled behind release controls |
| Downloadable preparation summary | [PR #66](https://github.com/adembilge/PracticaMIA/pull/66) | PDF is a non-official, reviewable draft, never a government receipt |
| Isolated browser acceptance | [PR #68](https://github.com/adembilge/PracticaMIA/pull/68), eight supported synthetic browser scenarios passing | Not a live Auth0 sign-in or real document acceptance |
| Neon database | Production revision `20261109_0016`; two preexisting cases and two reviewed source records checked | A schema revision does not imply live frontend parity |
| Production backend | Commit `4ab8fa2` was deployed and `/health` and OpenAPI routes returned HTTP 200 | Authenticated case and PDF requests were not verified end-to-end on the hosted website |
| Production frontend | Last verified production deployment on `5a3b78f` | Newer frontend deployment failed due to Vercel daily quota (HTTP 402) |

## Outstanding release gates

- Verify the latest frontend deployment, its same-commit backend, and a complete hosted login-to-PDF flow with genuine Auth0 browser sessions.
- Complete independent evaluations of the conversational assistant, citations, source currency and document extraction on representative cases.
- Keep real-document uploads disabled until privacy, security, malware scanning, retention, backup and operational obligations have been reviewed and demonstrated.
- Reconcile the canonical task registry against individual acceptance evidence; old governance states are not automatically updated by merged code.
- Complete operational monitoring, rollback and owner release sign-off before opening access to personal residence records.

## Evidence discipline

A passing synthetic fixture does not constitute a source approval; a signed rule cannot replace current official instructions; a completed review checkbox does not constitute a legal action; and a deployed backend is not proof that the frontend is updated.

For current implementation details see [the documentation index](README.md).
