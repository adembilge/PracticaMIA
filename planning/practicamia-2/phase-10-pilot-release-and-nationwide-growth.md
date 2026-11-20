# PracticaMIA 2.0 — Phase 10 · Pilot, release, and nationwide growth

**Roadmap tasks 91–100.** Measure whether people using PracticaMIA reach the correct official next step, release the supported workflows in controlled stages, and extend coverage across Italy as each new procedure and jurisdiction is verified. Keep the single specialist agent and **one user-facing chatbot interface** throughout rollout; document and form review, checklists, case tracking and recovery remain inline. Do not introduce a separate customer-facing Preview application or specialist feature screens as coverage grows.

**Dependencies.** Phase 2 supplies the participant and case matrix, capability contracts, comparison method, and primary outcome. Phase 3 supplies the official source catalog, jurisdiction rules, and review and withdrawal workflow. Phases 4–8 supply the supported end-to-end case paths. Phase 9 supplies the verified candidate scope, privacy assessments, test evidence, operational safeguards, and go, limited go, or hold decision. Changes to those inputs require the affected checks to be rerun.

**First vertical slice.** Rehearse one verified procedure end to end on the exact release candidate with synthetic data and two accounts. Start observed participant sessions only after the applicable Phase 9 gates and support checks pass. Count rehearsal and participant results separately. The first release can cover a smaller surface than the full Phase 2 research matrix if the decision record describes the missing coverage and its effect on release scope.

## 91. Define the pilot scope and decision rules

- **91.1** Turn the Phase 9 decision and Phase 2 capability contracts into a pilot matrix. Record each procedure, jurisdiction, authority, channel, language, enabled capability, approved evidence, fallback, and assigned owner.
- **91.2** Select cases spanning national guidance, locally implemented work, and cross-authority follow-up. Plan Phase 2's coverage across at least three authorities and multiple regions. Record which cells are eligible for real sessions, which still need research, and how any gap limits release.
- **91.3** Define the expected next action and accepted alternatives for each case. Have a reviewer confirm current official evidence before each pilot round. Define the observable finish point, such as identifying the correct office, reviewing a missing attachment, or opening the verified route.
- **91.4** Set targets before participant sessions. Use unassisted arrival at the correct next step as the primary outcome. Fix the planned participant and case counts, observation window, permitted help, comparison method, and minimum evidence for each scope decision.
- **91.5** Define pause triggers for critical guidance errors, suspected disclosures, missing evidence, unsupported status claims, and an unavailable fallback. Assign the person who can pause the affected scope and the person who approves resumption.
- **91.6** Create the pilot decision record with status, candidate version, eligible scope, participant objectives, owners, key dates, and open checks. Restrict sign-up and invitations to the approved pilot scope.

**Acceptance.** The pilot team can point to an approved plan for who may participate, which workflows they may use, how success is measured, and which conditions pause a session or release.

## 92. Verify the release candidate in a production-like environment

- **92.1** Record the exact app, database schema, agent configuration, model, source and rule snapshots, feature flags, and provider settings. Publish candidate identity in a support-accessible location.
- **92.2** Verify the release path against the intended hosting configuration. Check authentication, private storage, background work, uploads and OCR, form preparation, official link-outs, persistence across reload, and case deletion through the browser and backend.
- **92.3** Check the candidate with two synthetic accounts for permitted own-case reads and updates and denied cross-account actions. Exercise evidence reuse, receipt review, exports, and an interrupted upload followed by a retry.
- **92.4** Verify mobile and desktop completion. Open a prepared output where supported, return after leaving for an official route, and resume a saved case. Include a keyboard-only path and the supported pilot languages.
- **92.5** Validate environment separation, supported operator access, alerts, case data handling, feature controls, and the support contact path. Use permitted test accounts and synthetic documents for the rehearsal. Confirm that the environment follows the approved data policy before any real data is accepted.
- **92.6** Write an evidence-backed readiness note. Resolve or explicitly bound environment-specific issues. Recheck the affected routes after code, configuration, provider, schema, prompt, or source changes.

