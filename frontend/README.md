# PracticaMIA Frontend

The frontend is **Next.js 15 / React 19 / TypeScript**. Its **binding target is one ChatGPT-like customer chat at `/`**, one composer, conversation-only sidebar and inline document, source, checklist, approval, form and status cards. There is **no user-facing case/workspace/dashboard concept** in the target. **Current implementation remains legacy**: the landing page, `/cases/*` workflows, and the isolated agent-chat acceptance fixture have not been migrated to a full hosted single-chat product. Do not treat the existing pages as the target design. See [single-chat contract](../docs/SINGLE_CHAT_PRODUCT_CONTRACT.md) and D-010.

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

- `src/app/` — currently includes legacy standalone screens and server-side proxies; target primary customer route is `/` only. Internal auth/reviewer and legal routes are distinct supporting surfaces.
- `src/components/` — reusable case, document, assistant, and layout components.
- `src/lib/` — authentication configuration, request validation, state helpers, and domain clients.
- `src/app/globals.css` and `src/app/editorial.css` — shared styles and the editorial UI.
- `src/lib/i18n.ts` — English and Italian interface copy.
- `tests/` — unit and browser acceptance infrastructure.

The Next.js server obtains authorized backend access tokens; the browser does not receive raw API bearer credentials. For backend setup and environmental safeguards, see [backend documentation](../backend/README.md) and [the project overview](../README.md).

PracticaMIA is independent of the Italian government and does not submit applications on a user's behalf.
