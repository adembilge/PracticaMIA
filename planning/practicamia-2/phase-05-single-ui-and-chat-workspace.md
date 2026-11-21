# PracticaMIA 2.0 — Phase 5 · Single UI and chat workspace

> **D-010 binding product contract:** The only customer application is **one ChatGPT-style chat at `/`** with a conversation-history sidebar. No user-facing cases, case selection, case dashboard, document/form workspace, source browser, or feature-specific product page. A message starts a task; the agent maintains owner-scoped internal task state and all supported questions, evidence, uploads, actions, approvals and tracking appear as **inline chat cards**. Legacy `case_id` storage/routes are temporary compatibility only. See [single-chat contract](../../docs/SINGLE_CHAT_PRODUCT_CONTRACT.md). **Planning alignment only: Phase 5 is not started.**

**Roadmap tasks 41–50.** Deliver one user-facing chatbot interface for PracticaMIA. Users describe a task in their own words, answer the agent's questions, open official evidence, and see their next action. They can discuss multiple goals in the same conversation, or return to a prior conversation using chat history; internal task context is managed by the agent, not a user-facing case selector.

Connect the Phase 3 catalogue and Phase 4 agent API to real application data. Phases 6–8 add document handling, form preparation, checklist management, conversation and task history, and tracking **inside the same conversation**. Show actions only when the backend reports the capability available for the authenticated conversation and its internal task context.

**Binding product decision — one UI, one chat.** The customer has a single main conversation route and one message composer. Starting a procedure, asking questions, uploading documents, seeing OCR results, correcting fields, reviewing requirements and forms, approving changes, tracking progress, and resuming conversations all happen in the transcript using inline messages and interactive cards. Only a **conversation-history** sidebar is allowed; there is no customer case or task switcher. **Do not build standalone case dashboards, document workspaces, source browsers, form editor pages, separate task wizards, split-screen workspaces, or a separate Preview experience.** Sources and document pages may expand within the conversation without replacing it. An exported file is a downloadable result, not a second application screen. Government sign-in/payment/submission may still require an external official channel; show the verified handoff in chat and never claim the app performed it. Internal development, CI, and isolated test/staging deployments are engineering environments, not user-facing products or alternative UIs.

The [Phase 4 agent API handoff](phase-04-phase-05-handoff.md) records the implemented isolated routes, client state transitions, checked wire examples and integration decisions still open.

## Single-chat layout

| Element | Desktop | Mobile |
| --- | --- | --- |
| Conversation | One main transcript with persistent composer | The same transcript and composer, full width |
| Conversation history | Collapsible **conversations-only** sidebar; no case/task selector | Collapsible conversations drawer in the same chat shell |
| Questions, approvals and next steps | Interactive cards inserted at the relevant message | The same inline cards with touch-friendly controls |
| Sources, documents, forms and checklists | Expandable inline evidence, file, field and task cards | The same cards in the transcript; no route change or separate preview page |

Changing topic only changes agent context; there is no visible case concept or manual case selection. Expanded details must preserve composer drafts, transcript position, focus and the correct internal task binding. Keep official source links and downloads as explicit user actions.

## 41. Build the information architecture and application shell

- **41.1** Set up `/` as the sole user-facing chat route with one composer, new chat and conversation history. Source lookup, files and actions expand inside messages, never as standalone destinations.
- **41.2** Model the owner-scoped conversation separately from **internal task/workflow state**. A free-text question needs no case ID or task title. The agent detects task context and asks for disambiguation in chat; there is no case switcher.
- **41.3** Define chat-state URLs that reopen an authorised conversation or anchored message without navigating to a separate feature page. Expanding or closing an inline source, file or form preserves the originating message, scroll and focus.
- **41.4** Restore the authorised conversation, correct internal task context, draft-safe state and expanded inline detail from the backend after reload. For another account's link, show a safe unavailable message in chat.
- **41.5** Share component styles for headings, buttons, citations, cards, panels, errors, and progress. Use text and icons to convey status.

**Acceptance.** Users open a source and return to the same message. Reload restores the authorised conversation and pending in-chat action, with no case page, ID or selector.

## 42. Design the welcome and new-chat experience