**Acceptance.** The candidate and configuration tested in rehearsal can be identified and reproduced. The stated primary workflow, safe fallback, and account isolation are verified end to end.

## 93. Prepare recruitment and session materials

- **93.1** Recruit against the pilot matrix. Include people with the relevant administrative need, a spread of prior experience, and the device and language conditions to be assessed. Mark where recruitment leaves a scope gap.
- **93.2** Prepare invitations, participant information, and any required consent or acknowledgement for research participation, recording, or optional follow-up. Explain the purpose, observation method, data handling, withdrawal route, and support contact.
- **93.3** Give participants a short task brief that does not reveal the expected answer. Use one canonical scenario record for the moderator and specify when the participant can use an approved synthetic example or eligible personal material.
- **93.4** Define what observers may record and where it is stored. Use participant codes and minimal notes. Keep private case material out of shared tickets and reports. Use actual documents only within the previously reviewed pilot conditions.
- **93.5** Standardise the comparison with the user's existing approach. Use comparable cases and account for prior experience, task order, and moderator assistance. Record cases where a comparison is unavailable or unsuitable.
- **93.6** Rehearse one moderated session with a colleague, including the stop procedure, escalation path, and accessibility accommodations. Verify that participants can resume or withdraw without losing access to the support information they need.

**Acceptance.** Another moderator can run the same scenario and record outcomes consistently. Participant materials are understandable, recruitment matches the intended scope, and research records follow the approved handling rules.

## 94. Run the limited pilot with real participants

- **94.1** Invite the initial cohort within the approved scope and observation window. Record candidate, scenario, participant code, device, language, starting context, and guidance offered.
- **94.2** Observe whether the participant identifies the competent authority and explains the next official step in their own words. Track time, detours, misrouting, moderator interventions, corrections, and successful return to an ongoing case.
- **94.3** Score unassisted and assisted attempts separately. Report correct, incomplete, incorrect, and not assessed outcomes. Record where a permitted official handoff was reached or where an external condition prevented observation.
- **94.4** Capture product behavior and participant feedback as distinct evidence. Preserve the source and case event behind any disputed answer or status. Record a real submission or authority decision only when the available evidence supports it under Phase 8.
- **94.5** Pause the affected scope when a stop trigger is met. Preserve minimal incident evidence, route it to the assigned owner, and help the participant recover through the reviewed route where available.
- **94.6** Report the number of participants, cases, attempts, supported scope cells, withdrawals, and missing observations. Count a synthetic run as a rehearsal. Give participants the agreed follow-up and data-control instructions.

**Acceptance.** The pilot report contains observed real-participant outcomes, scope and denominators, evidence of assisted versus unassisted completion, and documented handling of every stop event. An unobserved scope cell stays unvalidated.

## 95. Triage findings and approve the release scope

- **95.1** Convert findings into reproducible issues. Record severity, affected procedure and jurisdiction, candidate and source versions, observed outcome, expected outcome, privacy-safe evidence, and an owner.
- **95.2** Group findings by likely source, rule, model, tool, document processing, UI, accessibility, environment, or research cause. Review administrative accuracy with the procedure owner and verify each fix at the layer that caused it.
- **95.3** Rerun affected automated gates and comparable participant tasks where the fix changes the observed user experience. Use a new comparable scenario when prior exposure would reveal the answer. Track corrected results alongside the original evidence.
- **95.4** Compare the actual results with prespecified targets and the Phase 2 comparison baseline. Report small samples and inconclusive cells explicitly. Include duration, support load, and cost where observed alongside primary completion.
- **95.5** Require resolution or exclusion from scope for each release-blocking item. Record accepted lower-severity limitations and their mitigations. Verify the fallback still works for any capability excluded from the release.
- **95.6** Publish a go, limited go, or hold record for the exact release candidate and scope. Include reviewed evidence, the person approving, enabled capabilities, excluded cases, unresolved questions, and a review date.

