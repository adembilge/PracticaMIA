# PracticaMIA frontend

Next.js 15, React 19 and TypeScript. The root route `/` is the single customer conversation interface. There are no separate customer task, document, demo or account workspaces.

## Development

Requires Node.js 22.

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`. The chat shell can render without credentials. Sending messages requires a configured Auth0 session and an accessible agent API. Agent transport remains restricted to isolated development/Preview infrastructure; production execution is disabled.

Store local configuration in ignored environment files. Auth0 secrets and backend access tokens must remain server-side.

## Verification

```bash
npm test
npm run typecheck
npm run build
```

Frontend CI runs unit tests, TypeScript checks, a production build and a real localhost HTTP smoke test. The separate Synthetic MVP Acceptance workflow mounts the actual chat component in Chromium against FastAPI and disposable PostgreSQL with short-lived synthetic RS256 identities.

## Structure

- `src/app/page.tsx` — single-chat entry route.
- `src/app/api/agent/` — authenticated, allowlisted conversation proxy.
- `src/app/api/conversations/tasks/` — private inline request-details adapter.
- `src/components/SingleChatWorkspace.tsx` — chat transcript, composer and conversation history.
- `src/components/AgentSourceCards.tsx` — inline approved-source citations.
- `src/components/AgentOfficialHandoff.tsx` — verified external handoff.
- `src/components/RequestDetailsCard.tsx` — inline confirmed-information review.
- `src/app/knowledge/review/` — protected operator-only source review surface.

PracticaMIA is independent of the Italian government and does not submit applications on a user's behalf.
