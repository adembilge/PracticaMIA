# PracticaMIA — First User Journey

**Version:** 0.1 — 3 November 2026  
**Status:** Draft product design; not an approved administrative ruleset  
**Related research:** `research/milan_residence_change.md`

## 1. User and goal

**Scenario:** One adult already registered as a resident in Milan has moved to a rented apartment at another Milan address. They are not adding household members or joining an existing registered household.

**User's goal:** Understand the correct residence-change process, identify missing information, review relevant evidence and documents, and be ready to complete the official government submission.

**PracticaMIA's job:** Help with preparation and verified guidance — **not** authenticate to, submit through, or approve an ANPR application.

## 2. First end-to-end journey

| Step | What the user does/sees | What PracticaMIA does | Exit condition |
|---|---|---|---|
| 1. Start | Enters: “I moved to a new apartment in Milan.” | Opens a draft case and proposes the residence-change procedure. | User starts a case. |
| 2. Scope check | Answers whether previously registered in Milan, still moving within Milan, applying alone, rental arrangement, and whether joining another household. | Records answers as user-provided; checks whether the case matches **reviewed** supported conditions. | `supported`, `needs_information`, or `unsupported`. |
| 3. Targeted intake | Provides previous/new addresses, move date, relevant applicant category, and any other verified required facts. | Requests only missing information; saves progress and tracks provenance. | Routing facts complete or case paused. |
| 4. Requirements | Reviews a checklist with government source links and any pending items. | Applies approved deterministic rules; retrieves source explanations. | Requirements shown, or explicitly blocked for unreviewed rules. |
| 5. Document review | Uploads a supported document, if required by approved rules; confirms or corrects extracted data. | Extracts fields, checks inconsistencies, and flags uncertainty; never silently confirms OCR. | Critical fields confirmed and mismatches resolved. |
| 6. Preparation review | Sees a case summary, verified checklist, blockers, and official handoff instructions. | Builds a reviewable preparation summary from confirmed facts; asks for user approval. | `submission_ready` **only if** required checks pass. |
| 7. Handoff | Opens the official service and submits personally. | Provides approved ANPR guidance, notes a separate TARI follow-up, and can save user-reported progress. | Handoff provided; no claim of government acceptance. |

**Early prototype shortcut:** Build steps 1–4 first using synthetic cases and a small, reviewed source set. Add document upload and package generation after the core journey is validated.

## 3. Main screen and expected output

One **case workspace** with four sections:

- **Conversation / next question:** A single relevant question or recommended action, plus the explanation.
- **Case facts:** Previous address, new address, move date, applicant/household information, and their source/confirmation states.
- **Requirements checklist:** Required and conditional actions, evidence citations, and incomplete or blocked states.
- **Review / handoff:** A concise preparation summary, open issues, official link, and submission-state disclaimer.

**Expected output for a successful supported case:** a cited procedure summary, personalized checklist, confirmed facts, reviewable preparation package or summary, and verified instructions to submit through ANPR. **Not** a claim that the application was filed or approved.

## 4. Branches to test

| Example | Expected behavior |
|---|---|
| Adult already registered in Milan, moves alone within Milan | Continue **only if** the applicant's documentary branch is reviewed and supported. |
| User cannot confirm prior registration | Ask a focused question; preserve `needs_information`. |
| User arrived from abroad | Mark this workflow unsupported; give a verified official starting point where available. |
| User joins an existing household or includes a minor | Mark unsupported in this initial slice; do not invent consent/document requirements. |
| New address differs from uploaded rental agreement | Show both values, require confirmation/correction, block dependent preparation. |
| Official requirement has no approved source or is stale | Do not generate a mandatory instruction; block and flag for review. |
| User clicks the official submission link | Record handoff, **not** completion or government confirmation. |

## 5. Verified official context vs. design assumptions

**Official context:** Milan says residence/address moves should be declared within **20 days**; its published service directs eligible applicants to ANPR with **SPID or CIE**. Registry entry and subsequent municipal checks are separate from final acceptance. Milan also identifies a related **TARI** declaration. See references below.

**Product assumptions (require approval):** The initial user scenario, intake fields, screen organization, checklist UX, draft case states, and the use of a preparation summary are product design choices. They are **not** a complete inventory of the live ANPR form or all citizenship-specific documentation rules.

**Unresolved before activating real-case rules:** Exact documents and fields by applicant category; whether each rental/registration document is mandatory; how to detect residence and household exceptions; the exact TARI action for an intra-Milan move.

## 6. Acceptance criteria for this design milestone

- [ ] Owner approves the initial user and scope boundary.
- [ ] A complete happy-path journey and unsupported path are understandable without code.
- [ ] Every legal/administrative claim points to an identifiable official source.
- [ ] Missing, contradictory, or unverified inputs do not silently become confirmed facts.
- [ ] The UI separates **prepared**, **user-reported submitted**, and **officially confirmed**.
- [ ] Document requirements remain conditional until reviewed and approved.

## Official references (checked 3 November 2026)

1. Comune di Milano, *Cambio di residenza*: https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza
2. Comune di Milano, *Come chiedere/cambiare residenza?* (updated 23 July 2026): https://servizicrm.comune.milano.it/centro-supporto/KA-00330/Richiestacambio-residenza-come-procedere
3. Comune di Milano, *Cambio residenza per stranieri già in Italia*: https://servizicrm.comune.milano.it/centro-supporto/KA-00597/Cambio-residenza-per-stranieri-gia-in-Italia
4. Comune di Milano, *Documenti immobile per stranieri in affitto*: https://servizicrm.comune.milano.it/centro-supporto/KA-00329/Residenza-stranieri-in-affitto-documenti-immobile

**Next build milestone after review:** Prototype the case workspace and scope-check question flow with synthetic data; then add persistence and approved requirements logic.
