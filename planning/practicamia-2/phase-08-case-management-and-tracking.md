# PracticaMIA 2.0 — Phase 8 · Case management, tracking, and cross-authority work

**Roadmap tasks 71–80.** Help a user resume an existing case, see the next action they can take, track what happened outside PracticaMIA, and manage related procedures across authorities through the same chat workspace and specialist agent.

**Dependencies.** Phase 3 supplies reviewed procedures, authorities, jurisdictions, and official channels. Phase 4 supplies authorised tools and persistent conversation state. Phase 5 supplies the shared chat, action cards, and workspace panels. Phase 6 supplies reviewed document evidence and access controls. Phase 7 supplies the versioned checklist, approved fields, and handoff event. Tracking must reference that event so submission evidence can be tied to the right case and preparation version.

**First vertical slice.** Select two independently verified pilot procedures with a realistic relationship. Start with manual receipt capture, a timeline, and a next action the user can resume from chat. Add deadlines, reminders, and cross-authority dependencies in subsequent slices. The automated acceptance scenario uses synthetic case data and receipts. The competent office, route, document reuse, and any procedural prerequisite must be verified before exposing a live procedure.

## 71. Model case preparation, submission, and authority status

- **71.1** Define a durable case ID, procedure and version, jurisdiction, competent authority, owner, and revision. Link the Phase 7 handoff record to the preparation revision that produced it.
- **71.2** Model preparation, submission evidence, authority observations, and workspace lifecycle independently. The case can be open for follow-up after submission, archived while awaiting an outcome, or preparing revised documents while an earlier attempt remains recorded.
- **71.3** Define preparation states for collecting information, needs review, and preparation complete. A later rule or form revision may reopen preparation for the affected items. Keep earlier handoffs and submission attempts pinned to their original versions.
- **71.4** Represent each submission attempt separately. Distinguish no submission evidence, user-reported submission, and matched submission receipt. Record authority-confirmed progress or decisions as observations with their own verified evidence and the exact status supported.
- **71.5** Define the allowed transitions with required evidence, actor, permission, and expected revision. Draft exports and official link opens record preparation activity. The agent can propose a case update through a typed tool. The backend checks permissions and evidence before writing.
- **71.6** Persist state changes and their timeline events atomically. Use idempotency keys for retries and expected revisions for concurrent updates from chat and the UI. On conflict, show the latest state and offer a review of the proposed change.

**Acceptance.** Preparing a draft, reporting a submission, recording a matched receipt, and confirming an authority decision produce four distinguishable results. Reloading the workspace restores them with the same evidence and dates.

## 72. Build the task and dependency model

- **72.1** Define a task with a stable ID, type, owning case, responsible party, completion criterion, source, and current state. Cover user action, evidence review, official follow-up, and waiting for an external event.
- **72.2** Support hard prerequisites and advisory ordering. Bind a dependency to the exact artifact or event required, such as a reviewed document revision or an authority acknowledgment. Validate the graph for cycles and invalid links when saving a template or connecting cases.
- **72.3** Use machine-readable reasons for blocked, actionable, waiting, completed, and cancelled tasks. A missing prerequisite names the task or evidence that would unblock it. Unresolved applicability stays visible as a review task.
- **72.4** Reuse a reviewed document through an authorised reference to its exact version. Recheck access and acceptance for each destination. Keep a record of where that version was used after handoff. Invalidation or access removal reopens dependent preparation where appropriate.
- **72.5** Recalculate affected tasks when evidence, deadlines, or rules change. Preserve unrelated completion and keep previously submitted attempts available. A failure to re-evaluate leaves the affected requirement in review.
- **72.6** Rank next actions deterministically by verified urgency, prerequisites that unblock work, and stable tie-breaks. The same ranked actions feed chat and case cards. Keep actionable work visible when a different branch is blocked.

**Acceptance.** A task can wait on one specific document revision while an independent task remains actionable. Withdrawing sharing of that document removes future access in the dependent case and identifies the replacement action.

## 73. Add a case timeline and correction history

