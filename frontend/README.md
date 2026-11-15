# PracticaMIA Frontend

The user interface for PracticaMIA is a **Next.js 15 / React 19 / TypeScript** application. It provides English and Italian navigation, authentication, saved cases, structured intake, case progress, assistant interactions, and review interfaces. Availability of individual features depends on the configured backend and environment.

## Development

Requires Node.js 22 and npm.

```bash
cd frontend
npm ci
npm run dev
```

Visit `http://localhost:3000`. The initial page can render without external credentials; protected case operations require Auth0 and an accessible FastAPI service.

Copy [`.env.example`](.env.example) to `.env.local` if you need local Auth0 and backend access, then supply the authorized development values. The frontend allows loopback HTTP for local APIs and uses HTTPS for remote APIs. Auth0 secrets and backend access tokens must stay server-side. Do not enable restricted document or administrative-review features without their corresponding backend safeguards.

## Checks

```bash
npm test
npm run typecheck
npm run build
```

The [frontend CI workflow](../.github/workflows/frontend-ci.yml) runs a built-server HTTP smoke test. The [browser acceptance suite](../docs/ACCEPTANCE_TESTING.md) uses a separate local harness.

## Architecture

- `src/app/` — routes and server-side API proxies.
- `src/components/` — reusable case, document, assistant, and layout components.
- `src/lib/` — authentication configuration, request validation, state helpers, and domain clients.
- `src/app/globals.css` and `src/app/editorial.css` — shared styles and the editorial UI.
- `src/lib/i18n.ts` — English and Italian interface copy.
- `tests/` — unit and browser acceptance infrastructure.

The Next.js server obtains authorized backend access tokens; the browser does not receive raw API bearer credentials. For backend setup and environmental safeguards, see [backend documentation](../backend/README.md) and [the project overview](../README.md).

PracticaMIA is independent of the Italian government and does not submit applications on a user's behalf.
