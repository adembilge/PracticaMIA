# PracticaMIA 2.0 — Phase 9 · Privacy, security, and quality evaluation

**Roadmap tasks 81–90.** Establish the privacy controls, security boundaries, and evaluation evidence needed to decide whether a specific procedure is ready for a limited pilot. Verify the whole journey through **one customer-facing chat route**, from free-text questions and inline document review through official handoff and later case tracking. No separate feature or Preview UI may be necessary to complete the in-app steps.

**Dependencies.** Phase 2 supplies pilot scope, completion outcomes, and the comparison baseline. Phase 3 supplies reviewed authority and source versions. Phases 4–5 supply the specialist agent, tool contracts, and UI. Phases 6–7 supply upload trust states, evidence review, approved fields, and handoff events. Phase 8 supplies status, dependencies, deadlines, reminders, integrations, and the case lifecycle. Tie acceptance evidence to exact versions of these inputs.

**First vertical slice.** Pick one verified pilot workflow. Run it in a production-like environment with two synthetic accounts and reviewed, synthetic documents. Follow the data through upload, OCR, agent retrieval, form preparation, external handoff, receipt review, and deletion. Run the isolation and evidence checks before expanding the workflow or enabling real uploads.

## 81. Inventory data and map processing boundaries

- **81.1** Trace chat messages, identity and account data, case facts, uploads, OCR output, approved fields, exports, receipt references, case events, preferences, and reminders from collection through deletion. For each item, record purpose, source, owner, recipients, location, and retention trigger.
- **81.2** Include less visible copies in the inventory. Review task queues, temporary processing storage, agent checkpoints, embeddings, caches, analytics, support tooling, logs, provider telemetry, backups, and locally downloaded artifacts. Record which copies share the case lifecycle.
- **81.3** Identify optional and sensitive fields for each pilot procedure. Define when the workflow can proceed with an extract, masked value, user confirmation, or a link to an official service. Define the minimum input required for each action.
- **81.4** Classify trust boundaries across the browser, API, case store, private storage, OCR workers, model provider, source updates, notification delivery, and any official connector. Assign owners and specify authorised ingress and egress at each boundary.
- **81.5** Keep the reviewed public source catalog and private case evidence in separate access domains. Define which case-scoped payloads go to a processor, which remain application-side, and what happens when a provider or workflow changes.
- **81.6** Review the inventory against one instrumented synthetic case. Resolve missing stores and undocumented transfers. Add a change checklist for new fields, tools, vendors, or environments.

**Acceptance.** A reviewer can trace a synthetic upload and each derivative to its authorised use, storage location, and disposal path. Every external transfer has a documented purpose and owner.

## 82. Review privacy obligations and user-facing disclosures

- **82.1** Assign accountable owners for the processing inventory, access requests, incident triage, and provider review. Record controller and processor roles per activity and the lawful basis being relied on where applicable. Review the treatment of special-category data if a procedure may expose it.
- **82.2** Review GDPR purpose limitation, minimisation, storage limitation, and protection by design against the real data flow. Document the relevant user rights, applicable exceptions, operating responsibilities, and response process. Have a qualified reviewer resolve open legal questions before enabling affected pilot features.
- **82.3** Screen for a data protection impact assessment using the processing scope and the Italian Garante's criteria. Record the conclusion and reasoning. Where required, complete the DPIA, track mitigations and residual risks, and follow any applicable consultation process before enabling the affected processing.
- **82.4** Review infrastructure, model, OCR, analytics, and delivery providers for data scope, processing agreements, regions, subprocessors, retention, model-training terms, deletion support, and applicable transfer safeguards. Bind approved provider settings to each environment.
- **82.5** Write clear notices where data is collected. Explain who operates the workspace, how it uses submitted data, when sharing occurs, how to exercise applicable rights, and how users reach the official channel. Use concise, accessible wording at the point of upload, export, and reminder setup.
- **82.6** Identify the AI assistant in the chat and review applicable AI Act role, classification, transparency, and timing for the intended deployment. Phase 7 handoff remains under user control. Keep applicable assessments, notices, provider evidence, and review decisions versioned.

**Acceptance.** The pilot's chosen data flows and deployment have documented privacy decisions and matching interface copy. Any unresolved assessment, provider transfer, or processing purpose has a named owner and a clear impact on pilot scope.

## 83. Enforce identity, authorisation, and account isolation

