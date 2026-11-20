# PracticaMIA 2.0 — Phase 7 · Requirements, form preparation, and official handoff

**Roadmap tasks 61–70.** Help a user turn a verified requirement list and reviewed case evidence into an application they can prepare for the correct official channel. The user should be able to answer four questions from the chat workspace: what is required, what is missing, what goes in each field, and where to continue officially.

**Dependencies.** Phase 2 supplies the pilot procedures and their expected user outcomes. Phase 3 supplies competent authorities, applicable requirements, versioned forms, and official passages. Phase 4 supplies case state, authorised tools, and user approval. Phase 5 supplies inline checklist, action, and form cards in the single chat UI; no separate form editor or application review page exists. Phase 6 supplies confirmed fields, unresolved values, documents, and provenance. Phase 8 will use the handoff record for receipt-based tracking.

**First vertical slice.** Choose one procedure for which the authority, requirements, and current form or portal channel have been verified. Use the portal preparation path as the initial output wherever that is how the service operates. Enable a filled PDF draft for a separately verified compatible official template. Test one conditional requirement, one unresolved field, and one intentional form-version change.

**Separation of state.** Checklist readiness describes preparation. User-reported submission, receipt evidence, and authority-confirmed outcomes belong to case tracking. Opening a channel, generating a draft, or exporting field values is recorded as a preparation action.

## 61. Model requirement rules and their applicability

- **61.1** Define a requirement identity and version. Record the procedure, competent authority, jurisdiction, applicable channel, validity interval, reviewed source passage, and approval state.
- **61.2** Represent applicability as typed conditions over approved case facts. Include unconditional, conditional, and mutually exclusive requirements. Capture when a condition depends on the applicant, place, date, or application route.
- **61.3** Distinguish required documents, acceptable alternatives, informational recommendations, prerequisites, and authority-specific exceptions. For an either-or requirement, record its group so that supplying one accepted option can satisfy it.
- **61.4** Return explicit rule outcomes for applies, does not apply, insufficient information, and needs review. Missing input must remain visible. A failed lookup or an absent value cannot turn into a negative eligibility decision.
- **61.5** Use reviewed rules for requirement decisions. Where official sources conflict or an effective date is unresolved, flag the affected rule for review and expose the next verified step available to the user.
- **61.6** Expose a read-only evaluation result to the Phase 4 agent with requirement IDs, outcomes, missing facts, and evidence IDs. Keep model-generated explanations linked to the evaluated result.
- **61.7** Build fixtures for missing location, boundary dates, alternative attachments, stale rules, two local variants, and a conflict that requires review.

**Acceptance.** Given the same case facts and rule versions, evaluation produces the same result. Every item that applies can be traced to a reviewed source and an explicit applicability decision.

## 62. Build the personalised readiness checklist

- **62.1** Merge the rule result with Phase 6 document evidence and the current case revision. Bind the evaluation to the exact versions of the facts, requirements, and relevant documents.
- **62.2** Show an outcome for each relevant item. Use states such as ready, missing, needs review, and not applicable. Retain unknown applicability where information is incomplete.
- **62.3** Show why an item is required, what supports it, what appears available, and what the user can do next. Link a document match to its source page and the underlying requirement to its official passage.
- **62.4** Handle alternatives without duplicate requests. When an approved document satisfies an alternative group, mark that group's readiness and show the evidence used.
- **62.5** Reevaluate affected items when a fact, document, channel, or source version changes. Preserve the previous evaluation in case history. Reopen only the decisions affected by the change.
- **62.6** Combine checklist results into a preparation state with visible blockers. Show whether the case can proceed to the available official channel, which field needs clarification, or where manual review is needed.
- **62.7** Confirm that a user can open a missing-item card in chat, add or select a document, and see the checklist refresh from backend evidence.

**Acceptance.** The pilot shows one ready item, one conditional item, and one item requiring user input. A case changes correctly when the user supplies or withdraws the relevant evidence.

## 63. Create the official form catalogue

- **63.1** Register the form or portal workflow as an asset for a specific procedure and channel. Store title, official code if available, authority, scope, language, effective dates when published, official URL, and review state.
- **63.2** Version the asset independently from the URL. For downloadable material, store a content fingerprint and reviewed template reference. A new PDF silently published at the same URL must still create a reviewable change.
- **63.3** Record whether preparation uses portal field guidance, a supported fillable PDF, or assisted manual completion. Classify online-only, static, fillable, and unsupported dynamic templates using verified examples.
- **63.4** Record what the reviewer checked, including template alignment, field labels, channel, and eligibility of the selected version for the supported procedure and jurisdiction.
- **63.5** Resolve form selection by procedure, authority, jurisdiction, channel, and applicable date. When more than one version appears plausible, ask the distinguishing question or show manual verification.
- **63.6** Expose the catalogue record inside chat. The agent and inline form card resolve the same reviewed version, link and applicability explanation.
- **63.7** Prepare fixtures for identical form titles, replacement at an existing URL, portal-only forms, and an unsupported form format.

