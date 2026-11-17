# Phase 3.4 — Source dates and temporal applicability

[PracticaMIA 2.0 task 21.4](phase-03-official-sources-and-catalog.md#21-model-procedures-authorities-sources-and-evidence) keeps dates stated by a publisher separate from capture, review and effective dates. Each date belongs to the [source version](phase-03-source-versioning.md) or to the specific claim it qualifies. A missing publisher date is unknown, not the date the page was retrieved.

## Date contract

| Date | Meaning and record | When absent |
| --- | --- | --- |
| `published_on` | Publication date explicitly stated by the publisher for this version, with its source locator. | Leave unknown; do not derive it from the URL, HTTP headers or capture time. |
| `updated_on` | Publisher's stated content-update date, separately from publication. Preserve the displayed value and its locator. | Leave unknown; do not treat a later observation as an update. |
| `observed_at` | When the exact source version was captured, as a timezone-aware timestamp. The existing `KnowledgeSourceVersion.retrieved_at` records this for a new version. | A stored version must have it; a research candidate without a capture has no observation evidence. |
| `reviewed_at` | When a human approved that exact version, recorded by the existing review workflow. | Null while review is pending. It does not substitute for any publisher date. |
| `effective_from` / `effective_until` | Dates explicitly governing a particular procedure claim, rule or channel assignment. Attach the supporting version and passage; use source-version-wide dates only when the statement applies to the whole source. | Leave unknown. Do not assume publication, update, observation or review makes a rule effective. |

Store a publisher-stated date as a normalized calendar date only when its day, month and year are unambiguous. Retain the original wording and passage or page locator, including the stated timezone or boundary wording where relevant. If the source gives only a month, a range without clear endpoints, or conflicting dates, keep the text and mark the normalized value unresolved. Do not insert a guessed day, end date or timezone. A date in a document title or an HTTP `Last-Modified` header is a research lead, not proof of the date of an administrative claim.

The current browser-rendered capture stores `observed_last_updated` as the page's displayed `DD/MM/YYYY` string. It is **publisher update metadata**, not the capture time; `retrieved_at` is the capture time. That import path currently rejects pages without a displayed update date. An undated page may still be handled through another permitted acquisition method, but the missing date must never be fabricated to pass browser-capture validation.

An unchanged repeat capture reuses the latest version and does not change its `retrieved_at`. The registry does not currently retain a separate last-checked timestamp for that repeat. A changed body or supported capture metadata creates a new pending version with a new observation time; any publisher date stated in that version remains separate. It does not rewrite the older version's dates or its case citations. Human review and the existing active-version checks still govern trusted guidance. A future effective date cannot by itself approve a source or activate a rule.

## Existing support and implementation gap

The current registry stores `retrieved_at`, `reviewed_at` and, for browser-rendered captures, the raw `observed_last_updated` string. It has no general `published_on`, normalized `updated_on`, effective-date fields or per-claim temporal evidence record. The [registry trust model](../../docs/OFFICIAL_SOURCE_REGISTRY.md#trust-model) checks approval, scope and integrity; it does not calculate whether an administrative claim is currently effective. Adding those fields and temporal applicability checks remains a separate implementation and human-review task. This design does not change the existing database, APIs, source approvals or rules.

## Acceptance scenarios

Use synthetic publisher text and versions; these dates do not assert any real administrative deadline or eligibility rule.

| Scenario | Expected record or decision |
| --- | --- |
| An undated page is captured through a permitted method. | Record its observation time; leave publication, update and effective dates unknown. |
| A page states it was published on 10 March 2026 and updated on 20 March 2026; it is captured on 25 March 2026. | Preserve the two stated dates and the distinct capture timestamp with their provenance. |
| A passage announces a change effective from 1 April 2026. | Link that date to the specific claim and passage. Do not apply it to unrelated claims or treat it as approved guidance. |
| Two passages give different effective dates for different case categories. | Keep separate scoped dates; do not assign one date to the whole document. |
| The same bytes and capture metadata are observed again later. | Reuse the version; do not present its original `retrieved_at` as the latest check. |
| A changed version is captured at the same URL. | Keep each version's dates and old case references separate; the new version awaits review. |
| A displayed date is partial, contradictory or absent on the browser-capture path. | Do not normalize by guesswork; flag unresolved data or reject that capture path under its current validation rule. |