- **73.1** Record document review, approval, preparation, handoff, submission report, receipt review, authority observation, deadline change, reminder, and closure events with typed payloads.
- **73.2** Store event occurrence time and tracking time separately. Capture the actor or source, affected case and attempt, and evidence reference. Label dates and times whose precision or source is limited.
- **73.3** Implement corrections and supersession. Keep the current claim clear, link to the corrected event, and recalculate affected status, tasks, or dates. The history remains subject to the case retention and deletion rules.
- **73.4** Show a concise default timeline with expandable details. Use labels like “You reported submitting”, “Submission receipt recorded”, and “Decision confirmed by the authority” only when the corresponding event qualifies.
- **73.5** Provide case-scoped timeline reads to the agent and UI. Authorise every evidence dereference. Keep raw documents, credentials, and unrestricted personal data out of event payloads and operational logs.
- **73.6** Test late-arriving events, retry duplicates, conflicting observations, partially dated evidence, and redaction. Preserve stable event order and show the last observed authority status with its observation date.

**Acceptance.** A user can answer “What happened last and how do we know?” A corrected receipt or source update changes the current view with a visible explanation and an appropriate audit trail.

## 74. Track deadlines and their provenance

- **74.1** Define three date types: a date stated by the authority in a notice, a date calculated from a reviewed rule, and a user-selected personal reminder. Render a date-only value as such when the evidence gives no exact time.
- **74.2** For notice dates, store the source document, exact page or field, date as printed, interpreted local date, and review status. Treat ambiguous OCR, multiple conflicting dates, and an unconfirmed document match as needing review.
- **74.3** For calculated dates, record the rule version, trigger event and its evidence, calendar and timezone, counting convention, exceptions, and explanation. For any holiday or extension logic, require the applicable reviewed rule and calendar. Run calculation in deterministic code.
- **74.4** Represent missing trigger, unverified trigger, conflicting dates, and unavailable rules. Show what is missing and where to verify it. Treat issue, delivery, access, and other event times as separate facts whose relevance depends on the reviewed rule for that procedure.
- **74.5** Recompute when a source, event, or calendar changes. Keep the earlier calculation and its evidence visible within retention policy, mark it superseded, and queue any dependent reminder for reconciliation.
- **74.6** Test date-only displays, midnight and daylight saving boundaries, a missing trigger, an authority-stated date that differs from a calculated date, calendar exceptions, and a corrected event. Use Europe/Rome in Italian local-time test cases where the procedure uses that timezone.

**Acceptance.** Every displayed administrative deadline has traceable evidence and precision. Missing or conflicting evidence yields a review action and a verified next step instead of a guessed date.

## 75. Capture receipts and support official status tracking

- **75.1** Capture the authority, procedure, attempt, reference type and value, event date, observation time, source, verification level, and official tracking URL when available. Support distinct protocol, appointment, payment, and notification reference types as appropriate.
- **75.2** Let users enter a reference or upload a receipt using Phase 6. Present extracted fields for review. Keep user statements and matched document evidence separate, with a distinction between review pending, matched, and mismatch requiring review.
- **75.3** Match the evidence to its authority and submission attempt using only the identifiers the relevant channel supports. If values disagree or a receipt could match multiple attempts, pause the association, show the differing fields, and let the user correct or unlink it.
- **75.4** Open tracking from the reviewed channel record. Include the user-visible reference when useful and permit copy where appropriate. Share reference values with an external site only where that official route documents and permits them. Keep references out of analytics and unnecessary URL parameters.
- **75.5** Record original authority wording and a narrowly mapped display status with the observation timestamp. Make the latest recorded observation, unavailable tracking, and stale observations explicit. Use a manual update when the official channel does not allow programmatic access. A SEND notification reference can help the user find a notice on SEND. Its presence alone leaves application status unchanged.
- **75.6** Implement retry and duplicate handling for receipt uploads and observations. Allow the same external reference in different authority scopes where valid. A payment receipt can satisfy a payment task. Promote a submission or decision state only when the evidence supports that specific event.

**Acceptance.** A user can record a submission reference, see and resolve a mismatch, then reopen the official tracker. Duplicate uploads and payment receipts never invent an application decision.

## 76. Add user-controlled reminders

