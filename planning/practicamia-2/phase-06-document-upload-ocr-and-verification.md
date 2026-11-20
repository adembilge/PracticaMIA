# PracticaMIA 2.0 — Phase 6 · Document upload, OCR, and verification

**Roadmap tasks 51–60.** Let a user attach an administrative document to an authorised case, locate the passages on which the agent relies, correct extracted values, and act on a verified request. The first end-to-end workflow is a notice requesting an attachment or clarification. A receipt can supply tracking evidence. Neither workflow changes an official status without evidence.

**Dependencies.** Phase 2 supplies pilot cases and expected outcomes. Phase 3 supplies the catalogue, official evidence, and applicable requirement IDs. Phase 4 supplies typed tools, approval events, and idempotent case updates. Phase 5 supplies the single chat composer and inline document/next-action cards; no separate document workspace or preview page is permitted. Phase 7 receives confirmed field values and provenance for form preparation.

**Implementation choices to validate.** Start with PDF, JPEG, and PNG candidates. Validate format and document-type support against the pilot before publishing the support matrix. Use native text extraction for suitable PDF pages and a separately versioned OCR adapter for image pages. Benchmark a local engine such as Tesseract on the pilot material. Decide on any hosted processor only after measuring accuracy, latency, cost, and reviewing its data handling. Run parsing and OCR as bounded background work.

## 51. Define supported administrative document types and their contracts

- **51.1** Select initial document types from actual Phase 2 obstacles. Prioritise notices requesting information or attachments and submission receipts. Add portal screenshots, official forms, and supporting documents where a pilot case has a defined outcome.
- **51.2** For each document type, specify what the system can identify, required fields, optional fields, and the next action it can help prepare. Define administrative document type separately from file format. A PDF can be a notice, receipt, or something the system cannot classify.
- **51.3** Define the supported file profile. Consider native-text, scanned, and mixed PDFs, plus JPEG and PNG photos or screenshots. Derive file size, page, image, and processing limits from fixture sizes, worker capacity, and the pilot rather than inventing production targets.
- **51.4** Define a typed document record. Include document ID, owner, case, storage reference, file version, media type, origin, upload and processing states, and extraction revision. Keep processing and human review status separate.
- **51.5** Define response types for unreadable, incomplete, unknown, or wrong-case documents. Keep the user's case unchanged until they resolve an ambiguous attachment. Show whether they can upload a clearer copy, correct the case, or proceed manually.
- **51.6** Prepare redacted or synthetic fixtures for each supported outcome. Include clean originals, skewed scans, partial screenshots, duplicate pages, conflicting values, and unreadable fields.

**Acceptance.** Each enabled document type has a real pilot need, an observable result, a defined error path, and labelled fixtures. Unknown files cannot be interpreted as a supported official document by default.

## 52. Implement authenticated upload and quarantine

- **52.1** Authorise both upload creation and finalisation against the current user and case. Use an application-generated object key and a scoped, short-lived upload permission where direct storage upload is used.
- **52.2** Validate allowlisted extensions, actual content and supported format. Enforce byte, page, pixel, and resource limits. Handle encrypted, malformed, truncated, and unsupported files with recoverable messages.
- **52.3** Store new files in private quarantine. Require the configured malware scan and validation before making the file eligible for parser, OCR, or preview processing. A failed or unavailable scan leaves the file unprocessed and offers the appropriate next step.
- **52.4** Bind finalisation to the authorised upload ID and the immutable object version or checksum that was checked. Treat repeated finalisation as the same operation. Prevent a file from being replaced between scanning and processing.
- **52.5** Restrict the accepted PDF and image features to what the supported workflow needs. Handle embedded attachments, active content, oversized decodes, and problematic metadata according to the documented file policy.
- **52.6** Remove abandoned uploads and failed temporary objects on a defined schedule. Record administrative outcomes such as scanner timeout or rejection without logging content or original filenames.
- **52.7** Test interrupted upload, wrong media type, limit violations, scanner outage, duplicate completion, and attachment to another user's case.