- **83.1** Define allowed operations for each actual principal, including case owner, explicitly authorised recipient if sharing is enabled, worker, source reviewer, and operator. Separate review of public procedures from access to personal documents.
- **83.2** Enforce case, account, and operation scope in the backend at each entry point. Cover chat tools, API routes, background jobs, database queries, object reads, search results, exports, and connector callbacks. Derive identity from trusted session or job context.
- **83.3** Apply least privilege to storage and service credentials. Isolate development, test, and production resources. Require encryption in transit and at rest, scoped service identities, key and secret rotation, and revocation checks appropriate to the deployed components.
- **83.4** Verify object ownership before issuing a short-lived download grant. Recheck permission during document reuse and after a shared reference is revoked. Document the lifetime of previously issued links and the design for enforcing revocation before that expiry where immediate access removal is promised.
- **83.5** Constrain operator access to an explicit support or incident purpose and record who accessed what and why. Keep private data out of deployment previews, pull-request fixtures, public source indexes, and broad support views.
- **83.6** Add a two-account regression matrix for normal reads and writes, expired sessions, revoked sharing, case exports, OCR results, search, agent memory, and queued work. Verify both denial for an unrelated account and valid access for each authorised account.

**Acceptance.** Two separate test accounts can complete their own cases and cannot access each other's data through UI, agent, API, document, retrieval, or background paths. Revoked access is enforced within the documented grant model.

## 84. Protect uploads, retrieval, and agent tools

- **84.1** Carry Phase 6 upload trust states into every downstream consumer. Keep files private and isolated until their type, size, and trust checks pass. Keep a blocked or unavailable scan visible to the user and retry through the defined review flow.
- **84.2** Process supported attachments in workers with resource and time limits, restricted access, patched parsers, and explicit permitted outputs. Use approved synthetic fixtures to verify corrupt-file, scanner outage, OCR timeout, and processing limit behavior. Avoid leaking contents through errors.
- **84.3** Treat documents, OCR content, and fetched passages as untrusted input to the agent. Preserve source boundaries and provenance, constrain retrieval to required case data and reviewed sources, and verify that embedded instructions cannot change tool permissions, destinations, or approval requirements.
- **84.4** Keep write-capable tools schema-validated and server-authorised. Bind user confirmation to the exact action, relevant resource, and revision. Handle replay, changes after approval, and interrupted executions with the same checks at mutation time.
- **84.5** Limit outgoing data and route requests through configured destinations. Keep official credentials and payment instruments in their official channels. Exercise cases with unapproved links and unauthorised action requests using mocked destinations and harmless fixtures.
- **84.6** Define privacy-preserving events for blocked or degraded paths. Establish dependency checks, patch ownership, rollback procedures or feature controls, and a safe way to disable a processor, connector, or tool while a finding is investigated.

**Acceptance.** Untrusted input cannot grant access, bypass an approval, or redirect an authorised action. A blocked upload preserves the user's ability to recover from the same case without exposing its content to downstream services.

## 85. Verify retention, user rights, and deletion

- **85.1** Define a retention schedule by data class and purpose with a start event, owner, expiry behavior, and documented exceptions. Design separate rules for archive, account closure, case deletion, published source material, and processor-held copies.
- **85.2** Make applicable access, correction, export, and deletion requests discoverable. Validate the requester's identity and authority when appropriate. Route exceptions and requests involving other people's data to a documented review process.
- **85.3** Test Phase 8 deletion end to end. Revoke access, stop pending work, and remove applicable data from objects, OCR derivatives, exports, agent state, caches, search indexes, notifications, and service providers. Verify retry behavior and record completion without retaining contents unnecessarily.
- **85.4** Define how authorised shared evidence and legal retention exceptions affect deletion. Document what remains, why it remains, who can access it, and when to review it. Recompute affected dependencies and invalidate stale links after a reference is withdrawn.
- **85.5** Document backup retention, restricted restoration, and how restorations reapply deletion records before user or agent access resumes. Test a restore using synthetic data and record the checks performed on derivatives and stale references.
- **85.6** Exercise user-visible status through a partially failed deletion and a recovered retry. Verify in-chat case history, agent retrieval, cards and downloads agree. Escalate overdue or incomplete deletion to the named owner.

**Acceptance.** An authorised user can request export or deletion, see progress, and receive the appropriate result. The restored environment respects recorded deletions, and remaining copies or exceptions are bounded by the documented policy.

## 86. Build versioned evaluation datasets and reproducible runs