**Acceptance.** The release decision can be reproduced from participant evidence and Phase 9 checks. A workflow with unresolved critical findings or insufficient mandatory evidence remains unavailable in the approved scope.

## 96. Roll out the approved release in controlled stages

- **96.1** Define release stages for internal access, the approved limited cohort, and broader access within verified coverage. Specify access conditions, observation periods, promotion evidence, owners, and stop thresholds for each stage.
- **96.2** Align database and background changes with the release sequence. Validate migrations, compatibility with the previous release, and queued job behavior. Where rollback is unsafe after a data change, approve a documented recovery or forward-fix path before opening access.
- **96.3** Prepare launch copy, help content, and visible coverage details. Describe supported procedures and current capabilities with correct authority and jurisdiction, and show users the supported next step when their case falls outside coverage.
- **96.4** Require the recorded scope approval from Task 95 and tested operational readiness from Task 97 before a production promotion. Verify deployed revision and configured flags for the target stage.
- **96.5** Run post-deploy smoke checks for a supported workflow, an unsupported jurisdiction, login and resume, official link-outs, and case isolation. Use synthetic data for smoke tests. Compare candidate and deployed evidence before enabling wider access.
- **96.6** Keep a promotion log with revision, time, scope, observed indicators, open issues, and the stop or rollback decision if reached. Promote a later stage only after the specified observation window and checks pass.

**Acceptance.** The running release matches the approved revision and scope. Users can identify availability and resume their work, and operators can pause the affected stage from a tested control.

## 97. Prepare support, incident response, and rollback for release

- **97.1** Assign release and support owners, escalation contacts, and an observation schedule. Monitor task success, administrative errors, source freshness, provider health, case isolation signals, and support backlog.
- **97.2** Link operational alerts to the corresponding source, tool, or feature owner and Phase 9 runbook. Verify alert delivery, access to diagnostics, and minimum data capture for support cases.
- **97.3** Rehearse disabling one procedure, source version, channel, model-dependent step, or upload capability. Check the chat fallback and its effect on already-open cases, reminders, and queued jobs.
- **97.4** Rehearse the preferred rollback or forward-fix with compatible schema and data handling in a production-like environment. Verify that the recovery still respects permission changes, deleted cases, and time-sensitive corrections.
- **97.5** Define communication and correction steps for affected users through the approved channels. Include when to recheck a recommendation or a deadline, who owns the message, and how to avoid sharing private case details.
- **97.6** Check post-recovery evidence before resuming. Record the known-good version, checks run, lingering work, and person authorised to resume. Keep the release guardrails active throughout the observation window.

**Acceptance.** A rehearsal demonstrates that the responsible operator can identify, contain, communicate, and recover from a release problem. The product state and case evidence remain usable for unaffected workflows.

## 98. Standardise onboarding of procedures and jurisdictions

- **98.1** Create a repeatable onboarding template for a procedure and jurisdiction. Capture authority, source evidence, effective dates, eligibility inputs, official route, language, supporting documents, and capability levels.
- **98.2** Reuse reviewed national requirements with explicit local variants where applicable. Record which claims are inherited, overridden, or unresolved in each jurisdiction. Require evidence for every local override and route.
- **98.3** Verify applicability rules, form revisions, channel outcomes, dates, and fallback before enabling the procedure. For unavailable capabilities, provide the reviewed official route or the next useful sourced step.
- **98.4** Validate fixture completeness and run focused tests for the new authority and near-neighbor authorities. Include missing location, changed location, stale sources, conflicting information, and any previously supported related workflow.
- **98.5** Assign a source reviewer and support owner. Record review cadence, trigger conditions for rechecking, withdrawal process, and how relevant updates reach existing cases.
- **98.6** Produce a coverage manifest that powers release flags, reviewed-source details opened within chat, user-facing support indicators, and expansion reporting. Keep the registry keyed by procedure, jurisdiction, channel, and capability revision.