- **76.1** Let the user set, edit, or remove a reminder from chat or a case action. Capture the reminder date and time, timezone, channel, and owner. Start with in-app reminders. Enable external delivery once a supported channel, consent flow, and delivery checks are in place.
- **76.2** Link the schedule to the case event, task, or exact deadline revision. Make confirmed administrative deadlines eligible for linked reminders. For unknown deadlines, offer a personal reminder to verify the date.
- **76.3** Persist local date and time with the IANA timezone and resolved UTC execution time. Define behavior for skipped or repeated local times and show users the saved schedule. Preserve the local timezone of a real appointment when displaying it.
- **76.4** Deduplicate reminder creation and delivery using the active reminder revision and occurrence key. Recheck that revision and case access immediately before dispatch. Handle bounded retries, stale jobs, and provider errors with visible delivery status where applicable.
- **76.5** Cancel obsolete reminders after a source changes, the task is completed, the setting is turned off, or the case is archived or deleted. If a changed date needs a new decision, ask the user to confirm the replacement schedule. Restoring a case exposes previously cancelled reminders for review.
- **76.6** Use neutral notification content and a signed-in case link. Keep documents, personal identifiers, and official references in the private workspace. Test opt-out, concurrent edits, changed dates, daylight saving, account isolation, and duplicate dispatch.

**Acceptance.** Once a task change or cancellation is committed, processing a queued job for the obsolete reminder revision skips dispatch. A user can create a verified follow-up reminder and see exactly when and how it will appear.

## 77. Prepare appointments and payments on official channels

- **77.1** Add appointment and payment action types linked to a reviewed procedure, authority, official route, and prerequisite state. Show the documents or reference values to have ready, the next action, and any verified instructions relevant to the case.
- **77.2** Record only source-backed fee and payment details with the currency, authority or creditor, and freshness. If the amount or eligibility is ambiguous, direct the user to verify it through the procedure's official channel.
- **77.3** Open the verified booking or payment route from chat. The user completes sign-in, booking, or payment there. Handle authentication or poor availability by offering any reviewed alternative route that is valid for the same procedure.
- **77.4** On return, let users record a confirmed appointment with time, timezone, location, and instructions or attach a payment receipt. Review and match the evidence before marking the task as confirmed. Support changed, cancelled, and unmatched appointments and recordings.
- **77.5** Treat a booking request, a booking confirmation, a payable notice, and completed payment as distinct. An official channel opening only records a handoff. Keep payment instruments and sign-in credentials with the official channel.
- **77.6** Test mobile return, unavailable booking, unsupported channel, wrong-creditor receipt, an unresolved payment, and an authority cancellation. For pagoPA, use the receipt path appropriate to how the user paid.

**Acceptance.** The user can prepare for, leave for, and return from an official booking or payment route. The case history reflects the actual evidence after return, while application submission and payment remain separate milestones.

## 78. Support archiving, restoring, exporting, and deleting a case

- **78.1** Define archive, restore, close, reopen, export, and deletion as distinct actions. Show pending tasks and reminders before closure and require the appropriate confirmation for irreversible actions.
- **78.2** Keep archived cases available to authorised users. Stop active reminders and applicable processing while archived. On restore or reopen, revalidate official links, current rules, deadlines, and dependencies before suggesting actions.
- **78.3** Provide a permission-filtered export of the case summary, task statuses, provenance, approved values, and eligible documents. Let the user preview included data. Generate downloads with short expiry and authenticated access.
- **78.4** Publish the deletion impact for the case, linked cases, and shared documents before confirmation. Revoke access promptly, cancel scheduled work, and queue idempotent cleanup across application data, blobs, OCR derivatives, exports, caches, case indexes, and agent checkpoints.
- **78.5** Preserve another authorised case's independently retained evidence where appropriate. Invalidate deleted or revoked references and create a replacement action for any dependent work. Document the treatment of deletion metadata and backups for Phase 9 review.
- **78.6** Verify cleanup with a completion record that avoids sensitive content. Cover partial failure, safe retries, restore-versus-delete races, in-flight uploads, stale signed links, and removal from search and agent retrieval.

**Acceptance.** Archive and restore recover the selected case with revised next steps where needed. A deleted case is inaccessible through the workspace, agent tools, and download paths. Shared evidence follows its recorded ownership and access rules.

## 79. Define the official integration registry and access model

