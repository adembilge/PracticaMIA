# Single-chat product contract

## Binding customer experience

The only customer application interface is one ChatGPT-style conversation at `/`. Users write an ordinary-language message without creating, naming, selecting or opening a task record.

The conversation sidebar contains conversation history only. Every supported clarification, answer, evidence passage, confirmed fact, correction, approval, checklist, document review, form draft, status update and handoff appears inline in that same conversation.

There are no separate customer-facing task pages, dashboards, document workspaces, form editors, source browsers, procedure wizards or synthetic demos. Authentication and verified external government services are separate security/authority handoffs, not alternate PracticaMIA workflows.

## Private internal state

The backend may maintain owner-scoped internal task/workflow records for authorization, versioning, provenance and resumption. These records are implementation details and must never become a user-facing selector or prerequisite.

Historical storage identifiers and API adapters may remain temporarily while a verified migration is designed. Do not drop tables, delete existing user records, alter owner bindings or weaken privacy controls as part of frontend cleanup.

## Security invariants

1. An owner can retrieve only their own conversations, internal task state, attachments, artifacts and audit receipts.
2. A free-text first message does not require a task ID, procedure choice or form.
3. Extracted, inferred or model-authored values remain unconfirmed until the user explicitly approves them.
4. A change is shown as saved only after the exact server-side commit is confirmed.
5. Disconnects, retries and topic changes preserve authoritative conversation state and do not duplicate writes.
6. No unsupported source, invented deadline, legal eligibility claim or government-submission claim is permitted.
7. Customer document review and preparation remain inline in the chat.
8. Stale or archived internal state cannot be changed from an outdated control.
9. Any future storage migration must be reversible or independently verified and preserve owner isolation, retention and recovery.

## Current implementation status

The root route renders the single-chat shell. Legacy customer pages and demo surfaces are being removed. The UI shell does not imply that the agent is production-ready: the authenticated agent transport and worker remain restricted to isolated development/Preview infrastructure, and production execution is disabled.

## Acceptance

- Desktop and mobile root route show one conversation shell and one composer.
- No customer route exists for standalone tasks, documents, source browsing, demos or account workspaces.
- A signed-in owner can resume only their own conversation history and pending actions.
- Clarifications, citations and approval decisions remain consistent after refresh and reconnect.
- A second account cannot read or mutate another owner's conversation or internal task state.
- Production deployment SHA, Auth0 behavior, database ownership and operational controls are independently verified before release claims.
