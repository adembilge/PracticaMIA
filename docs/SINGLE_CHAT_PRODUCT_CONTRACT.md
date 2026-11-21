# PracticaMIA — Single-Chat Product Contract

**Decision:** D-010, 21 November 2026. **Status:** binding target architecture, NOT a claim that the hosted application already implements it. **Current execution:** Phase 4 only; Phase 5 is not authorised to start. This contract supersedes legacy multi-screen examples wherever they disagree.

## Product in one sentence

PracticaMIA is **one ChatGPT-style conversational assistant** for navigating Italian administrative procedures. A user describes their need in ordinary English or Italian and **does everything inside that same chat**: understand requirements, clarify facts, upload and review documents, check official evidence, approve changes, prepare outputs, track progress, and resume past conversations.

**There is no user-facing case, case creation, case workspace, case list, case switcher, dashboard, document center, form editor, or multi-page procedure wizard.** No user action may require a visit to a separate PracticaMIA feature page. A verified **external government portal** remains a possible user-controlled handoff; hosted Auth0 login and legally required policy information are supporting infrastructure, not product workflows. Protected human source review is an operator-only function.

## Primary UX contract

```text
  ┌──────────────────────┬────────────────────────────────────────────┐
  │ PracticaMIA          │  New conversation                         │
  │ + New chat           │                                            │
  │                     │  User: I received a notice from Torino.   │
  │ Conversation history│                                            │
  │ · Residence question│  Assistant: Who issued it?                │
  │ · Torino notice     │  [Choose authority] [Not sure]            │
  │ · Permit renewal    │                                            │
  │                     │  User: [attachment.pdf]                   │
  │                     │  [Inline document / OCR review card]       │
  │                     │  [Inline evidence and source card]         │
  │                     │  [Inline next-step / approval card]         │
  │                     │                                            │
  │                     │  ┌──────────────────────────────────────┐ │
  │                     │  │ Ask anything…                Attach Send│ │
  └──────────────────────┴────────────────────────────────────────────┘
  Mobile: collapsible history drawer, full-width transcript, persistent composer.
```

The sidebar contains **conversations only**, never separately created cases or tasks. One conversation can discuss several authorities or related procedures. The agent detects a topic change, asks for clarification, and binds the relevant internal work item automatically. If needed, the assistant offers a **message-level action** to continue a previous topic; the user is never sent to a case page or asked to create a case object.

### In-chat event and card palette

| Need | User sees in the transcript | Server control |
| --- | --- | --- |
| Unknown task or city | A clarifying question with options or free text | Procedure/jurisdiction resolution |
| Reliable procedural answer | Explanation with expandable reviewed official citations | Approved source and scope checks |
| Document | Attachment chip, progress, page preview and OCR field confirmation | Private object authorization, scanner, extraction |
| Requirements | Expandable requirements/checklist and next-step card | Versioned deterministic rules |
| Form or application draft | Inline field review, correction and explicit approval; downloadable artifact | Version and server-confirmed write |
| Multiple tasks | Assistant context cue and chronological events in the same chat | Scoped internal task association |
| Deadline/receipt | Inline timeline, evidence type and reminder action | Receipt provenance, date validation and delivery |
| Uncertain, failed or stopped action | Clear status and safe retry; no invented success | Encrypted journal and exact persisted receipt |
| Resume a conversation | Select earlier conversation in sidebar; continue in same composer | Owner-scoped conversation history and cursor |

No decorative or fake model responses should claim unsupported capabilities. Assistant may offer an official site link only when approved current evidence supports that handoff. No automatic SPID/CIE login, payment, signing, or government submission.

## Public application routes

**Target customer application**: `/` is the single chat shell. Optionally `/?conversation=<opaque-id>` or a chat-path alias may deep-link **to that same shell**, after authentication and ownership revalidation. New chat, past chats, files, citations, approvals, settings and status are inline controls/dialogs in the shell. No standalone `/cases/*`, `/knowledge/*`, `/demo/*`, `/account` workflow or alternate Preview UI. Legal/privacy pages and external identity-provider/official-government URLs are not alternative task workflows.

**Current repository reality:** legacy `/cases/*`, `/demo/*`, `/knowledge/*`, `/account` and the editorial landing page still exist, and the isolated agent-chat reference is at `frontend/tests/acceptance/agent-reconnect.tsx`. They are **migration inventory**, not approved final UX. Keep existing test/staging contracts intact while building a safe, feature-gated migration. Do not silently redirect routes until signed-in history and saved information are proven recoverable. Do not call the current hosted UI compliant with this contract.

## Data and agent architecture

```text
  One chat shell + one composer
         │ server-owned authenticated session
         ▼
  Conversation API + encrypted event journal + stream/reconnect
         │ one specialist LangGraph agent
         ├─ Scope and intent detection / clarification
         ├─ Approved official-source RAG and citations
         ├─ Deterministic requirements/verified handoff
         ├─ Typed internal task/fact state and approvals
         ├─ Private document intake / OCR / field review
         └─ Artifact generation / receipts / progress
         ▼
  Per-user conversation + internal task states + provenance (PostgreSQL)
```