**Acceptance.** A new locality can be added using reviewed sources, rules, and tests while retaining one agent and one chat. Evidence from nearby jurisdictions stays correctly scoped.

## 99. Expand in waves using verified coverage and observed demand

- **99.1** Rank candidate waves using observed demand, user impact, gap frequency, source quality, local variation, maintenance effort, and support capacity. Record the criteria and evidence behind the next wave.
- **99.2** Choose a limited set of additional procedures or jurisdictions and map how the wave affects existing national and local guidance. Add explicit acceptance cases for mixed jurisdictions and cross-authority dependencies.
- **99.3** Complete Task 98 onboarding and the applicable Phase 9 gates for the wave. Verify current sources and fallbacks, then rehearse changes using the tested release workflow.
- **99.4** Release the wave to the intended scope and record actual completion, misrouting, unsupported requests, stale sources, and support load during the observation period. Compare results by jurisdiction and capability with prior validated scope.
- **99.5** Review the wave with its owners. Expand, hold, narrow, or withdraw scope using the recorded thresholds and evidence. Rerun dependent tests if an official source or jurisdiction boundary changes.
- **99.6** Publish coverage by verified procedure and location. Report national and local footprint with explicit denominators and capabilities. Keep unverified or withdrawn areas discoverable through safe fallbacks where official guidance is available.

**Acceptance.** One additional verified scope can be enabled, monitored, and withdrawn with auditable evidence. Existing users retain valid guidance, and the product's coverage claims match the current manifest.

## 100. Close the roadmap and hand over ongoing operations

- **100.1** Reconcile all 100 task IDs against deliverables and verification evidence. Distinguish planned, implemented, tested, pilot-approved, and released status. Leave open work visible with owners and next review dates.
- **100.2** Assemble the evidence pack with tested candidate versions, participant summary, release decision, current scope, privacy and quality approvals, incidents and fixes, and active operating procedures.
- **100.3** Verify ownership and review cadence for source freshness, procedure updates, participant feedback, quality regressions, privacy requests, access reviews, and incident response. Confirm that replacement operators can find the relevant procedures and contacts.
- **100.4** Create the post-release backlog from actual participant findings, unsupported but recurring requests, source maintenance issues, and operating metrics. Rank items with rationale and ties to verified user need.
- **100.5** Record the next expansion wave or the conditions that need to be met first. State whether the operating decision is continued pilot, broader release within verified scope, or hold.
- **100.6** Close the phase with a review of release evidence, current coverage, ownership, and follow-up. If a release or wave remains on hold, retain the work as open and record the concrete evidence still needed.

**Acceptance.** The team can distinguish the completed roadmap plan from verified implementation and actual release status. Operators have a current list of supported workflows, known limitations, open work, and the next operating decision.

## Implementation order

| Slice | Tasks | Expected result |
| --- | --- | --- |
| Define and rehearse the pilot | 91–93 | Approved scope and measurement protocol, tested candidate, and ready participant materials |
| Observe users and decide scope | 94–95 | Real-participant results, verified fixes, and a recorded scope decision |
| Prepare operations and release | 97, then 96 | A tested support and recovery path before staged production promotion |
| Broaden verified coverage and hand over | 98–100 | Repeatable onboarding, measured expansion waves, and ongoing ownership |

**Closure demonstration.** Two synthetic accounts verify release-candidate isolation and workflow recovery. A real participant reaches a verified official next step, with their result recorded separately from rehearsal. The team fixes and retests a material finding, records the approved release scope, and rehearses disabling one affected workflow before staged promotion. A separately verified jurisdiction is added as its own wave and appears in the coverage manifest, with source reviews, tests, and operational ownership attached.
