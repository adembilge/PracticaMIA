# Phase 4 — Single-chat migration gap audit

**Snapshot:** 21 November 2026. **Product decision:** [D-010](DECISIONS.md) / [single-chat contract](SINGLE_CHAT_PRODUCT_CONTRACT.md). **Classification:** implementation gap, not evidence of release. No Phase 5 implementation was authorised by this audit.

## Verdict

**The current hosted app is not yet the requested ChatGPT-style single-chat product.** The *architecture decision* and active future-phase requirements now require one app shell, one composer, conversation-only sidebar, and all features as inline conversation cards. The *existing frontend* still renders editorial marketing and independent case workflows. The Phase 4 isolated chat fixture demonstrates portions of the intended behavior, but its local test server and synthetic sessions are not the hosted application.

## Current-to-target matrix

| Surface/capability | Verified repository location | Current status | D-010 target | Delivery gate |
| --- | --- | --- | --- | --- |
| Main customer entry | `frontend/src/app/page.tsx`; `HomeView.tsx` | Editorial landing, directs user to a saved/new case | Root `/` is the actual chat shell and free-text composer | Phase 5; no go yet |
| Main navigation | `frontend/src/components/SiteHeader.tsx`; `frontend/src/app/cases/**` | Distinct case/account and related feature pages | Conversation history only; no user-facing case entity | Phase 5 |
| Isolated conversation prototype | `frontend/tests/acceptance/agent-reconnect.tsx` | Local-only chat with questions, approvals, history and inline saved intake | Integrate equivalent typed components into real authenticated hosted shell | Phase 4 contracts / Phase 5 integration |
| Conversation service | `backend/app/agent/reconnect_router.py` | Isolated authenticated route builder, not blanket production/customer enablement | Production-ready owner-scoped conversation API with scheduler and reconnect | Phase 4/5 gated |
| Legacy case storage | `backend/app/cases/**`; `/api/v1/cases/**` | Real owner-scoped persisted legacy data | Hidden internal task/workflow layer behind chat | Design/migrate in Phase 5/8; preserve data |
| Requirement and intake UI | `CaseIntakePanel.tsx`, `CaseJourneyPanel.tsx`, `SavedCaseWorkspace.tsx` | Independent case panels | Inline questions, checklists, field approvals and typed receipts | Phase 5/7 |
| Document review | Existing document UI/proxies and private-document checks | Gated legacy feature and CI fixtures | Attachment/OCR review inline within chat messages | Phase 6; privacy gates |
| Official evidence review | Approved-source services plus legacy knowledge pages | Operator/customer surfaces remain separated | Inline citation evidence for customer; authorized operator review remains protected | Phase 5/7 |
| Conversation/timeline | Phase 4 encrypted agent events and history APIs | Local signed API/browser tests | Conversation sidebar, restored ordered events, in-chat milestones | Phase 5/8 |
| Multi-authority procedures | 3-authority Phase 4 source worksheet | Candidate claims pending human review | Ask freely, disclose unsupported scope, never invent instructions | Human review + pilot |
| Live account isolation | Auth0 manual case read/PDF observations; opt-in two-account harness | Partial real identity evidence; new write matrix not confirmed live | Cross-user protection for every chat/task/doc/artifact and retained old deep link | Live staging/release gate |

## Immediate engineering guardrails (Phase 4)

- Treat `docs/SINGLE_CHAT_PRODUCT_CONTRACT.md` as the authoritative UX requirement. Keep the earlier 94-task source record intact for provenance, but do not build its historical 12-page UI.
- Keep Phase 4 agent event, clarifications, corrections, approvals, history and tenant tests in place; do not rewrite those integration tests to depend on a visible case switcher.
- Mark legacy case screens and `case_id` API as *migration only*, without removing existing user records or weakening security.
- Every feature proposal must document its in-chat event/card, authorization boundary and current backend capability. No separate customer route is an acceptable delivery shortcut.
- The user explicitly paused Phase 5; updating this roadmap, design and acceptance evidence is **not** approval to begin its implementation.

## Product acceptance script (future hosted build; not executed here)

1. Open `/` on desktop or 390px viewport; user sees chat transcript and composer, not a "Prepare my case" CTA.
2. Enter “I want to register a new address in Milan” without any wizard or case creation.
3. Respond to the inline clarification and open an approved-source citation inside the same chat.
4. Attach an approved synthetic file, see extraction progress and a page/field card in the conversation; confirm one field explicitly.
5. View requirements, next action, corrected values and a generated draft in the same transcript; download without visiting another app page.
6. Change topic to another Italian administrative question; the agent clarifies and scopes internal task state automatically without exposing a case switcher.
7. Reload and reopen a previous conversation from the sidebar, preserving confirmed receipts and preventing duplicate writes.
8. Open the same conversation as a second signed-in account: API and UI must deny access to messages, documents, task state and generated artifacts.
9. Verify that a pending/unapproved official source cannot produce verified guidance or a live external filing link.
10. Verify URL changes, focus and network events: the app remains the **one chat shell** throughout all supported customer steps.

Passing the current 33-scenario synthetic browser harness or an earlier two-account case test does **not** satisfy these hosted single-chat acceptance steps.

## Migration dependency and risk register

- **High:** Existing saved cases and attachments must remain owner-scoped during rekeying into conversation-linked internal tasks. Require reversible mapping, dual-read checks and incremental deployment; never drop records as a UI shortcut.
- **High:** Hosted agent transport, worker scheduling and Auth0 session integration must be separately validated; local fixture success is insufficient.
- **High:** Source approval, correctness, submission-state honesty and real-document security review remain independent mandatory gates.
- **Medium:** Scroll, focus, keyboard/mobile cards, long conversation history and safe account switching need explicit full-route browser E2E.
- **Medium:** Legacy links and user-visible "case" text in the current live deployment remain noncompliant until Phase 5 migration.
- **Low:** Historical file/folder names may remain for audit; customer UI must not expose the underlying case concept.

**Current release verdict:** **Not D-010-compliant yet; planned migration only.** Phase 5 remains blocked; Phase 4 research, signed-agent tests and human-source/pilot work continue.