- **42.1** Show a prompt such as “What do you need help with?” and a message field. Let users type before choosing an authority, document type, or procedure.
- **42.2** Offer three optional starting points covering finding an authority, understanding a notice, and tracking an application. Each opens an editable draft that the user can send.
- **42.3** Show the first reply directly in the conversation. Ask for a city, authority, or stage in plain language when it changes the next step.
- **42.4** For a returning user, show recent conversations and an in-chat resume suggestion with the pending action, never a case list. Keep the composer ready for an unrelated question.
- **42.5** Design Italian and English prompts, controls, empty states, and errors together. Keep official Italian terms in source and form views.

**Acceptance.** New users can send a question without selecting an example. Returning users can find an open task from the home view.

## 43. Implement message composition and attachments

- **43.1** Add a multiline composer and a visible Send control. Check keyboard behaviour and mobile viewport changes while entering text.
- **43.2** Model draft, sending, acknowledged, and failed states. Keep failed submissions editable.
- **43.3** Use the Phase 4 client message ID for safe retries and duplicate suppression.
- **43.4** Define per-file name, upload state, cancellation, and retry. A failed attachment preserves the message and other attachments.
- **43.5** Connect attachment availability to backend capability. Show actual progress once Phase 6 is enabled. Treat selection, upload, and processing as separate states.
- **43.6** Preserve the composer draft when expanding inline cards, switching conversations, or reopening message history. Avoid persisting sensitive drafts in unprotected browser storage.

**Acceptance.** Failed messages can be edited and retried without duplicates. A failed attachment does not remove other files or the draft.

## 44. Handle agent progress, streamed responses, and reconnection

- **44.1** Map Phase 4 events to acknowledged, running, awaiting input, completed, disconnected, and failed states.
- **44.2** Show progress backed by events, such as “Searching official sources.” Use determinate progress only when the backend provides it.
- **44.3** Place verified answers in the conversation. If the user is reading older messages, retain scroll position and offer a control to jump to the new answer.
- **44.4** Reconnect by run ID and last event sequence. Fetch missed events, display duplicates once, and reconcile with the final server state.
- **44.5** Connect Stop to the backend. Show distinct states for cancellation, a temporary disconnect, and an execution error. Reflect any changes already committed.
- **44.6** Keep verified partial output visible after a timeout. Retry with the current question and internal task context intact where possible.

**Acceptance.** Disconnecting and reconnecting during a response creates no duplicate output. Stop reports the actual result.

## 45. Build in-chat action, question, and approval cards

| Card | User action |
| --- | --- |
| Clarifying question | Choose an option or write an answer |
| Suggested action | Open, save, or defer the task |
| Approval request | Compare, correct, accept, or reject values |
| Official service handoff | Read what to do and open the verified channel |
| Document or form review | Open the relevant item or section when available |

- **45.1** Render cards from typed agent events. Show actionable controls only when an action ID and backend capability exist.
- **45.2** Make the primary action clear and appropriate to the card.
- **45.3** Show affected field, existing value, proposed value, and evidence on an approval card. Display the edited value before approval.
- **45.4** Handle pending, successful, declined, failed, and stale states. A stale card should link to the current proposal where available.
- **45.5** Show “Saved” or “Updated” after the server confirms the operation.

**Acceptance.** Users can answer a question, correct a value, and see the result in chat. Stale cards cannot change another internal task inadvertently.

## 46. Build the in-chat “What should I do next?” card

- **46.1** Include the current goal, next step, rationale, any missing input or document, and competent channel.
- **46.2** Show one primary in-chat action. Other goals are resumed through natural-language clarification or a previous **conversation**, not a case switcher.
- **46.3** Show whether a workflow event comes from a user note, agent proposal, receipt, or official status. Make the basis of a completion claim inspectable.
- **46.4** Use actionable recovery for missing data, unverified sources, and technical failures. Link to the corresponding question, source, or retry.
- **46.5** Disambiguate multiple administrative goals using an inline question, then show the correct next-action card for the server-bound internal task; never expose a customer case name or selector.
- **46.6** Refresh from backend conversation and internal task state after changes. Merely writing a chat message does not complete a task.

**Acceptance.** A returning user can find and understand the next step without rereading the conversation. A clarified topic switch displays the right task without a case selector.

## 47. Connect citations to the official catalogue