**Acceptance.** Each enabled pilot form has a traceable official version and a reasoned preparation method. The user can open the original official channel from the selected asset.

## 64. Define and review the form-field mapping contract

- **64.1** Define stable field IDs distinct from template-specific names. Keep the original Italian label, translated explanation, section, page, and help text. Preserve the label the user will see in the official portal.
- **64.2** Define data type, output format, length, allowed values, required conditions, dependencies, and whether the field expects one or multiple entries.
- **64.3** Define acceptable input sources per field. Include user-entered values, confirmed case facts, and reviewed Phase 6 document values. Record why a proposed source is suitable for the field.
- **64.4** Define the reviewed mapping for each form version. For a PDF, record the exact qualified field name and any widget-specific behaviour. For a portal, use verified section labels and guidance users can follow in the official UI.
- **64.5** Support adjacent fields that look alike but mean different things. Test a contact address versus a declared address, an issue date versus a submission date, and repeated labels in different form sections.
- **64.6** Classify fields that need explicit user review, such as identity, reference numbers, consequential dates, and case-defining choices. Keep signature and official-use fields outside generated entry values.
- **64.7** Version and review the mapping independently of the case. Provide a test that verifies every mapped PDF field actually exists in its chosen template. [pypdf form structure](https://pypdf.readthedocs.io/en/stable/user/forms.html)

**Acceptance.** A developer can locate each mapped field in the official input, identify authorised value sources, and tell whether a user must review it. A changed or misidentified field fails validation.

## 65. Propose values and collect user approval

- **65.1** Generate field proposals from the approved mapping and the current case. Each proposal carries the field ID, value, provenance, case revision, and form or mapping version.
- **65.2** In an inline chat form-field card, show the official label, proposed value, explanation and source. Let users accept, edit, reject or defer inside the same transcript without losing other changes.
- **65.3** Show competing values when evidence disagrees. A user cannot confirm one silently inferred from another case. Open the relevant document page or case fact for verification.
- **65.4** Leave absent values unresolved. Ask targeted questions for genuinely necessary fields, including conditional fields that become required after another answer changes.
- **65.5** Bind user approval to the exact proposal and input versions. Make retries idempotent. If facts, evidence, or mappings change before approval is applied, expose the newer proposal and require the affected values to be reviewed again.
- **65.6** Preserve approved values that remain unaffected by a later edit. Show why an affected approval became stale and what the user needs to do.
- **65.7** Test reload, duplicate confirmation, two tabs, stale approval, and refusal. Confirm an edit does not accidentally update another field or case.

**Acceptance.** A user reviews and corrects one critical field with visible provenance. Review history survives closing and reopening the case, and stale confirmations cannot overwrite current data.

## 66. Validate preparation and show actionable errors

- **66.1** Validate on the server against the selected form and mapping versions. Check required fields, field types, format, allowed values, length, conditional sections, and cross-field consistency.
- **66.2** Keep factual confirmation separate from formatting validity. A well-formed identifier can still require user verification. Normalisation must preserve the meaning of names, accents, leading zeros, and dates.
- **66.3** Give validation results stable codes and field references. Distinguish blocking issues, items needing review, and optional suggestions. Provide a direct route back to the field that needs action.
- **66.4** Reevaluate conditional fields and checklist items after edits. Hide or clear obsolete derived values according to mapping rules while preserving the audit trail.
- **66.5** Before generating an output, check its exact prerequisites again. An expired version, unresolved required field, or missing critical approval must be visible. Users may still benefit from safe, verified partial guidance.
- **66.6** Test boundary lengths, unsupported characters, ambiguous dates, leading zeros, lost approval, and conflicting cross-field answers. Validate both Italian and English UI labels for the same official field.

**Acceptance.** Error messages point directly to the work users can perform. The system rejects a completed-draft claim when the selected form or required information is no longer valid.

## 67. Prepare values for the portal or generate a reviewed draft

- **67.1** Make portal preparation the default for verified online-only workflows. Show portal sections in order, original field names, approved values, and unresolved items. Let the user copy an individual value deliberately.
- **67.2** For a verified compatible PDF, use the pinned official template and the approved field mapping. Preserve the original source asset and generate a separate private draft. Production use depends on format and rendering tests.
- **67.3** Verify generated values in the PDF and render the result. Check text visibility, accents, multi-page widgets, boxes, radio and choice states, field overflow, and pagination in the supported preview and a representative reader.
- **67.4** Provide a manual guide for unsupported templates or fields. Show the official file and verified values where available. Identify unresolved fields and signature steps for the user.
- **67.5** Show a compact, inline summary of the prepared artefact and what was filled, with an authorised download action in chat. Keep draft status in the card and artefact metadata; retain template, mapping and case revision lineage. Do not open a separate PracticaMIA Preview screen. Keep signature and authority-reserved fields for the official process.
- **67.6** Enforce access controls for in-chat artefact inspection, copy and download. Keep personal values out of analytics and public links. Audit preparation actions without copying document contents into logs.
- **67.7** Test a portal workflow and a verified fillable fixture independently. Record the unverified output paths and recovery behaviour.

**Acceptance.** The user can enter verified portal values with the correct Italian field names. If a compatible official template is enabled, the draft renders correctly with the approved values and carries exact source lineage.

## 68. Prepare a response to an official request for additional documents

- **68.1** Use Phase 6 findings to list the original requested items and their passages. Tie each item to the notice reference and relevant case.
- **68.2** Let the user match or replace proposed attachments. Show resolved and outstanding requests, multiple requirements covered by one file, and files with the wrong case or scope.
- **68.3** Draft a concise response with the authority, reference, and user-approved attachment list. Preserve uncertain dates and identifiers as unresolved when the evidence is incomplete.
- **68.4** Let the user edit the draft and confirm which items are included. Link changes to the notice and preserve the previous draft in the case where needed.
- **68.5** Resolve the response channel from the notice and verified official catalogue. Surface channel conflicts or a missing proof of authority before presenting the route as confirmed.
- **68.6** In the pilot, use a notice that requests two items, of which one is already available and one remains missing. Verify the response draft reflects both states and the actual next action.

**Acceptance.** The user sees what the authority asked for, which attachments are ready, what remains, and the official channel supported by the available evidence.

## 69. Build the official handoff card and evidence contract

- **69.1** Show an inline chat handoff card with the authority, service or channel name, verified official link or office route, and one concrete next action, alongside prepared attachments, values and remaining checks. No new PracticaMIA page is required.
- **69.2** Check that the destination still matches the selected authority, procedure, location, and submission channel. If a previously verified destination is no longer usable, show the verified route available or identify the missing verification.
- **69.3** Explain the user’s part of the handoff, including any applicable official sign-in, signing, payment, attachment, or send step. Keep these actions under user control in the official channel.
- **69.4** Save a structured handoff record with case ID, form and checklist versions, channel, and the date of the preparation action. Keep official confirmation separate from the fact that a draft was exported or a link was opened.
- **69.5** Tell the user what to retain after submitting, such as a receipt or reference when the channel provides one. Pass that evidence contract to Phase 8 for tracking.
- **69.6** Test keyboard and mobile behaviour, interrupted navigation, unavailable destination, reopening the case, and switching between two similar authorities.

**Acceptance.** A user reaches the verified channel and can explain the next action. The case shows preparation and handoff accurately and can later receive submission evidence.

## 70. Verify form changes, evaluate the pilot, and close Phase 7

- **70.1** Subscribe form and requirement mappings to Phase 3 freshness updates. Detect versions that differ in content, portal labels, channels, or published instructions.
- **70.2** When a version becomes stale or is withdrawn, identify affected fields, approvals, drafts, and open cases. Prevent new completed drafts from using the withdrawn version. Keep earlier records inspectable and show their version.
- **70.3** Revalidate against the newly reviewed version. Transfer unchanged values only where mappings and approval conditions remain valid. Show users exactly which fields need a fresh review.
- **70.4** Build a regression set for scope, conditional rules, version transitions, alternative attachments, template changes, approval replay, access isolation, and the official handoff state.
- **70.5** Run a pilot from a Phase 6 notice through checklist evaluation, user correction, field preparation, and the verified official route. Include a missing attachment and a mid-process template change. Test reload after the correction.
- **70.6** Measure supported checklist decisions, critical field errors, false readiness, stale form use, user correction rate, unassisted next-action accuracy, and preparation time. Agree thresholds before enabling each capability for users.
- **70.7** Deliver the validated procedure matrix, rule and form versions, approval and evidence contracts, export format support, pilot results, and handoff event model to Phase 8.

**Acceptance.** The selected pilot workflow can be completed to the official handoff with a traceable checklist and approved fields. Changes to official evidence reopen affected preparation steps. Tracking can distinguish a prepared case, a claimed submission, and evidence of submission.

## Implementation order

| Slice | Tasks | Expected result |
| --- | --- | --- |
| Verified requirements | 61–62 | Applicability and personalised readiness with evidence |
| Verified forms and values | 63–66 | Versioned form, reviewed mappings, user approval, and actionable errors |
| Prepared output and handoff | 67–69 | Portal-ready guidance or compatible draft, response preparation, and the verified channel |
| Change recovery and pilot | 70 | Version-change regression and handoff contract verified for Phase 8 |

**Closure demonstration.** A user opens a reviewed notice from Phase 6. PracticaMIA explains one conditional requirement and identifies an unresolved field. The user corrects it and reviews the prepared values in the same workspace. When the form version changes, the affected field returns to review. After confirming it again, the user opens the verified official channel and can later return to the same prepared case.
