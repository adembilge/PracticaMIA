# PracticaMIA 2.0 — Phase 5 · Single UI and chat workspace

**Roadmap tasks 41–50.** Deliver the chat-centred PracticaMIA web application. Users describe a task in their own words, answer the agent's questions, open official evidence, and see their next action. They can switch between tasks within a conversation and return later to the active case and pending step.

Connect the Phase 3 catalogue and working Phase 4 agent API to real application data. Phase 6 connects document upload and review to its processing pipeline. Phase 7 connects form preparation. The interface uses backend capability information to expose actions actually available for the case.

## Workspace layout

| Area | Desktop | Mobile |
| --- | --- | --- |
| Navigation | Compact menu for New Chat, My Cases, and Official Sources | The same destinations in a top menu |
| Chat | Main area for messages, questions, and action cards | Full-width main view |
| Next action | Expandable panel alongside an active case | Short chat card with a detail view |
| Source, document, or form | Detail panel opens on selection | Full-screen detail with a clear return path |

Chat stays the primary workspace at each size. Show the active case name and its next action. Open detail on demand and retain the case name in the detail view.

## 41. Build the information architecture and application shell

- **41.1** Set up three entry points. New Chat starts with free text. My Cases lists saved matters and pending actions. Official Sources opens the Phase 3 catalogue within the same shell.
- **41.2** Model the active conversation and case separately. A general question can exist without a case title. When the user switches to another case, update its detail panels.
- **41.3** Define route and panel behaviour. Deep-link to an authorised source or saved view. Browser back and panel close return to the originating message or list.
- **41.4** Restore authorised chat, selected task, and open detail from the backend after reload. Show a safe access state for another account's link.
- **41.5** Share component styles for headings, buttons, citations, cards, panels, errors, and progress. Use text and icons to convey status.

**Acceptance.** Users can open a source and return to the same message. Reload restores the authorised case and view.

## 42. Design the welcome and new-chat experience

- **42.1** Show a prompt such as “What do you need help with?” and a message field. Let users type before choosing an authority, document type, or procedure.
- **42.2** Offer three optional starting points covering finding an authority, understanding a notice, and tracking an application. Each opens an editable draft that the user can send.
- **42.3** Show the first reply directly in the conversation. Ask for a city, authority, or stage in plain language when it changes the next step.
- **42.4** For someone with an open case, offer a single resume link showing its name and pending action. Keep new chat available.
- **42.5** Design Italian and English prompts, controls, empty states, and errors together. Keep official Italian terms in source and form views.

**Acceptance.** New users can send a question without selecting an example. Returning users can find an open task from the home view.

## 43. Implement message composition and attachments

- **43.1** Add a multiline composer and a visible Send control. Check keyboard behaviour and mobile viewport changes while entering text.
- **43.2** Model draft, sending, acknowledged, and failed states. Keep failed submissions editable.
- **43.3** Use the Phase 4 client message ID for safe retries and duplicate suppression.
- **43.4** Define per-file name, upload state, cancellation, and retry. A failed attachment preserves the message and other attachments.
- **43.5** Connect attachment availability to backend capability. Show actual progress once Phase 6 is enabled. Treat selection, upload, and processing as separate states.
- **43.6** Preserve drafts across in-app panel changes. Avoid assuming persistent browser storage for text that can contain personal data.

**Acceptance.** Failed messages can be edited and retried without duplicates. A failed attachment does not remove other files or the draft.

## 44. Handle agent progress, streamed responses, and reconnection

- **44.1** Map Phase 4 events to acknowledged, running, awaiting input, completed, disconnected, and failed states.
- **44.2** Show progress backed by events, such as “Searching official sources.” Use determinate progress only when the backend provides it.
- **44.3** Place verified answers in the conversation. If the user is reading older messages, retain scroll position and offer a control to jump to the new answer.
- **44.4** Reconnect by run ID and last event sequence. Fetch missed events, display duplicates once, and reconcile with the final server state.
- **44.5** Connect Stop to the backend. Show distinct states for cancellation, a temporary disconnect, and an execution error. Reflect any changes already committed.
- **44.6** Keep verified partial output visible after a timeout. Retry with the current question and case intact where possible.

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