- **79.1** Record each integration by authority, procedure and jurisdiction, capability, official documentation, authentication and data scope, eligibility evidence, owner, last review, fallback route, and enabled environment. Use verified link-out and manual evidence capture as the default path.
- **79.2** Distinguish public guidance, authenticated citizen portals, and service-to-service APIs. Verify documentation, authority permission, representation of the user, and the intended purpose before exposing any connector. Track progress from candidate to eligible, tested, enabled, and suspended.
- **79.3** Evaluate PDND per e-service. Record the eligible consuming organisation, allowed purpose, approval and credential requirements, permitted fields, and onboarding evidence. Defer a specific connector until eligibility and authorisation for PracticaMIA's use are confirmed.
- **79.4** Define a read-status contract with case-scoped authorisation, explicit provider identity, typed response and timestamp, narrowly defined status mapping, and a manual fallback on denial, rate limits, or outages.
- **79.5** Require server-side authorisation for outbound calls. Use a reviewed channel registry for link and redirect destinations. Keep credentials off the client, out of agent context, and out of logs. Restrict calls and data to the approved capability.
- **79.6** Keep a disable control per connector and test with mocks or approved sandbox credentials. Run tests for expired access, malformed results, retry limits, wrong-case data, and fallback. A suspended connector must leave manual tracking usable.

**Acceptance.** Every enabled channel has a verified owner and capability, a current review record, and a usable failure path. A procedure with no enabled API still supports official link-out and reviewed receipt capture.

## 80. Validate a multi-authority case from start to finish

- **80.1** Define one representative pilot life event with two independently verified procedures owned by different authorities. Specify the actor, locale, expected authority, dependencies, evidence types, success criteria, and which observations the agent can present.
- **80.2** Create synthetic fixtures for a reusable reviewed attachment, one unavailable prerequisite, a conditional task, an unmatched receipt, a later matched receipt, and a source change. Keep the E2E suite independent of live submissions, payments, and bookings.
- **80.3** Start the case in chat, prepare one action, share a permitted evidence revision across the two cases, and resume after reload. Verify that verified urgency and real prerequisites determine priority and that separate actionable work remains reachable.
- **80.4** Record a user submission report, resolve the receipt mismatch, record the official observation it actually supports, and open the authority tracker. Add or update a reminder using an evidenced date, then exercise a revised or cancelled date and check for stale delivery.
- **80.5** Complete and close the workspace case with one task still awaiting an authority update. Show the pending item at closure, reopen it with a later notice, and verify corrections affect only the dependent task. Test cross-account isolation of timeline, exports, and evidence.
- **80.6** Score incorrect status promotions, incorrect authorities, unsupported deadline dates, missed dependency invalidations, duplicate reminders, and users identifying the correct next action without assistance. Require zero unsupported status promotions and zero cross-account disclosures in the Phase 8 acceptance suite. Set the other pilot targets before running it.
- **80.7** Hand cases, events, deadline and reminder contracts, integration inventory, deletion coverage, and the cross-authority regression suite to Phase 9. Record the scope of tested procedures and any feature flags or manual fallbacks.

**Acceptance.** Both procedures remain individually traceable and task priorities survive reload, corrections, partial completion, closure, and reopening. The user sees where each procedure stands and what they can do next without any invented authority outcome.

## Implementation order

| Slice | Tasks | Expected result |
| --- | --- | --- |
| Resumable case | 71–73 | Persisted progress, dependencies, timeline, and next action in chat |
| Tracking and reminders | 74–76 | Verifiable dates, matched receipts, and cancellable follow-ups |
| Official follow-up and case lifecycle | 77–79 | Booking and payment preparation, lifecycle actions, and reviewed integration registry |
| Cross-authority validation | 80 | Reproducible end-to-end case and handoff package for Phase 9 |

**Closure demonstration.** The user returns to a life event with two authority-specific cases. They report completing a submission, attach its receipt, and resolve a reference mismatch. The first case shows receipt recorded, with the authority's decision still pending. The second case shows a blocker and the next available action. A corrected notice updates the relevant due date and cancels the superseded reminder. The user closes the workspace case and later reopens it when the authority sends an update, with the earlier evidence and corrections still visible.

## Official channel references

- [Dati e interoperabilità — Department for Digital Transformation](https://innovazione.gov.it/progetti/dati-e-interoperabilita/)
- [Opening a notice or communication on SEND — official SEND support](https://assistenza.notifichedigitali.it/hc/it/articles/52068038598801-Come-aprire-una-notifica-SEND-o-una-comunicazione-sulla-piattaforma-SEND)
- [Finding a payment receipt — official pagoPA support](https://assistenza.pagopa.gov.it/hc/it/articles/32186752927761-Dove-trovare-la-ricevuta-di-un-pagamento)
