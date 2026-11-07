# First Milan route — reviewer-ready field and rules package (7 November 2026)

**Status: proposed; not approved.** This does **not** change the active catalog or confer municipal/legal approval. Production routes and real-document handling remain disabled.

## Exact scope

One Italian adult already recorded as resident in Italy, moving individually to Comune di Milano (not joining an existing household), as holder of a **registered private rental agreement**. The authenticated synthetic Preview now asks this fifth housing-basis question. Owner, hosted guest, public-housing, nonregistered lease and family-joining situations are outside this FIRST product route, not legally ineligible.

## First-party evidence and what it actually establishes

| Institution | Exact official resource | Confirmed direction | Evidence state in PracticaMIA |
| --- | --- | --- | --- |
| Comune di Milano | https://servizicrm.comune.milano.it/centro-supporto/KA-00371/ (updated 23 July 2026) | Residence-change notification within 20 days using ANPR, household-aggregation consent in the separate branch, and a distinct TARI declaration | Three independently reviewed excerpts already stored: `e139e910-3a89-4994-b450-b5107d8db7dd:0000`, `:0003`, `:0005` |
| Comune di Milano | https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza | Eligible service categories, SPID/CIE access, registration followed by municipal checks | Candidate official page; **not approved in the project registry** |
| Ministero dell'Interno / ANPR | https://sc.anpr.interno.it/serviziCittadino/dist/docs/guida_compilazione_cambio_residenza.pdf | Section 1.1.1 Famiglia; 1.1.2 Residenza; 1.1.3 Immobile; 1.1.4 Allegati; 1.1.5 Dati aggiuntivi; 1.1.6 Riepilogo | Candidate PDF; original bytes, publication/currentness and individual passages **not yet independently approved in the project registry** |

The current official ANPR guide text (version date not established) explicitly describes destination province, municipality, street type/name, civic number and CAP. For a registered tenant it describes property-title option 2 and the registration office municipality, date and number. It indicates driving licence and vehicle yes/no entries in the family section; some additional address components are optional. **Do not claim these are the final 2026 ANPR UI fields until their currentness is checked.**

The guide says supporting attachments are normally optional, while certain other citizen categories have compulsory permits. Consequently, an invented mandatory Italian-renter PDF upload would be misleading. The first product route must support optional supporting evidence and still verify any local conditional exceptions with the authorized reviewer.

Do not apply Milan's separate municipal attachment list for **foreign nationals arriving from abroad** to this already-resident Italian route. That workflow and its uploads are different.

## Exact artifacts for reviewer

1. `requirements/milan-residence-change/italian_individual_registered_rental_candidate_v2.json` — proposed versioned route and municipal citations, **still pending**. It cannot activate the live rules engine.
2. `requirements/milan-residence-change/individual_registered_rental_anpr_field_review_v1.json` — ordered ANPR fields with provisional mandatory/conditional flags, source links and separate nonresident exceptions.
3. `backend/app/preparation/intake.py` — five synthetic eligibility-boundary questions, now including registered rental; excluded choices trigger an out-of-product-scope message.
4. `backend/tests/test_milan_registered_rental_draft.py` — refusal and boundary regression tests.

## Human sign-off checklist

- [ ] Retrieve, timestamp, hash and store the original ANPR citizen guide and the municipal service page, preserving provenance; confirm that the guide describes the *current* user interface.
- [ ] Review and approve each operative source version and exact ANPR passages using the existing authenticated review queue.
- [ ] Check whether registered private tenancy entails any specifically mandatory document uploads under the currently applied ANPR/Milan procedure; distinguish *legal-occupancy evidence data* from *an uploaded contract*.
- [ ] Confirm mandatory vs optional fields, including rent-registration date wording, contact details, family-head relationship, and driver/vehicle flags.
- [ ] Confirm the official ANPR handoff URL, identity requirements, branch, TARI follow-up and exceptions; do not use SPID/CIE credentials inside PracticaMIA.
- [ ] After authoritative coverage is complete, prepare the final rules catalog and request **independent authorized human approval plus Ed25519 signature**. Never copy a private signing key into GitHub, Vercel or model context.
- [ ] Run positive/negative/out-of-scope, data-correction, source-revocation and two-account authenticated browser E2E tests before any real-user launch.

**Do not publish a mandatory checklist from this file until those approvals exist.** The synthetic preparation flow remains useful for testing the entire UX without implying legal completeness.
