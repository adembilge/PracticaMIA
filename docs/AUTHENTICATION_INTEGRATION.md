# PracticaMIA — Auth0 Login and Server-side Case Bridge

**Status:** Implemented as an optional integration scaffold; no Auth0 account, credentials or public backend is connected. The anonymous demonstration remains unchanged.

## Chosen architecture

- **Identity provider:** Auth0 Regular Web Application, using the official Next.js SDK (v4.33.0).
- **Frontend session:** Auth0 SDK handles authorization-code login, callback, logout, encrypted HTTP-only session cookies and token refresh. The login UI is unavailable until all required server-only variables are set.
- **API tokens:** Requested from Auth0 for the configured API audience. The FastAPI verifier checks a signed RS256 access token, issuer, audience, expiration and user identity.
- **Browser-to-backend:** Browser communicates only with its same-origin Next.js server. The Next.js route retrieves a token server-side and forwards it to the configured FastAPI origin.
- **Not exposed:** No access tokens in localStorage, sessionStorage, React props, browser JSON, or public environment variables. The SDK's optional browser access-token endpoint is disabled.
- **Explicit boundaries:** The proxy permits only a configured HTTPS backend origin (or loopback HTTP in local development), supports listing empty synthetic cases and creating empty synthetic cases only, and rejects cross-origin POST requests.

## Before enabling login

1. Create an Auth0 tenant and a **Regular Web Application**. Use a separate development configuration from production.
2. Create an Auth0 custom API. Choose its identifier, for example `https://api.practicamia.example`. Enable RS256 signing for its access tokens.
3. Set the Auth0 application Allowed Callback URLs to `http://localhost:3000/auth/callback` for local development. For production add the exact approved canonical callback URL, for example `https://practicamia.vercel.app/auth/callback`.
4. Set Allowed Logout URLs to `http://localhost:3000` and the corresponding approved production URL.
5. Do not automatically authorize every temporary Vercel preview callback. Either leave authentication disabled on previews or use a separately controlled development app/domain.
6. Generate a new 32-byte random secret as 64 hexadecimal characters (for example via `openssl rand -hex 32`). Do not commit, paste into a public issue, or print the actual secret.
7. Store variables from `frontend/.env.example` in your **local `.env.local`**, and in Vercel's encrypted server-side environment settings when ready.

## Required Next.js variables

| Variable | Meaning |
| --- | --- |
| `AUTH0_DOMAIN` | Auth0 tenant domain **without** `https://` (e.g. `tenant.eu.auth0.com`) |
| `AUTH0_CLIENT_ID` | Regular Web Application client ID |
| `AUTH0_CLIENT_SECRET` | Regular Web Application client secret |
| `AUTH0_SECRET` | Random 64-character hexadecimal secret for encrypted session cookies |
| `AUTH0_AUDIENCE` | Custom Auth0 API identifier; must exactly match FastAPI `AUTH_AUDIENCE` |
| `APP_BASE_URL` | Frontend canonical origin; set for stable production and local URLs |
| `BACKEND_API_URL` | Optional server-only FastAPI origin (e.g. `https://api.example.com`); do not set until backend is securely hosted |

## Required FastAPI variables

- `AUTH_ISSUER=https://<AUTH0_DOMAIN>/` (include the final slash).
- `AUTH_JWKS_URL=https://<AUTH0_DOMAIN>/.well-known/jwks.json`.
- `AUTH_AUDIENCE=<AUTH0_AUDIENCE>`.
- `DATABASE_URL` for persistent PostgreSQL and `ENABLE_DEMO_CASE_API=1` only after confirming JWT validation and backend network boundaries.

**A signed-in browser session does not prove that the backend is deployed or connected.** The account page reports separate sign-in and backend availability states.

## User-visible pages

| Path | Behavior |
| --- | --- |
| `/account` | Explains disabled login, or shows sign-in/sign-out when Auth0 configured |
| `/cases/saved` | Requires session and backend config; lists only synthetic cases and permits creating an empty synthetic case |
| `/api/cases` | Same-origin BFF GET and CSRF-protected POST. Returns 503 until fully configured, 401 for signed-out users, and never returns access tokens |
| `/cases/new` and `/cases/demo` | Existing anonymous in-memory demo, unchanged |

Auth0 routes `/auth/login`, `/auth/logout`, and `/auth/callback` are mounted by SDK middleware only when configured. Browser navigation to login/logout uses normal anchors, not client-side prefetch.

## Verification

- `cd frontend && npm ci && npm test && npm run typecheck && npm run build`.
- Tests cover missing/partial server configuration, backend URL allowlisting, and POST Origin validation.
- GitHub Actions and Vercel check the unconfigured build, ensuring the anonymous demo remains available.
- **Not yet tested end-to-end:** Real Auth0 login, cookie renewal, custom API token issuance, live FastAPI connectivity. This requires an Auth0 tenant plus a private, authenticated backend.

## Security and deployment limitations

- Do not collect real personal addresses or documents through these endpoints. Only empty synthetic case records are supported.
- The backend is not deployed. Do not configure `BACKEND_API_URL` to a public unauthenticated service.
- Add API rate limiting, monitoring and non-sensitive audit events, retention/deletion rules, secure networking, and end-to-end tests before handling real records.
- Once FastAPI is deployed, do not assume browser CORS is the only authorization layer: verify JWTs and per-user owner checks on every backend request.

## Sources

- Auth0 Next.js SDK 4 documentation: https://auth0.github.io/nextjs-auth0/
- Auth0 SDK repository: https://github.com/auth0/nextjs-auth0