**Acceptance.** Only an authorised, validated, scan-cleared object can enter extraction. Upload failure preserves the message draft and other valid attachments. [OWASP file upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)

## 53. Build private storage, access, retention, and deletion

- **53.1** Use private object storage and transport encryption. Record the storage region and the systems that can read each data class. Keep originals, previews, temporary derivatives, and extraction results associated with their document version.
- **53.2** Enforce case ownership at each read, download, preview, extraction, or deletion request. Authorise workers through narrowly scoped service identities. Avoid exposing storage keys or granting the agent direct file-system access.
- **53.3** For previews and downloads, use short-lived authorised access. Where immediate revocation is needed, choose a server-mediated read or equivalent access control and test what remains reachable after case deletion or session changes.
- **53.4** Define retention per artefact. Include originals, thumbnails, OCR text, extracted fields, temporary copies, jobs, logs, and backups. Delete expired or user-deleted data through a repeatable operation and record its outcome without retaining the document content.
- **53.5** Minimise storage and model access to fields needed for the user's task. Keep uploaded files, OCR results, and user-specific extraction out of the official catalogue, its index, and unrelated cases.
- **53.6** Before enabling personal documents in a pilot, review the processing purpose and lawful basis, special-category handling where relevant, third-party processing and transfers, retention, deletion, and any required impact assessment. Carry the resulting controls into Phase 9 verification.
- **53.7** Test two accounts, expired access, deletion while a job is active, attachment moves where supported, and retention expiry. Verify that screenshots and traces used in tests are redacted or synthetic.

**Acceptance.** A second account cannot retrieve a known document ID or preview. Removing access or deleting a document disables new reads and cancels or prevents stale worker output. [GDPR, Articles 5 and 25](https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng)

## 54. Implement the background processing workflow

| Stage | Exit condition |
| --- | --- |
| Upload received | Finalised object linked to the authorised case |
| Safety checks pending | Validation and scanning produce a recorded outcome |
| Ready to process | A specific cleared document version is available |
| Extracting | Page-level extraction completes or records partial/failure outcomes |
| Ready for review | Preview and structured findings are available |
| Failed, cancelled, or replaced | Outcome is visible and stale output cannot alter the case |

- **54.1** Define allowed state transitions and inline display states in the Phase 5 chat composer and document cards. Represent partial extraction and user review explicitly.
- **54.2** Create jobs using document version, pipeline version, and stage as the idempotency scope. Repeated events or worker retries must not duplicate document records or publish the same result twice.
- **54.3** Set worker concurrency and resource budgets. Bound retry attempts for transient errors. Return a stable actionable error for permanent failures. Keep a failed-job record for controlled diagnosis and replay.
- **54.4** Isolate parsing and OCR workers from broad network and storage access. Use time, memory, page and decode limits. Remove temporary artefacts once work completes or is abandoned.
- **54.5** Apply results only if the expected document and case versions still permit it. Cancellation, replacement, and deletion must take precedence over late results. Recover incomplete jobs after worker restart.
- **54.6** Publish only user-facing progress events such as “Checking the file”, “Reading pages”, and “Ready for review”. Use page progress only when it reflects actual work. Avoid exposing parser output in status events.
- **54.7** Verify queue failures, process restart between stages, repeated delivery, cancellation during work, and many files attached to the same case.

**Acceptance.** A valid file can recover from a transient worker failure without duplicates. Users see a terminal or recoverable state and their case remains consistent.

## 55. Extract native text and apply OCR at page level

- **55.1** Evaluate each PDF page for a usable text layer. Use native extraction where text is legible and its layout can be mapped. When a layer is absent or unusable, render that page under resource limits and apply OCR.
- **55.2** Preserve page order, text blocks, reading order, and coordinate anchors. Record page dimensions, orientation, and the transform used to map extraction coordinates back to the original preview.
- **55.3** Benchmark deskewing, rotation, contrast changes, and cropping on labelled samples. Keep the original unchanged. Avoid transformations that remove marginal marks or change the interpretation of data.
- **55.4** Configure language and layout from measured needs. Start with Italian document text and evaluate English or mixed-language pages in the pilot. Include two columns, tables, stamps, and poor-quality phone photographs.
- **55.5** Report extraction by page as readable, partial, unreadable, or failed. A poor-quality date or clipped field should remain unknown and require replacement or review. Do not reconstruct missing characters.
- **55.6** Record extraction method, processor version, preprocessing version, and timing. Retain enough provenance to reproduce a field without logging raw document contents.
- **55.7** Compare native and OCR results against ground truth. Use field-level checks on dates, references, headings, and requested attachments alongside text accuracy.