- **47.1** Put the citation control beside the claim it supports. Make the relationship clear when one paragraph refers to several sources.
- **47.2** Show authority, title, exact passage or PDF page, scope, and last check date. Label the official link clearly.
- **47.3** Distinguish the original Italian wording from the explanation. Preserve terms the user will need to find on the official page.
- **47.4** Use Phase 3 identifiers so citation expansion and the in-chat source search resolve to the same exact passage and version.
- **47.5** Mark the affected recommendation when a source changes or is withdrawn. Keep historical support visible on previous messages.
- **47.6** Verify mobile and keyboard navigation. Collapsing an inline passage returns focus and scroll position to the citation that opened it.

**Acceptance.** Users can reach the supporting official passage and return to the same place in chat.

## 48. Set the inline document, form, and history card structure

- **48.1** Define document name, type, upload and processing state, preview, and page reference components.
- **48.2** Define the form name and version, original labels, proposed values, evidence, and confirmation controls. Show the difference between missing and confirmed fields.
- **48.3** Show conversation and internal task events chronologically, including messages, attachments, proposals, corrections, and saved changes.
- **48.4** Standardise expand, collapse, in-chat anchors, scroll, and focus. Ask how to proceed when collapsing a card would discard an unsaved edit.
- **48.5** Pass inline-card contracts to Phase 6 for documents and pages, Phase 7 for forms and fields, and Phase 8 for tracking events.
- **48.6** Verify card composition with safe fixtures. Once real tools are enabled, render results in the same conversation bound to the correctly authorised internal task.

**Acceptance.** Document evidence, form review, and conversation history expand inline in one chat route. Later phases can supply data without adding a user-facing page or changing navigation.

## 49. Complete session, saving, and return flows

- **49.1** Make sign-in requirements clear according to product rules. Test questions, confirmed in-chat saves, personal attachments, and history independently.
- **49.2** Carry a safe internal return target during sign-in. Restore the intended conversation after successful authentication.
- **49.3** On expiry, show which operations completed and what must be retried after signing in again.
- **49.4** In the conversations-only sidebar show conversation title, last activity and optional safe pending-action indicator. Selecting a conversation restores the transcript, current internal task context and inline cards. Do not render cases or tasks as selectable entities.
- **49.5** Clear private data and visible internal task state when accounts change. Previous account messages, documents, and notes must disappear.
- **49.6** Use two test accounts for shared links, expiry, sign-in, conversation switching, and return behaviour.

**Acceptance.** Users resume authorised **conversations** after sign-in; there is no user-facing case. A second account cannot see the first account's messages, internal task state, documents or receipts.

## 50. Verify mobile, accessibility, and the full journey

- **50.1** Test desktop, tablet, and narrow mobile screens. Include long Italian authority names, source links, conversations, and the on-screen keyboard.
- **50.2** Complete the workflow with a keyboard. Verify focus when expanding and collapsing cards, correcting approvals, and switching conversations in the same chat.
- **50.3** Announce meaningful states such as new question, answer ready, and error. Avoid announcing each streaming update. Use [WCAG 2.2 AA](https://www.w3.org/TR/WCAG22/) as the accessibility target.
- **50.4** Measure initial usability, first status event, conversation scrolling, and detail open time. Load heavy viewers on demand.
- **50.5** Automate first question, clarification, source review, correction, saving, disconnect, and sign-in recovery.
- **50.6** Give a small user group a task without explaining the interface. Observe where participants cannot identify the next action and prioritise fixes.

**Acceptance.** The core journey works on desktop and mobile, by keyboard, and after connection loss. Returning from a source preserves conversation context.

## Implementation order

| Slice | Tasks | Evidence |
| --- | --- | --- |
| First working journey | 41–42 and the core of 43–44 | Send a real agent message and receive a verified answer |
| Advance a task | 45–47 | Answer a question, inspect the source, and find the next action |
| Return to the same task | 48–49 and reconnection in 44 | Resume after collapsing a card, closing the tab, or signing in again |
| Verify the journey | 50 | Mobile, keyboard, and network interruption tests pass |

**End-to-end demonstration.** The user starts with free text and completes clarification, cited-source expansion, an authenticated in-chat save receipt and conversation resumption **without leaving the chatbot route or seeing a case object**. Phase 6 adds in-chat document upload, extraction review and confirmation; Phase 7 adds inline checklist/form preparation and official handoff; Phase 8 adds conversation history, internal task events and tracking through the same composer. Any external government interaction is a clearly labelled link-out, not another PracticaMIA UI.
