# PracticaMIA 2.0 — Phase 3 · Official sources and Italy-wide procedure catalogue

**Roadmap tasks 21–30.** When a user asks which authority says something, where it applies, and where it is written, PracticaMIA should identify the service, competent authority, applicable source version, and supporting passage. The real cases from Phase 2 determine the initial scope. The Phase 4 agent and the user interface query the same catalogue.

## 21. Model procedures, authorities, sources, and evidence

| Record | Information held |
| --- | --- |
| Authority | Official name, authority ID, aliases, domains, and units |
| Jurisdiction | Italy, region, province, municipality, or authority-specific service area |
| Procedure | User task, official Italian name, alternative phrasing, and authorities |
| Service channel | Portal, downloadable form, appointment, office, or official contact |
| Source and version | Durable ID, URL, publisher, observed version, and review |
| Evidence passage | Heading, paragraph, table row, or PDF page |
| Rule and form reference | Supported condition, document requirement, or form version |

- **21.1** Record the roles of authorities involved in a procedure, such as publishing the service or receiving the application.
- **21.2** Record each valid channel and the scope in which it applies.
- **21.3** Keep the source ID separate from its version. Create a version when content changes at the same URL and retain previous case citations.
- **21.4** Store publication or update, observation, and effective dates independently. Allow missing dates when the source does not state them.
- **21.5** Link each claim to the source section that supports it. A form explanation by itself cannot verify a current fee.
- **21.6** Define how to migrate Phase 1 records. Send records with unclear approval scope back to review.

**Acceptance.** A procedure supports multiple authority roles, locations, and sources. Each claim leads to a version, passage, and review decision.

The [21.1 authority-role contract](phase-03-authority-roles.md) defines how to record each body's role and the evidence for that relationship.

The [21.2 service-channel contract](phase-03-service-channels.md) defines how to record where each step takes place and which case conditions make the channel applicable.

The [21.3 source-version contract](phase-03-source-versioning.md) defines revision identity and how a saved case keeps the exact citation it used.

The [21.4 source-date contract](phase-03-source-dates.md) separates publisher-stated, observation, review and effective dates and records missing dates explicitly.

## 22. Import Italian authority and geography identifiers