**Acceptance.** Users can answer a question, correct a value, and see the result in chat. Stale cards cannot change the current case inadvertently.

## 46. Build the “What should I do next?” panel

- **46.1** Include active case, next step, rationale, any missing input or document, and competent channel.
- **46.2** Show one primary action, such as reviewing a value or opening the official service. Keep other tasks reachable in the same panel.
- **46.3** Show whether a case event comes from a user note, agent proposal, receipt, or official status. Make the basis of a completion claim inspectable.
- **46.4** Use actionable recovery for missing data, unverified sources, and technical failures. Link to the corresponding question, source, or retry.
- **46.5** Show the case name when several tasks exist. Switching cases replaces the previous next action with the current case's action.
- **46.6** Refresh from backend case state after changes. Merely writing a chat message does not complete a task.

**Acceptance.** A returning user can find and understand the next step without rereading the conversation. Switching cases shows the right task.

## 47. Connect citations to the official catalogue

- **47.1** Put the citation control beside the claim it supports. Make the relationship clear when one paragraph refers to several sources.
- **47.2** Show authority, title, exact passage or PDF page, scope, and last check date. Label the official link clearly.
- **47.3** Distinguish the original Italian wording from the explanation. Preserve terms the user will need to find on the official page.
- **47.4** Use Phase 3 identifiers so the chat citation and Official Sources view resolve to the same passage and version.
- **47.5** Mark the affected recommendation when a source changes or is withdrawn. Keep historical support visible on previous messages.
- **47.6** Verify mobile and keyboard navigation. Closing the detail returns focus and scroll position to the citation that opened it.

**Acceptance.** Users can reach the supporting official passage and return to the same place in chat.

## 48. Set the shared document, form, and history panel structure

- **48.1** Define document name, type, upload and processing state, preview, and page reference components.
- **48.2** Define the form name and version, original labels, proposed values, evidence, and confirmation controls. Show the difference between missing and confirmed fields.
- **48.3** Show case events chronologically, including messages, attachments, proposals, corrections, and saved changes.
- **48.4** Standardise open, close, deep links, scroll, and return. Ask how to proceed when closing a panel would discard an unsaved edit.
- **48.5** Pass contracts to Phase 6 for documents and pages, Phase 7 for forms and fields, and Phase 8 for tracking events.
- **48.6** Verify component structure with safe fixtures. Once real tools are enabled, render their backend results in the corresponding case.

**Acceptance.** All three panels open in the same case context and return to chat. Later phases can supply data without changing navigation.

## 49. Complete session, saving, and return flows

- **49.1** Make sign-in requirements clear according to product rules. Test questions, case saving, personal attachments, and history independently.
- **49.2** Carry a safe internal return target during sign-in. Restore the intended conversation or case after successful authentication.
- **49.3** On expiry, show which operations completed and what must be retried after signing in again.
- **49.4** In My Cases, show name, status, last update, and next action. Reload case context and related conversation when selected.
- **49.5** Clear private data and visible case state when accounts change. Previous account messages, documents, and notes must disappear.
- **49.6** Use two test accounts for shared links, expiry, sign-in, case switching, and return behaviour.

**Acceptance.** Users resume authorised tasks after sign-in. A second account cannot see the first account's data through links or UI caches.

## 50. Verify mobile, accessibility, and the full journey

- **50.1** Test desktop, tablet, and narrow mobile screens. Include long Italian authority names, source links, conversations, and the on-screen keyboard.
- **50.2** Complete the workflow with a keyboard. Verify focus when opening and closing a panel, correcting approval, and switching cases.
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
| Return to the same task | 48–49 and reconnection in 44 | Resume after leaving a panel, closing the tab, or signing in again |
| Verify the journey | 50 | Mobile, keyboard, and network interruption tests pass |

**End-to-end demonstration.** The user starts in free text, answers a short clarification, opens the official passage, saves the next action, and finds it again after leaving the page. Use the real agent and catalogue. Phase 6 adds document reading and verification to that working journey.