**Acceptance.** A mixed native and scanned PDF returns distinguishable results by page. Users can locate extracted text on the original page and understand what remains unreadable. [Tesseract image-quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)

## 56. Classify documents and extract typed, traceable fields

- **56.1** Classify the document type and likely issuer. Represent ambiguous and unknown results explicitly. Match issuer candidates against the Phase 3 authority catalogue where relevant.
- **56.2** Define per-type schemas for fields such as reference, issue date, stated response date, requested attachment, channel, or receipt identifier. Distinguish the date the document was issued from dates used for another event.
- **56.3** Return original text, normalised candidate, source page and span or coordinates, extraction method, pipeline revision, and review state for each field. A field can have competing candidates.
- **56.4** Use structured extraction and validate values server-side. Normalisation must not turn an ambiguous date or missing digit into a confirmed field. Model or OCR confidence can prioritise review and cannot substitute for confirmation.
- **56.5** Require clear document evidence for factual extraction. Treat embedded instructions and links as untrusted document content. A file cannot grant access, select a privileged tool, or authorise a case update.
- **56.6** Expose an authorised read-only document tool to the Phase 4 agent. Return selected evidence and field IDs relevant to the user task. Use the existing proposal and approval flow for case writes.
- **56.7** Test similar documents from different authorities, different types with similar headers, contradictory values across pages, and stable field references on reprocessing.

**Acceptance.** Critical extracted values can be located on the original page. Unsupported classifications or missing evidence produce an explicit unknown state.

## 57. Turn a notice into its next actionable task

- **57.1** Identify the issuer, document reference, request, listed attachments, explicitly stated date, and stated response channel where available.
- **57.2** Present the notice wording and the agent's explanation with traceable evidence. Highlight the original Italian phrase where it helps the user find it on the document.
- **57.3** Distinguish a date printed in the document from an inferred deadline. An ambiguous or event-dependent deadline remains pending until the necessary facts and applicable rule are verified. Give the user the location and the missing information.
- **57.4** Use the official catalogue to verify the relevant authority and channel when they can be identified. Surface differences between the document and current sources for review. Keep document-specific information tied to the case.
- **57.5** Produce one next-action card, such as “Review the requested attachment” or “Confirm the date on page 2.” Include supporting passage, uncertainty, and any verified official channel.
- **57.6** Let the user confirm or correct the result using the Phase 4 proposal flow. Use only recorded evidence to describe application or submission status. Leave later form generation to its Phase 7 contract.

**Acceptance.** In a pilot notice, the user can explain what was requested, show where it is written, and identify the concrete next step without depending on an unsupported inference.

## 58. Detect missing, mismatched, and conflicting documents

- **58.1** Compare files with the applicable verified requirement or the explicit request in the notice. Use the procedure, location, version, and case conditions. If coverage is incomplete, identify which checklist items are still unknown.
- **58.2** Model requirement outcomes such as present, missing, unreadable, conflicting, or awaiting review. Only mark a requirement missing when there is evidence that it applies and no usable supporting file meets it.
- **58.3** Match an attachment to a requirement with an explanation. Confirm classifications for files with similar names. Ask before attaching a file that appears to belong to another case.
- **58.4** Compare normalised values with the original strings visible. Distinguish format variation from material conflict. Show both pages or the confirmed case field rather than silently choosing a value.
- **58.5** Let the user correct, replace, or decline a proposed match. Link each resolution to requirement version and evidence. Recheck affected results when a source or document changes.
- **58.6** Test exact matches, harmless formatting differences, genuinely conflicting dates or references, duplicate attachments, and an invalidated requirement. Keep decisions isolated across cases.