- **22.1** Use [IPA](https://indicepa.gov.it/ipa-dati/dataset/amministrazioni) for authorities and [ISTAT](https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/) for administrative units. Record the release, URL, and ingestion time.
- **22.2** Keep external IDs, catalogue IDs, and display names independent. Preserve case links through name changes.
- **22.3** Match official and former names, acronyms, languages, and spelling variants. Return candidates and ask for a distinguishing location when ambiguous.
- **22.4** Keep office addresses and service areas distinct. A location and a procedure can point to different areas.
- **22.5** Make import idempotent and detect new, changed, merged, and inactive records.
- **22.6** Test namesakes, city and province distinctions, renaming, and authorities serving multiple municipalities.

**Acceptance.** An unambiguous name consistently resolves to one ID. Ambiguous queries return relevant candidates.

## 23. Register official sources for the pilot workflows

- **23.1** Write down what must be answered for each pilot case, such as the competent authority, current form, and conditional requirement.
- **23.2** Choose the appropriate evidence type for each question. An authority directory supports identity, a service page supports the channel, a form supports its fields, and an instruction or rule supports requirements.
- **23.3** Record issuer, official URL, document type, language, access, procedure, location, reuse terms if known, and review date.
- **23.4** Evaluate the [Single Digital Gateway](https://www.agid.gov.it/it/agenzia/attuazione-misure-pnrr/sportello-digitale-unico-single-digitale-gateway) and similar directories for discovery. Tie document, date, and fee claims to evidence from the competent authority.
- **23.5** Record each case's source gap. Where the authority is confirmed and the local form remains unverified, record routing as the supported capability.
- **23.6** Measure discoverable procedures, verified explanations, rule evidence, and form versions.

**Acceptance.** Each pilot case has a competent service or a visible source gap explaining why it could not be verified.

## 24. Build HTML and PDF source ingestion

- **24.1** Fetch sources in background jobs. Record URL, source ID, attempt time, outcome, and errors. Continue processing other sources when one fails.
- **24.2** Handle HTTP status, redirects, content type, size, encoding, and timeouts. Revalidate redirects to a different domain.
- **24.3** Retrieve sources whose access conditions permit ingestion. Send login-required, automation-blocked, or uncertain sources to review. Allow manual evidence where appropriate.
- **24.4** Fingerprint raw content and cleaned text separately. Identify whether changed menus or cookie notices affect the substantive content.
- **24.5** Deduplicate identical content. Preserve the previous version and queue review when it changes.
- **24.6** Limit this pipeline to official sources. User document storage and processing belong to Phase 6.
- **24.7** Test 404s, transient server errors, invalid PDFs, unexpected files, redirect loops, and unchanged content.

**Acceptance.** Identical content creates no duplicate. Changed content creates a review record. Fetch errors leave prior evidence intact.

## 25. Turn source content into citable evidence

- **25.1** Extract HTML headings, paragraphs, lists, tables, and links structurally. Remove recurring site elements.
- **25.2** Preserve the original PDF page, text blocks, and table relationships. Record OCR use and flag critical fields for review.
- **25.3** Include the relevant condition and exception with the passage. Retain row and column headers with table cells.
- **25.4** Give every evidence passage a stable ID and location. Allow navigation to the URL, source version, section, or page.
- **25.5** Preserve the official Italian wording. Make the underlying passage accessible when showing a translation.
- **25.6** Verify that a claim with only a document title and no supporting passage fails citation validation.

**Acceptance.** A reviewer can open the official location from a search result and read the relevant instruction in context.

## 26. Build source review, approval, and withdrawal

- **26.1** Define new, under review, approved, rejected, archived, and withdrawn version states and their effects on search and answers.
- **26.2** Show the reviewer prior and new content, changes, publisher, procedure, and proposed jurisdiction.
- **26.3** Record approval by procedure, location, condition, time, and evidence type. Review a form explanation and a mandatory requirement on their respective evidence.
- **26.4** Write reviewer, time, decision, rationale, and version to the audit history.
- **26.5** Exclude withdrawn versions from new responses. Flag linked steps in open cases for revalidation.
- **26.6** Test reviewer authorisation and which source versions can be published as verified.

**Acceptance.** Each approved use has traceable scope and rationale. Unapproved or withdrawn versions cannot provide verified guidance.

## 27. Implement applicability and source conflict handling

- **27.1** Pass procedure, location, date, and known conditions as typed query fields. Support a residence location that differs from the service location.
- **27.2** Evaluate national instructions with applicable local channels or office details. Preserve the scope of each.
- **27.3** Return clarification requirements when missing context changes the outcome.
- **27.4** Cover older versus newer versions, local variants, and genuine contradictions.
- **27.5** Send unresolved conflicts and both pieces of evidence to review. Show the user a verified official channel where possible.
- **27.6** Reassess dependent evidence and preparation steps when the municipality, date, or procedure changes.

**Acceptance.** Evidence from two local jurisdictions remains isolated. Missing context and genuine conflict produce observably different outcomes.

## 28. Build hybrid search and the agent query API

- **28.1** Establish a PostgreSQL full-text baseline for Italian terms, acronyms, form codes, and authority names.
- **28.2** Evaluate semantic search for everyday phrasing, synonyms, and multilingual queries. Add pgvector if the measured gain justifies it.
- **28.3** Filter by procedure, jurisdiction, and review status before retrieval.
- **28.4** Rank by relevance, applicability, source type, and freshness. Avoid filling results with copies of the same content.
- **28.5** Define a typed response for Phase 4 containing procedure, authority, location, channel, version, passage, coordinates, and missing context as applicable.
- **28.6** Verify through API tests that the UI and agent resolve the same source and version.
- **28.7** Measure whether correct procedures and passages appear among the first results, as well as wrong-jurisdiction and unanswered queries. Set targets from the first set.

**Acceptance.** Equivalent official Italian and everyday English queries reach the applicable service. Researchers can inspect why filters excluded a result.

## 29. Monitor freshness, links, and form versions

- **29.1** Set check frequency by source type and impact on the user's task.
- **29.2** Track URLs, redirects, versions, and relevant text changes. Distinguish presentation changes from procedural instructions.
- **29.3** Identify affected rules, fields, procedures, and cases. Prioritise date, fee, document, and form changes.
- **29.4** Define separate retry or review paths for outages, relocated pages, and verified content changes.
- **29.5** Refresh the index and cache on withdrawal. Recheck version status before answering if search returns stale results.
- **29.6** In open cases, show the affected step and which fields need review.

**Acceptance.** The system can identify records affected by a change. Withdrawn versions cannot support new answers, and their previous use remains visible in case history.

## 30. Finish the Official Sources view and close Phase 3

- **30.1** Add an Official Sources view within the application shell, searchable by authority, procedure, region, municipality, and document type.
- **30.2** Show publisher, official link, procedure, applicability, last check, and accessible passage.
- **30.3** Resolve agent citation IDs to the same source version and passage. Pass this contract to Phase 4.
- **30.4** Show the regions and capabilities for which a procedure has verified sources.
- **30.5** Test adding a source, approving it, finding it, receiving a new version, and withdrawing the old version.
- **30.6** Pass the search API, catalogue IDs, citation schema, uncertainty outcomes, regression cases, and pilot scope to Phase 4.

**Acceptance.** The UI and agent API show the same version, scope, and passage. The pilot set covers wrong location, obsolete forms, changes, and withdrawal.

## Phase 3 closure checklist

- Authority and geography directories, the pilot catalogue, and versioned sources and passages are available.
- Review, withdrawal, and freshness workflows are verified.
- The search API, evaluation set, and Official Sources view share evidence IDs.
- A pilot case yields the right procedure, competent authority, applicable source, passage, and valid channel. Changing its municipality or form version produces the expected change in results.
