# PracticaMIA — Auth0 Login and Server-side Case Bridge

Auth0, the Next.js server-side case bridge and Neon persistence support the signed-in fictional saved-case journey. See [hosted acceptance](ACCEPTANCE_TESTING.md) for production and staging observations.

## Chosen architecture

- **Identity provider:** Auth0 Regular Web Application, using the official Next.js SDK (v4.33.0).
- **Frontend session:** Auth0 SDK handles authorization-code login, callback, logout, encrypted HTTP-only session cookies and token refresh. The login UI is unavailable until all required server-only variables are set.
- **API tokens:** Requested from Auth0 for the configured API audience. The FastAPI verifier checks a signed RS256 access token, issuer, audience, expiration and user identity.
- **Browser-to-backend:** Browser communicates only with its same-origin Next.js server. The Next.js route retrieves a token server-side and forwards it to the configured FastAPI origin.
- **Not exposed:** No access tokens in localStorage, sessionStorage, React props, browser JSON, or public environment variables. The SDK's optional browser access-token endpoint is disabled.
- **Proxy boundaries:** Remote backend origins use HTTPS. Local development may use loopback HTTP. Case mutations require the same origin and a validated payload. FastAPI independently checks credentials and case ownership.

## Before enabling login

1. Create an Auth0 tenant and a **Regular Web Application**. Use a separate development configuration from production.
2. Create an Auth0 custom API. Choose its identifier, for example `https://api.practicamia.example`. Enable RS256 signing for its access tokens.
3. Set the Auth0 application Allowed Callback URLs to `http://localhost:3000/auth/callback` for local development. For production add the exact approved canonical callback URL, for example `https://practicamia.vercel.app/auth/callback`.
4. Set Allowed Logout URLs to `http://localhost:3000` and the corresponding approved production URL.
5. Use separate Preview Auth0 configuration for the [isolated staging branch](VERCEL_NEON_DEPLOYMENT.md#isolated-preview). Authorize its exact callback and logout URLs.
6. Generate a new 32-byte random secret as 64 hexadecimal characters (for example via `openssl rand -hex 32`). Do not commit, paste into a public issue, or print the actual secret.
7. Store variables from `frontend/.env.example` in your **local `.env.local`** and in Vercel's encrypted server-side environment settings. Keep each environment’s credentials scoped to its own application.

## Required Next.js variables

| Variable | Meaning |
| --- | --- |
| `AUTH0_DOMAIN` | Auth0 tenant domain **without** `https://` (e.g. `tenant.eu.auth0.com`) |
| `AUTH0_CLIENT_ID` | Regular Web Application client ID |
| `AUTH0_CLIENT_SECRET` | Regular Web Application client secret |
| `AUTH0_SECRET` | Random 64-character hexadecimal secret for encrypted session cookies |
| `AUTH0_AUDIENCE` | Custom Auth0 API identifier; must exactly match FastAPI `AUTH_AUDIENCE` |
| `APP_BASE_URL` | Frontend canonical origin; set for stable production and local URLs |
| `BACKEND_API_URL` | Server-only FastAPI origin required for case operations |

## Required FastAPI variables

- `AUTH_ISSUER=https://<AUTH0_DOMAIN>/` (include the final slash).
- `AUTH_JWKS_URL=https://<AUTH0_DOMAIN>/.well-known/jwks.json`.
- `AUTH_AUDIENCE=<AUTH0_AUDIENCE>`.
- `DATABASE_URL` for persistent PostgreSQL and `ENABLE_DEMO_CASE_API=1` only after confirming JWT validation and backend network boundaries.

**A signed-in browser session alone does not prove that the backend is operational.** The account page reports configuration state; verify authenticated case CRUD and database persistence separately.

## User-visible pages

| Path | Behavior |
| --- | --- |
| `/account` | Offers sign-in, registration and the public demo when signed out, or account controls when signed in. The shared header shows the account display name when available. |
| `/cases/saved` | Lists synthetic cases, creates a case, and opens a saved case workspace |
| `/cases/{id}` | Owner-scoped scope, typed intake, checklist acknowledgement, package export and official handoff for supported fictional cases |
| `/api/cases` | Same-origin BFF GET and CSRF-protected POST. Returns 503 if unconfigured and 401 if signed out; never exposes access tokens |
| `/api/cases/{id}` | GET an owner-scoped case or DELETE it with Origin protection |
| `/api/cases/{id}/scope` | Origin-protected PATCH for a validated prefix of synthetic scope answers |
| `/cases/new` and `/cases/demo` | Public example flow |

Auth0 routes `/auth/login`, `/auth/logout`, and `/auth/callback` are mounted by SDK middleware only when configured. Browser navigation to login/logout uses normal anchors, not client-side prefetch.

The app's account entry uses PracticaMIA's design and passes the selected `en` or `it` locale to Auth0. Registration also passes `screen_hint=signup`. Auth0 Universal Login renders the credential form and applies its tenant's branding and enabled languages.

## Verification

- `cd frontend && npm ci && npm test && npm run typecheck && npm run build`.
- Tests cover missing/partial server configuration, backend URL allowlisting, and POST Origin validation.
- GitHub Actions and Vercel check the unconfigured build, ensuring the anonymous demo remains available.
- **Verified in production (November 2026):** Auth0 login and custom API token issuance; Next.js server proxy, FastAPI case creation/listing, Neon persistence for synthetic records.
- **Live boundaries exercised:** manual two-account checks covered case and draft download read isolation in production and selected scope/PDF operations in staging. Refresh-token lifecycle, full delete/resume coverage, and live reviewer authorization need separate evidence.

## Security and deployment limitations

- Use fictional data for the hosted case flow. The structured intake permits categorical facts and an optional move date. Real documents have separate [vault release controls](PRIVATE_DOCUMENT_VAULT_RELEASE.md).
- The backend is publicly reachable but all case routes require verified bearer tokens; keep strict JWT validation, ownership checks, rate limiting and network boundaries.
- Add API rate limiting, monitoring and non-sensitive audit events, retention/deletion rules, secure networking, and end-to-end tests before handling real records.
- Once FastAPI is deployed, do not assume browser CORS is the only authorization layer: verify JWTs and per-user owner checks on every backend request.

## Sources

- Auth0 Next.js SDK 4 documentation: https://auth0.github.io/nextjs-auth0/
- Auth0 SDK repository: https://github.com/auth0/nextjs-auth0