**No user-visible case entity exists in the target product.** The backend still needs owner-scoped internal workflow/task state and durable facts to prevent cross-topic leaks, accidental updates or duplicate actions. Use `conversation_id`, `thread_id`, `task_id`, `run_id`, `document_id`, `approval_id` as implementation identifiers when needed, but never make a case ID or case-selection operation a prerequisite for the user. A task is discovered from conversation context or an explicit **in-chat** clarification, not a separate user-created record. Current `cases` tables and `case_id` APIs are **legacy migration adapters only**; replace or encapsulate behind conversation-owned task services after schema design, encrypted-history migration and authorization tests. Do not drop tables or delete existing records casually.

### State and security invariants

1. One owner can retrieve only their own conversations, task state, attachments, artifacts and audit receipts, across all API routes, tools and cached UI state.
2. A free-text first message works without a case ID, procedure selection or form.
3. User messages cannot directly turn extracted, inferred or model-authored values into confirmed facts; show explicit inline approval.
4. An action shows **saved** only after the exact committed server-side event; accepted but unapplied proposals remain pending.
5. Model failure, disconnect and topic switch preserve the authoritative conversation; retries have idempotent message IDs.
6. No unsupported source, invented deadline, claim, successful official submission or legal eligibility result.
7. User-facing UI stays on a single chat shell during document review, form corrections, source inspection and multi-task progress.
8. Historic or archived internal work cannot be silently changed from stale chat controls; restoration requires an explicit authenticated in-chat action.
9. Migrate existing stored data only with reversible/verified backfill, owner binding, and no privacy regression.

## Phase-by-phase migration and delivery gates

| Phase | Required target architecture | Current interpretation |
| --- | --- | --- |
| **4 — now** | Conversation-first state/event contracts, intent, evidence, multi-topic clarifications and in-chat approval/history prototypes. Close legacy UX gaps in architecture documentation and acceptance requirements. | Continue Phase 4 and its approved human pilot/review gates; **do not start Phase 5**. |
| **5 — planned** | Replace editorial landing, /cases pages and isolated test fixture with a **real hosted single chat shell** at `/`. Inline sources, questions, approvals and saved conversation history. | Blocked until Phase 4 handoff and explicit go-ahead. |
| **6 — planned** | Document upload/OCR/page review **inside messages**; no document portal. | Security/review gates still apply. |
| **7 — planned** | Requirements, checklists, form preparation, download and verified external handoff **inside chat**. | Do not activate unreviewed rules. |
| **8 — planned** | Internal tasks, receipts, deadlines, reminders, corrections, archive/export/delete managed **conversationally**. | No cases screen or case switcher. |
| **9 — planned** | Privacy, isolation, accessibility and evaluation with **single-route** E2E tests. | No production release inferred. |
| **10 — planned** | Pilot, review, gated release and growth of **one-chat product**. | Human approval required. |

### Legacy-to-target migration inventory

| Legacy artifact | Future disposition |
| --- | --- |
| `frontend/src/components/HomeView.tsx`, `frontend/src/app/page.tsx` | Replace entry experience with real authenticated chat, not a hero/marketing plus "Prepare my case" CTA. |
| `frontend/src/app/cases/**` and legacy `SavedCaseWorkspace` | Remove from customer navigation after validated conversation migration; preserve old links through an owner-checked recovery flow inside chat. |
| `frontend/src/app/demo/**`, customer `knowledge/**` | Retire separate product screens; preserve CI fixtures and protected operator source-review tools outside consumer product. |
| `frontend/src/components/CaseIntakePanel.tsx`, `CaseJourneyPanel.tsx` | Extract typed inputs/checklist as **inline chat cards**; never navigate to a case page. |
| `frontend/tests/acceptance/agent-reconnect.tsx` | Promote tested events, history, pending questions and approval cards into the hosted shell; isolated harness remains for regression. |
| `backend/app/cases/**`, `/api/v1/cases/**`, legacy `case_id` FKs | Retain as compatibility while introducing conversation-bound task services; migration must prove no cross-owner loss or unintended data deletion. |
| Legacy product spec 12-stage roadmap and numbered 94 tasks | Preserve as historical task IDs and audit reference; **do not** use its multi-screen chapter as current UX instructions. |
| Phase 4–10 active PracticaMIA 2.0 plans | Apply this contract to **every** phase without renumbering; tasks use chat-first journey and internal task identifiers. |

## Required acceptance tests before saying the product matches this decision

- On desktop and 390px mobile, a new visitor sees **one conversation surface** and can enter free text without a case or authority selection.
- After sign-in, a user can complete an entire synthetic flow (question, optional attachment, reviewed citation, correction, checklist, PDF, external handoff) without navigating to another PracticaMIA feature route.
- Multiple conversations appear only in the chat sidebar. A new topic does not reveal an internal task/case ID or force a case switcher.
- Refresh, browser restart and account change preserve only correct owner-scoped history, cards and confirmed receipts.
- Old saved records are correctly recovered or explicitly migrated; old deep links cannot expose inaccessible data.
- Every Phase 5–10 acceptance test includes the **single chat route** invariant. Dedicated development/operator routes are excluded from customer-route counts but cannot be linked as customer workflow steps.
- The precise deployed commit, live Auth0/Neon account isolation, source approvals, privacy gates and real participant outcomes are independently confirmed.

**Definition of done:** This file and decision log establish the contract. They **do not** certify that the current UI or API has been migrated. Only full hosted implementation plus passing acceptance evidence can do so.
