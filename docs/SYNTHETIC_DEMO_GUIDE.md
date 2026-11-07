# PracticaMIA — approved synthetic-only interactive demonstration

**Authorization:** User approved development of a fictional PracticaMIA demo on 6 November 2026, explicitly excluding approval of real Comune di Milano sources or eligibility rules.

**Deployment boundary:** The new walkthrough is only available on **Vercel Preview** or local development at \`/demo/synthetic\`. Its server-rendered route calls \`notFound()\` in production. A corresponding preview-only navigation banner is absent from production. All existing case, knowledge, and reviewer APIs remain unchanged.

## Goal

Show a realistic **product interaction**, not a claim of legal accuracy or live AI capability:

1. Choose a fictional residence-change scenario.
2. Confirm invented applicant facts from constrained dropdowns.
3. See an illustrative deterministic decision, mock rule and clearly labelled non-official evidence.
4. Load an **embedded fictional sample document** and inspect a **simulated extraction** with page and evidence trace.
5. Explicitly confirm/correct the extracted value, including a conflict that blocks progress.
6. Review a structured fictional preparation package.
7. Approve it as a **demo participant** and reach a **simulated, non-submitting handoff**. Optionally export the synthetic JSON.

## Built-in scenarios

| Scenario | Expected behavior |
| --- | --- |
| Standard | Confirm facts → mock checklist → embedded sample → confirm field → review → package → simulated handoff |
| Missing information | Stops at missing simulated registration context, requires explicit answer; no checklist/package until resolved |
| Unsupported | Stops at intentionally excluded mock scenario (arrival from abroad / household join); no checklist/package |
| Conflict | Raw fictional document address differs from confirmed intake; review blocks until the participant corrects the field and re-confirms |

The rules do **not** describe Italian law. The embedded evidence ID \`SIM-EVIDENCE-001\` is intentionally fake and has no official URL. The UI states that no municipality has approved anything.

## Separation and privacy

- Source: \`frontend/src/lib/synthetic-demo.js\` (deterministic fixture engine); \`frontend/src/components/SyntheticDemoWorkspace.tsx\`.
- No external API, backend, Auth0, LangGraph, model, OCR, storage, real document upload, or official-site call is made by the synthetic workflow. The existing frontend still loads ordinary Next.js site resources.
- No freeform name/address entry: selections are restricted to the authored fictional fixtures. No persistence, localStorage or browser cookies are written by the demo workflow.
- The fake extraction is explicitly called **simulated**, not described as actual OCR.
- Status \`simulated_handoff\` is only for this demo. The exported package always contains \`simulation_only: true\` and \`government_submission_status: NOT_SUBMITTED\`.
- Neither this authorization nor this feature alters any \`KnowledgeSource\`, \`KnowledgeReviewEvent\`, reviewer allowlist, \`rules/catalog.json\`, source status, or real administrative checklist.
- No production schema migration is needed to try this preview-only browser walkthrough.

## Run and acceptance

From \`frontend\`:

\`\`\`bash
npm ci
npm test
npm run typecheck
npm run build
npm run dev
\`\`\`

Open \`http://localhost:3000/demo/synthetic\`. For a connected Vercel Git Preview deployment, open \`https://<exact-preview-host>/demo/synthetic\`. These URLs use the same client bundle but server gating relies on \`VERCEL_ENV=preview\` or local \`NODE_ENV=development\` without \`VERCEL_ENV\`.

Expected assertions (covered by \`tests/synthetic-demo.test.mjs\`):

- Production always returns a not-found route even if \`NODE_ENV\` is accidentally \`development\`.
- Unconfirmed facts, absent sample, unconfirmed extraction, unreviewed document and mismatched addresses cannot yield a package.
- Unknown and unsupported mock scenarios never invent a checklist or allow an approval.
- Corrected conflicts require a second explicit review.
- Editing facts invalidates prior package approval.
- Happy path ends in \`simulated_handoff\`, always marked \`NOT_SUBMITTED\`.
- No municipal URL is provided by the mock evidence or handoff.

## Not yet done / not claimed

This demo is **UI-only** and must not be presented as a verified live backend E2E. The opt-in authenticated preparation backend added in PR #34, approved official sources/rules, real OCR/malware checks, persistent multi-user privacy, production deployment and actual user-only official handoff are separate milestones. Keep the branch and PR in review until authorized integration and release checks are complete.
