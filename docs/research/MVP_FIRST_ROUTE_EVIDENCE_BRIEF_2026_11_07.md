# Milan individual residence-change MVP — evidence review brief

**Research snapshot:** 7 November 2026. **Status:** candidate evidence; NOT an approved production ruleset. This file cannot authorize the app to issue mandatory requirements or produce a filing-ready package.

## Proposed narrow product scenario

One fictional Italian citizen, already registered resident in Italy, moving individually into Milano without joining an existing household. These questions distinguish the first *product-supported scenario*; an out-of-scope answer is not a legal ineligibility finding.

## Direct official sources to review

| Institution / source | URL | What the published page supports | Review needed |
| --- | --- | --- | --- |
| Comune di Milano, specific Italian resident FAQ, updated 23 July 2026 | https://servizicrm.comune.milano.it/centro-supporto/KA-00371/ | Notification to Anagrafe within 20 days via ANPR; household aggregation requires additional consent; TARI declaration is separate | Confirm stored source-version hash, capture freshness, exact passages and scope |
| Comune di Milano, Cambio di residenza service | https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza | This service covers changes from another Italian municipality or within Milan; online access requires SPID/CIE; municipality reviews after declaration | Acquire and independently approve complete current snapshot |
| Comune di Milano, general residence-change FAQ | https://servizicrm.comune.milano.it/centro-supporto/KA-00330/ | Foreigners already resident in Italy have a route distinct from arrival from abroad; appointment/household exceptions exist | Confirm whether any branch conditions affect chosen narrow case |
| ANPR official citizen change-of-residence guide | https://sc.anpr.interno.it/serviziCittadino/dist/docs/guida_compilazione_cambio_residenza.pdf | Candidate guide for the actual ANPR data-entry workflow and attachments | Verify publication/currentness, exact required fields and conditional attachments; independently review original PDF before encoding rules |

## Verified direction, NOT approved rule activation

- The proposed user handoff is the **official ANPR service**, operated by the person using their own credentials. PracticaMIA must not request SPID/CIE passwords, submit the declaration, or claim acceptance.
- The Milan FAQ distinguishes a residence declaration from a **separate TARI** declaration. Do not label TARI as a prerequisite for the change-of-residence filing without explicit reviewed evidence.
- Household-aggregation consent is relevant to a different branch; exclude that branch rather than extrapolating its requirements to an individual move.
- The app's first output should be a **reviewable preparation summary and verified handoff**. Do not invent an official ANPR PDF/form or imply that a generated JSON document can be submitted.

## Hard unanswered questions before activating one real ruleset

1. Precisely which ANPR fields must be completed for this user and housing arrangement, and which can be left blank?
2. Which supporting uploads, if any, are mandatory versus optional or conditional, and what exact current authoritative text supports that distinction?
3. Do rental, owner, sublet and hospitality arrangements require different declarations or documents? Narrow further to one arrangement if evidence remains uncertain.
4. Which page/version is the official primary handoff target, and what user-facing preconditions (SPID/CIE) should be displayed?
5. Are citations, snapshots, review dates and passage hashes sufficient to bind every operative rule to a current source?

## Required human decision

A designated authorized reviewer must confirm sources and scenario completeness, approve the exact active source versions and rule catalog, and sign the catalog using the project's existing offline reviewer process. Until then:

- Keep `backend/app/rules/catalog.json` pending review.
- Keep the `/preparation` Preview environment synthetic-only.
- Preserve `blocked` for any unapproved real checklist, package or official-handoff action.
- Test the completed route, out-of-scope cases, missing information and source revocation before release.

**Engineering follow-up:** integrate the approved ruleset into the guided intake and the existing deterministic evaluator; then run the real Preview end-to-end test with synthetic accounts and documents before requesting public beta approval.
