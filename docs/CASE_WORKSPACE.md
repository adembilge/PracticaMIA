# Persistent synthetic case workspace

**Milestone:** `feature/persistent-case-workspace` (PR review before production).

## Scope

Convert the independent saved case list into an authenticated case workspace without collecting real personal data. The five existing English–Italian demo scope questions are reused verbatim from `frontend/src/lib/i18n.ts`.

User flow:

1. Sign in to Auth0 and open `/cases/saved`.
2. Create an empty case. The app sends `POST /api/cases` and opens `/cases/{id}`.
3. Load the existing case through `GET /api/cases/{id}`. A missing/other-owner case is not disclosed.
4. Answer one question; `PATCH /api/cases/{id}/scope` saves a validated prefix of one to five `yes`, `no` or `unsure` answers.
5. Stop safely for `unsupported` and `needs_information`; neither state is a legal determination. Editing an earlier answer clears later answers.
6. Reload or sign back in to resume at the next unanswered, uncertain, or unsupported question.
7. Review all five saved answers when the synthetic scenario matches the demo pattern. Delete the entire synthetic case with an explicit confirmation.

The anonymous `/cases/new` and `/cases/demo` flow remains separate and client-only. This milestone does **not** persist addresses, dates, documents, or other real personal data, and does not connect the prototype checklist to official requirements.

## API contract and protection

| Frontend BFF | Backend API | Controls |
| --- | --- | --- |
| `GET /api/cases` | `GET /api/v1/cases` | Auth0 session; server-side bearer; owner filter |
| `POST /api/cases` | `POST /api/v1/cases` | Strict same-origin Origin; empty synthetic body only |
| `GET /api/cases/{id}` | `GET /api/v1/cases/{id}` | UUID path validation; owner filter |
| `PATCH /api/cases/{id}/scope` | `PATCH /api/v1/cases/{id}/scope` | Origin check; UUID; strict payload validation |
| `DELETE /api/cases/{id}` | `DELETE /api/v1/cases/{id}` | Origin check; UUID; user confirmation; owner filter |

All tokens remain on the Next.js server. The backend validates RS256/JWKS issuer/audience/expiry and derives ownership from the signed `sub`. Responses disable caching. The browser cannot choose a backend URL or owner ID.

## Acceptance

- [x] Bilingual scope questions reuse existing translations.
- [x] Server-only BFF exposes read, update and delete for an owned case.
- [x] Earlier answer changes invalidate later answers.
- [x] Invalid paths, unexpected keys and non-enumerated answers are rejected.
- [x] Database schema and Auth0 env vars remain unchanged.
- [ ] GitHub CI passes on the feature commit.
- [ ] Review Vercel preview UX and manually verify reload/resume.
- [ ] Merge after review; test the production user journey.

## Out of scope / remaining risk

Actual admin requirements are still research drafts; no production eligibility claim is permitted. Separate authenticated end-to-end tests with two real Auth0 users, live expired-session exercise, retention policy, monitoring, rate limiting, and document privacy controls remain future work.