- **86.1** Create a manifest of supported procedures, authorities, jurisdictions, relevant languages, channels, and difficulty levels. Cover typical questions, missing facts, valid exceptions, outdated sources, near-match authority names, and explicitly unsupported requests.
- **86.2** Create synthetic documents and case timelines with reviewed source passages, expected decisions, acceptable variants, and reasoning notes. Use public authority material where permitted. Keep personal pilot data out of shared fixtures and fall back to approved controlled access when a real assessment requires it.
- **86.3** Separate development, repeatable regression, and restricted holdout sets. De-duplicate closely related cases across splits. Give each item an ID, owner, source version, expected result, severity, and last review date.
- **86.4** Use deterministic checks for exact structured fields, dates, approvals, state transitions, and access policy. Have reviewers label ambiguous guidance and administrative scope. Use model-assisted grading for triage or as a calibrated signal and adjudicate release-critical cases with reviewers.
- **86.5** Record the model and settings, prompt and tool versions, retrieval snapshot, source and rule versions, dataset revision, backend revision, and test environment. Keep per-run denominators, errors, incomplete results, latency, and cost.
- **86.6** Establish small pull-request checks, a versioned full benchmark, and a restricted holdout run for the pilot candidate. Require explicit deltas for changed sources or expected behavior. Turn confirmed regressions into minimal, reviewed fixtures.

**Acceptance.** A reviewer can rerun a benchmark with the same manifest, inspect why each case passed or failed, and compare revisions without changing the hidden holdout to fit an expected score.

## 87. Evaluate administrative accuracy and source grounding

- **87.1** Evaluate whether the answer selects the correct procedure, authority, jurisdiction, channel, and applicable prerequisites. Include different municipalities and national rules where supported. Record whether genuinely ambiguous inputs lead to an appropriate clarifying question.
- **87.2** Score citation correctness at claim level. Verify each consequential claim against the referenced passage, its issuer, jurisdiction, active date, and scope. Track missing citations and sources that are current but fail to support the claim.
- **87.3** Evaluate time-sensitive guidance, conflicts, superseded sources, and unavailable trackers. Check that the answer surfaces uncertainty with a verified next action and distinguishes case facts, user reports, third-party evidence, and authority observations.
- **87.4** Test unsupported procedures, incorrect jurisdiction assumptions, absent required information, language mismatch, and attempts to obtain an official outcome. Compare how often the agent defers safely with how often it needlessly defers supported cases.
- **87.5** Score answers with a rubric for authority and route correctness, evidence support, completeness of the next action, and communication of uncertainty. Report results by procedure and jurisdiction so a strong aggregate cannot conceal a release-critical failure.
- **87.6** Review critical findings with the procedure owner. Fix the underlying source, rule, retrieval, or presentation issue, then rerun the affected slice and the cross-procedure regression suite. Compare completion with the Phase 2 baseline where meaningful.

**Acceptance.** In the reviewed candidate suite, each release-critical recommendation is supported by applicable official evidence or the workflow produces an actionable deferral. The report shows which procedures and jurisdictions were exercised.

## 88. Evaluate document, form, and case workflow quality

- **88.1** Score OCR and extraction by field and document quality, including Italian names, dates, identifiers, and multi-page notices. Measure exact match for critical fields, how often missing or conflicting data is flagged, and whether the user can reach the supporting page for review.
- **88.2** Verify tasks from reviewed evidence to form mapping, corrections, regenerated output, and Phase 7 handoff. Exercise a replaced form, a pending critical field, an invalidated approval, and one portal-only workflow.
- **88.3** Exercise progress after handoff. Check receipt matching, preservation of earlier attempts, accurate status labels, deadline provenance, reminder rescheduling, and two linked procedures that can progress independently.
- **88.4** Test interruptions, provider timeouts, retries, concurrent case edits, and paused sessions. Verify the user can complete all available in-app steps and recover on the **same chatbot route** with inline controls only. Check supported languages, mobile and keyboard paths; reject cross-screen dependencies.
- **88.5** Measure workflow success, next-action identification, correction effort, time to complete, median and tail latency, and cost per completed eligible workflow. Report failures and timeouts alongside performance and note any sample sizes too small for a reliable comparison.
- **88.6** Confirm reviewers can reproduce every critical discrepancy from the collected run evidence. Keep download preview test data synthetic. Retest every fix across case state, access control, and approval behavior.

**Acceptance.** A reviewed end-to-end workflow has correct approved fields, a traceable handoff, and accurately reported follow-up across reloads. Critical mismatches become visible review items with a path to recover.

## 89. Instrument the system and rehearse incident response

