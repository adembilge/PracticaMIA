# Product and engineering decisions

## D-009 — Keep development merges separate from Vercel release checks

The product owner approved continuing non-release development without waiting for Vercel's deployment quota. Review the diff, exact PR head, repository branch rules and required GitHub checks before merging. An automatic Vercel rate-limit failure is not a development-merge gate if GitHub permits the merge. Never report an unavailable deployment as successful.

This does not authorize changing Vercel project settings, billing, permissions, production aliases or release gates.

## D-010 — One customer conversation; no user-facing task entity

The product has exactly one primary customer interface: a ChatGPT-style conversation at the application root. Users start with free text. They do not create, name, select, open or browse internal task records.

Clarifications, evidence, confirmed facts, approvals, document review, preparation and status appear inline in the conversation. The sidebar contains conversation history only.

Private owner-scoped task/workflow state may remain in the backend for authorization, versioning, provenance and resumption. Historical storage names are implementation details, not product UX. Do not delete stored user records or drop old tables without a separately reviewed migration that proves owner mapping, recovery, retention and isolation.

No standalone dashboard, task page, document workspace, source browser, form editor or synthetic demo is part of the customer product. Human source review remains a protected operator function. Government login, payment, signing and submission remain user-controlled external actions.

## D-011 — Approved source cleanup and single-chat root migration

The product owner explicitly approved removing the legacy customer task/demo interfaces and making the single-chat shell the root UI as part of repository cleanup. This is a UI and repository cleanup decision, not authorization to delete production data, drop database tables, enable production agent execution or begin Phase 5.

Phase 4 remains active. Phase 5 remains paused until separately approved.
