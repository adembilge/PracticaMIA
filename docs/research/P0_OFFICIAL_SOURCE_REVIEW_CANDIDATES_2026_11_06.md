# Official Milan evidence candidates for P0 human review

**Research snapshot: 6 November 2026.** This dossier records publicly visible pages to help a designated human reviewer determine legal applicability. It is **not** an approved source bundle, does not supply raw source snapshots or hashes, and does not activate rules, document requirements, deadlines or links in PracticaMIA.

## Official pages discovered or rechecked

| Candidate | Current visible indication | Review question |
| --- | --- | --- |
| [Comune di Milano — Cambio di residenza](https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza) | Service description addresses moves within Milano/another Italian Comune, with separate handling of people arriving from abroad; official service links to ANPR and requires SPID or CIE for access | Confirm exact supported individual scenarios, eligibility exclusions and live ANPR handoff |
| [Comune support — Come chiedere/cambiare residenza?](https://servizicrm.comune.milano.it/centro-supporto/KA-00330/Richiestacambio-residenza-come-procedere) | Dated 23 July 2026; distinguishes residents already in Italy from foreign nationals coming from abroad; mentions household/stay exceptions | Decide supported branch, deadline conditions, and clearly exclude unsupported household aggregation |
| [Comune support — Italian citizens changing residence](https://servizicrm.comune.milano.it/centro-supporto/KA-00371/) | Dated 23 July 2026; directs people moving from another municipality or within Milano to ANPR | Check if a narrowly supported single-adult scenario can be independently attested |
| [Comune support — Foreign citizens already resident in Italy](https://servizicrm.comune.milano.it/centro-supporto/KA-00597/Cambio-residenza-per-stranieri-gia-in-Italia) | Dated 1 July 2026; addresses people already resident in Italy via online service | Keep nationality-specific/registration preconditions out of scope until independently reviewed |
| [Comune support — Request status](https://servizicrm.comune.milano.it/centro-supporto/KA-00325/Verifica-stato-pratica-di-residenza) | Dated 13 August 2026; directs users to municipal Fascicolo del Cittadino | Do not equate visible record updates, self-report or portal activity with government confirmation |

## Proposed first scenario, **not approved**

A **single adult already registered in Italy** changing registered residence to an address within Milano, with no additional household aggregation, no special proxy/consent arrangement and no separate immigration procedure. This is a design candidate only. Do not infer nationality, permit eligibility, property title or mandatory attachments from this proposal; the reviewer must define and document them from current primary sources.

## Evidence required to activate any rule

1. Retrieve the authentic public official page or human-authorized browser capture with canonical URL, observed title, publication/update date, original bytes where available, and precise passage offsets. Do not substitute search snippets.
2. Link the source to the existing versioned registry and run the existing provenance checksum validations.
3. Have an authorized human reviewer resolve conflicts, currentness and conditions; approve each precise version through the controlled review workflow. An older Allegato A PDF remains excluded unless separately validated for current use.
4. Create a complete, narrow `backend/app/rules/catalog.json` with exact citation IDs, route conditions, document types and verified template instructions. No inferred requirements.
5. Obtain an **external Ed25519 reviewer signature** over the catalog's canonical JSON excluding `review_signature`, and deploy only the 32-byte public verification key as `PREPARATION_RULE_REVIEW_PUBLIC_KEY`. The signing private key must never be placed in the repository, CI logs or Vercel environment.
6. Have a second reviewer independently test all positive, negative, missing-information and revoked-source scenarios, including complex household and arrival-from-abroad cases.
7. Only after browser, privacy, source and deployment gates should operator consider the controlled UI safe for non-synthetic use. This PR does not enable it in production.

## Blocking unknowns

- Exact validity of each document requirement and eligibility branch.
- Whether additional municipal PDF forms or specific user documents are mandatory in the selected narrow route.
- Whether sourced official destinations cover the complete accepted handoff and how government confirmation should be represented.
- Data retention, deletion, malware-screening and legal/provider assessment required before handling real uploads.

Existing staging knowledge snapshots and their approval status must be checked against this dossier. Do not fabricate hashes, source version IDs, acceptance records or real government responses.