**Acceptance.** The product shows a justified missing attachment and a traceable conflict in the appropriate pilot cases. Ambiguity remains reviewable and no conflict is resolved silently.

## 59. Complete review, correction, and approval in the conversation

- **59.1** Expand an authorised document evidence card inside the chat transcript, with page navigation embedded in the card. Selecting an extracted field highlights the original passage when coordinates exist. Do not redirect to a document or Preview screen.
- **59.2** Show raw and normalised values, quality flags, review status and confirmation effects inside the message card. On mobile, expand the field and page evidence sequentially within the transcript without losing selection.
- **59.3** Support accept, correct, mark unreadable, upload a replacement page or document where supported, and retry extraction. Maintain original evidence and user corrections in the audit history.
- **59.4** Apply user-approved facts through Phase 4's typed proposal contract. Bind approval to document, extraction, field, and case revisions. Require fresh review if the underlying evidence changes.
- **59.5** Preview downstream impact when a user changes a previously confirmed field. Mark related form suggestions or pending actions for revalidation. Do not silently overwrite prior confirmations.
- **59.6** Preserve chat context, scroll, focus and case while expanding or collapsing document cards. Provide a text alternative for unavailable page highlights. Show saved corrections only after backend acknowledgement.
- **59.7** Verify keyboard, desktop, mobile, session expiry, concurrent edits, and save failures.

**Acceptance.** A user can locate, correct and confirm a critical document field in chat, collapse and reopen its card, and find the confirmed value and updated next step in the same transcript. Phase 7 distinguishes confirmed and unresolved field values.

## 60. Evaluate document workflows and close Phase 6

- **60.1** Build a held-out, redacted or synthetic evaluation set across pilot authorities, document types, native PDFs, scans, and photographs. Label exact fields, spans, page numbers, requested attachments, unreadable content, and expected next actions. Keep documents from the same source template together where relevant when splitting the set.
- **60.2** Measure document classification, critical field precision and coverage, evidence location, unreadable-field detection, missing attachment precision and recall, conflict detection, and user correction frequency. Set release thresholds after measuring the baseline by document type.
- **60.3** Measure upload-to-review time, failure recovery, queue wait, worker cost, and the impact of OCR preprocessing. Report partial results instead of treating all incomplete documents as failures or successes.
- **60.4** Run the negative path suite. Cover wrong-case attachments, interrupted upload, scanner failure, unauthorised access, cancelled jobs, stale approvals, and document text trying to trigger tools.
- **60.5** Run a user test with a redacted or synthetic notice. Ask the participant to identify the requested item and correct a field using page evidence. Record time, need for assistance, and whether they reached the correct next action.
- **60.6** Verify the end-to-end slice in a controlled test environment, using only one customer chat route: upload, scan, extract, review, correct, confirm, show the next action, close the browser, and resume the same conversation. Include a poor-quality document needing a replacement.
- **60.7** Hand off the supported document matrix, approved field and provenance contract, unresolved fields, benchmark findings, and review events to Phase 7. Enable personal document types only where the agreed privacy, security, and quality checks are complete.

**Acceptance.** The notice workflow succeeds with positive and recovery examples, including after reopening the case. Each enabled document type has measurable evidence, and outputs cannot mark an unreadable field as confirmed or a receipt as approval.

## Delivery order

| Slice | Tasks | Expected result |
| --- | --- | --- |
| Safe file intake | 51–54 | Authorised upload, quarantine, storage, and retry-safe processing |
| Read and understand | 55–57 | Page-level extraction, evidence-linked fields, and a useful notice action |
| Compare and confirm | 58–59 | Missing attachment and conflicts are reviewable and corrections persist |
| Verify and hand off | 60 | Pilot evidence and confirmed field contracts are available for Phase 7 |

**Closure demonstration.** A user uploads a scanned notice from chat. PracticaMIA points to the requested attachment and the relevant page. The user corrects an ambiguous value, confirms the correction, and sees the verified next action. An unreadable field stays unresolved. Returning later restores the same case, evidence, and next action.
