# PracticaMIA — First Interactive Prototype

A responsive **Next.js + TypeScript** frontend prototype for the first PracticaMIA journey.

## Run locally

Requirements: Node.js 22 and npm with access to the npm registry. Dependencies are locked in `package-lock.json`.

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000.

Optional checks:

```bash
npm test
npm run typecheck
npm run build
```

> Vercel successfully built the Next.js application from GitHub commit `8edb961` on 4 November 2026. The build included type validation and static generation. Run `npm test`, `npm run typecheck`, and `npm run build` locally when developing; pull requests also run these commands via GitHub Actions.

## Standalone browser preview

Open `preview.html` in a browser. This is a self-contained **English-only interactive preview** that works without npm. The Next.js application also has the Italian translation. The preview was browser-tested on desktop and mobile.

## Routes

- `/` — welcome and how-it-works page
- `/cases/new` — demo case creation
- `/cases/demo` — five scope questions, synthetic intake, and illustrative checklist
- `/cases/demo/review` — read-only review and official guidance reference

## Important behaviors

- English/Italian language toggle; frontend labels only.
- Deterministic branches for supported demonstration / out of scope / information unknown.
- Input validation and reconfirmation after changing answers.
- Responsive desktop and mobile workspace.
- No backend, LLM, authentication, uploads, application generation or government submission.
- **No user data is saved or sent to a server.** Refreshing the browser resets the demo.
- Do not enter real personal information. Enter synthetic addresses.
- Passing the scope check is *only* a match for the demo scenario, not a government eligibility decision.
- Documentary requirements are intentionally not fabricated; they remain pending administrative review.

## Prototype checks

Eight tests in `tests/flow.test.mjs` cover matching scenario, missing information, unsupported paths, date/address intake validation and duplicate-address detection.

## Sources

The product behavior follows:

- `../docs/UX_INTERFACE_SPEC.md`
- `../docs/FIRST_USER_JOURNEY.md`
- `../research/milan_residence_change.md`

Official municipality guidance linked from the prototype:
https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza

## Next engineering milestone

Review usability, validate applicant-specific administrative requirements, then implement case persistence and a deterministic requirements engine before introducing LangGraph.

## Optional authentication scaffolding

The Account and Saved Demo Cases pages use a server-side Auth0 session when configured, but are **disabled by default**. See [authentication integration](../docs/AUTHENTICATION_INTEGRATION.md). The public guided demonstration does not save information and does not require login.