- **89.1** Define structured metrics and logs for authorisation denials, source freshness, queue health, scan failures, model/OCR timeouts, duplicate suppression, deletions, and agent tool decisions. Redact sensitive values and allowlist what can reach analytics and operational logs.
- **89.2** Track signals by environment and capability with privacy-preserving correlation IDs, controlled retention, and restricted access. Define planned alert thresholds, owners, severity, and operating hours. Test that alerts reach the assigned responders.
- **89.3** Write a response runbook for a suspected privacy incident, incorrect procedure guidance, unsafe data processing, or integration failure. Record first actions, evidence preservation, scope assessment, escalation, containment, and user correction.
- **89.4** Identify which capabilities can be disabled independently, such as new uploads, an OCR provider, a stale procedure, a source publisher, or an official connector. Document the user experience and recovery verification for each shutdown.
- **89.5** Rehearse a privacy incident with synthetic data, including documenting when it was detected and when the controller became aware, and assess the applicable regulator or user notification steps with the accountable owner. Include an administrative guidance incident with correction of the affected rule and case actions.
- **89.6** Check recovery before re-enabling a capability. Confirm relevant queues, data cleanup, model or source revisions, case-state accuracy, and user-visible communication. Record the drill outcome and assign fixes with deadlines.

**Acceptance.** A drill demonstrates a complete path from signal to escalation, containment, verification, and recovery. Logs support diagnosis without storing raw private documents, full prompts, or credentials.

## 90. Define release gates and prepare the Phase 10 handoff

- **90.1** Define a gate matrix by procedure, jurisdiction, channel, and capability. Require evidence for privacy review, approved sources, access isolation, administrative accuracy, document quality where applicable, lifecycle correctness, and operational recovery.
- **90.2** Approve metric definitions, sample sizes, and targets before evaluating the release candidate. Include zero observed critical failures in mandatory suites for cross-account disclosure, unsupported submission or authority outcomes, bypassed user approval, and unsupported critical deadlines or eligibility guidance.
- **90.3** Record severity, evidence, and owner for each finding. Block the affected capability or scope for a critical failure or missing mandatory evidence. Use documented scope controls and visible manual fallbacks where an unaffected procedure can still progress.
- **90.4** Run the tests against the exact pilot candidate in the intended configuration. Record app, schema, policy, prompt, model, and source revisions, environment and provider controls, test outcomes, and supporting evidence. Re-run the relevant gates after changes to those inputs.
- **90.5** Produce a go, limited go, or hold decision with the confirmed scope, mitigations, known limitations, rollback actions, and reviewers' approvals. Specify the evidence needed to add another locality, provider, or higher-risk capability.
- **90.6** Give Phase 10 the pilot candidate report, reviewed scope matrix, benchmark and holdout summary, privacy assessment evidence and open items, incident runbooks, feature controls, and monitoring owners. Keep private evaluation and incident evidence in the appropriate restricted location.
- **90.7** Run one final release rehearsal from beginning to end. Include two-account isolation, unsupported case deferral, an official source update, an upload degradation scenario, post-handoff authority status, and verified deletion. Record the exact checks completed.

**Acceptance.** The Phase 10 pilot owner can identify what is eligible to ship, reproduce the approval evidence, and disable an affected capability. A procedure with a critical failure or an unmet mandatory gate remains unavailable for the pilot.

## Implementation order

| Slice | Tasks | Expected result |
| --- | --- | --- |
| Inventory and privacy review | 81–82 | Versioned data map, provider inventory, assessments, and matching user disclosures |
| Enforce critical controls | 83–85 | Verified isolation, upload and agent boundaries, and end-to-end data lifecycle |
| Build and run independent evaluations | 86–88 | Repeatable procedure, document, and workflow evidence at release-candidate scope |
| Rehearse operations and approve scope | 89–90 | Incident and rollback drill, gate decision, and Phase 10 handoff |

**Closure demonstration.** Two synthetic users work on separate cases. One uploads a notice and receives advice grounded in the correct authority and date. A changed source triggers review of the affected deadline. The submission receipt updates the timeline while the authority's decision is pending. The other user cannot retrieve the case from the UI, agent, search, or export. Deleting the case removes access to its artifacts and derivatives, including after the restore drill. The team records the pilot decision against the tested revision.

## Primary references for the privacy review

- [General Data Protection Regulation — EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng)
- [Italian Garante's list of processing operations subject to a data protection impact assessment](https://www.garanteprivacy.it/home/docweb/-/docweb-display/docweb/9058979)
- [Artificial Intelligence Act — EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng)
