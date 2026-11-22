# Phase 3.5 — Evidence for each procedure claim

[PracticaMIA 2.0 task 21.5](phase-03-official-sources-and-catalog.md#21-model-procedures-authorities-sources-and-evidence) links each procedural claim to the section that actually supports it. The [authority-role](phase-03-authority-roles.md) and [service-channel](phase-03-service-channels.md) assignments each make claims; a retrieved passage is evidence to inspect, not an automatic endorsement of every statement made about its topic.

## Claim and evidence contract

Record a separate, reviewable claim for each material assertion. A claim identifies the procedure and step, its exact statement, its type (for example authority role, filing channel, condition, document, form, fee or deadline), and its jurisdiction and case conditions. Split a sentence when its parts need different evidence or scopes. Keep an unsupported part unresolved rather than treating a citation for another part as proof of the whole sentence.

For each claim, retain one or more evidence links with `source_id`, `source_version_id`, `passage_id`, and the passage's section path or PDF page. The linked version and passage must agree with the [source-version contract](phase-03-source-versioning.md). Record which words or facts in the passage support the claim, including the relevant qualification or exception. A URL, document title, search hit, or form field name can be a research locator but cannot by itself complete a trusted evidence link. If extraction loses a material table row, footnote or condition, keep the claim pending until a faithful versioned passage can be reviewed.

The reviewer checks the claim's wording and scope against the exact passages, their current approval and integrity, and any conflicting material. Review of a source version alone does not approve every possible claim inferred from it. The claim can support current guidance only after its own assertion and applicability have been reviewed and all required source versions still pass the [registry trust checks](../../docs/OFFICIAL_SOURCE_REGISTRY.md#trust-model). If evidence is missing, contradictory, outside the jurisdiction or from an inactive version, withhold the claim from trusted guidance and record the gap. Preserve earlier claim and citation references in case history under the [3.3 contract](phase-03-source-versioning.md#citation-on-a-saved-case), without using them as current evidence after withdrawal.

### What a passage may support

| Candidate claim | Evidence required |
| --- | --- |
| An office receives a particular filing. | A passage identifying that office's role for the procedure and applicable scope; a publisher name alone is insufficient. |
| A portal accepts a filing. | A passage describing submission through that portal for the relevant step and case; a public information page or downloadable form alone supports only the action it describes. |
| A form asks for a field. | The versioned form page or official instructions showing that field. This does not establish that the form is an accepted filing route or that the field is mandatory in every case. |
| A fee has a specific amount or applies to a case. | Current reviewed material explicitly supporting the amount, currency, applicable procedure, payer and conditions, plus any relevant [temporal scope](phase-03-source-dates.md). A form explanation or payment field alone cannot verify a current fee. |
| A deadline or requirement applies. | Passages supporting the trigger, scope, condition and exceptions, followed by a separately reviewed deterministic rule where a case-specific decision is needed. |

## Existing support and implementation gap

The current registry stores version-scoped `KnowledgePassage` IDs, section paths, exact offsets and hashes. [Approved passage search](../../docs/APPROVED_PASSAGE_SEARCH.md#contract) verifies active source versions and returns those identifiers. The signed first-route ruleset has `evidence_refs`, which the [case checklist](../../backend/app/cases/checklist_service.py) resolves again before use. These controls provide traceability for that narrow reviewed route. The general Phase 3 catalogue does not yet store independent claim records, claim-specific support decisions or reviewed links for the proposed 3.1 and 3.2 assignments. Search relevance and a valid citation do not establish that a claim is fully supported. Implementing the general claim review and invalidation flow remains separate work; this document makes no new source or rule approval.

## Acceptance scenarios

Use synthetic passages and fictional procedures; none of the examples states a real administrative fee or obligation.

| Scenario | Expected decision |
| --- | --- |
| One passage names the receiving office and its service area. | Link the scoped receiving-role claim to that exact version and passage after review. |
| A sentence names both a receiving office and an online filing channel, but the passage supports only the office. | Split the claims; keep the channel claim pending. |
| A form explains where to enter a payment amount but states no current fee. | Do not issue a fee amount or fee-applicability claim from that form. |
| A fee passage covers a different procedure, place or case category. | Reject it as support for the requested claim even if the amount matches. |
| A deadline passage omits the trigger or an exception needed for the case. | Keep the case-specific deadline unresolved and request supporting evidence or review. |
| Two current official passages conflict on a material condition. | Preserve both references, flag the conflict and withhold the affected claim. |
| A cited source version changes or loses approval. | Stop using the claim for current guidance; retain its historical citation and require re-review. |
