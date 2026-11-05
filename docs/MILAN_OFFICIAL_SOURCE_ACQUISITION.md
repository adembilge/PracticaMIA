# Milan official-source acquisition inventory — 5 November 2026

**Status: SOURCE METADATA ONLY. Not ingested or approved.**
**Procedure:** selected changes of registered residence (*cambio di residenza*)
within Milano or to Milano from another Italian municipality. This inventory
does **not** certify that the municipality's requirements have been exhaustively
verified for every household, nationality, housing title or edge case.

## Outcome of the official-source review

The municipal service portal and its official support center expose useful
source titles, URLs and search-indexed guidance. Direct page acquisition through
the available retrieval service failed with **HTTP 403**. The search index can
help discover and triage pages, but **cannot be treated as an original HTML
snapshot or evidence of successful ingestion**.

Neon staging `staging-knowledge-0003-0006-2026-11-05` now has **17**
candidate source records, up from four. All remain `candidate`, with no active
version. The database has **zero** source versions, raw HTML/PDF snapshots,
extracted passages and approval events. Production remains on Alembic
`20261104_0002` without the knowledge tables.

The thirteen new source records (ten service/FAQ pages and three PDF leads) are version-controlled in
`backend/app/knowledge/candidate_sources.json`. The existing four records
are unchanged. Candidate metadata is *not* trusted evidence; only
reviewed, hash-bound snapshots can enter approved retrieval.

## Source inventory

Every URL in the table is published under a Comune di Milano domain and
was corroborated through the official site's indexed results on 5 November
2026. Content and applicability require independent original-page review.

| Source ID | Official page | Topic / why it matters |
| --- | --- | --- |
| `milano-residence-change` | [Cambio di residenza](https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza) | Scope, filing channel, declaration timing and initial process |
| `milano-residence-faq` | [Richiesta/cambio residenza — FAQ](https://servizicrm.comune.milano.it/centro-supporto/KA-00330/) | General application FAQ; canonical path and current wording require live verification |
| `milano-italian-residence-change` | [Italian residents moving within Italy](https://servizicrm.comune.milano.it/centro-supporto/KA-00371/) | Existing Italian residents, in-person delegation and household aggregation |
| `milano-foreign-resident-change` | [Foreign residents already in Italy](https://servizicrm.comune.milano.it/centro-supporto/KA-00597/Cambio-residenza-per-stranieri-gia-in-Italia) | Resident foreign citizens changing address or municipality |
| `milano-foreign-rental-documents` | [Foreign tenants: lease evidence](https://servizicrm.comune.milano.it/centro-supporto/KA-00329/Residenza-stranieri-in-affitto-documenti-immobile) | Rental agreement, registration receipt as applicable; public-housing exception |
| `milano-hospitality-consent` | [Guests: assenso all'ospitalità](https://servizicrm.comune.milano.it/centro-supporto/KA-00367/Residenza-per-italiani-ospiti-documenti-immobile) | Consent from tenant or owner for an applicant staying as a guest |
| `milano-free-loan-home` | [Comodato gratuito](https://servizicrm.comune.milano.it/centro-supporto/KA-00428/Residenza-in-comodato-gratuito-documenti-immobile) | Written or verbal free-use arrangements, conditional evidence |
| `milano-foreign-homeowner` | [Foreign homeowners: property deed](https://servizicrm.comune.milano.it/centro-supporto/KA-00429/Residenza-stranieri-proprietari-documenti-immobile) | Document proving ownership |
| `milano-valid-residence-permit` | [Valid residence permit](https://servizicrm.comune.milano.it/centro-supporto/KA-00598/) | Foreign citizens with current permits; identity and residency documentation |
| `milano-renewing-residence-permit` | [Residence permit under renewal](https://servizicrm.comune.milano.it/centro-supporto/KA-00370/Residenza-con-permesso-di-soggiorno-in-rinnovo) | Expired permit and evidence of renewal; special qualification |
| `milano-eu-not-working` | [EU citizen not working](https://servizicrm.comune.milano.it/centro-supporto/KA-00491/) | Conditional identity, economic-resources and healthcare coverage evidence |
| `milano-residence-application-status` | [Check the application status](https://servizicrm.comune.milano.it/centro-supporto/KA-00325/Verifica-stato-pratica-di-residenza) | Official status-check route, not proof of approval |

### Research findings requiring human legal and procedural review

- **Procedure:** The [main service page](https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza)
  distinguishes moving within Milan or from another Italian municipality from
  arrivals from abroad. It describes the ANPR identity channel, the 20-day
  communication window, initial registration and subsequent checks.
- **In-person household changes:** The [Italian](https://servizicrm.comune.milano.it/centro-supporto/KA-00371/)
  and [already-resident foreign](https://servizicrm.comune.milano.it/centro-supporto/KA-00597/Cambio-residenza-per-stranieri-gia-in-Italia)
  FAQs mention adult household members, delegation when a member cannot attend
  and consent if joining an existing registered household.
- **Housing evidence varies by occupancy:** A [foreign tenant's FAQ](https://servizicrm.comune.milano.it/centro-supporto/KA-00329/Residenza-stranieri-in-affitto-documenti-immobile)
  mentions a lease and any applicable registration receipt;
  [guest](https://servizicrm.comune.milano.it/centro-supporto/KA-00367/Residenza-per-italiani-ospiti-documenti-immobile),
  [free-use](https://servizicrm.comune.milano.it/centro-supporto/KA-00428/Residenza-in-comodato-gratuito-documenti-immobile)
  and [ownership](https://servizicrm.comune.milano.it/centro-supporto/KA-00429/Residenza-stranieri-proprietari-documenti-immobile)
  arrangements have different supporting materials. Do not apply the
  foreign-tenant list universally to Italian applicants.
- **Foreign-document requirements vary:** The
  [valid-permit](https://servizicrm.comune.milano.it/centro-supporto/KA-00598/)
  and [renewal](https://servizicrm.comune.milano.it/centro-supporto/KA-00370/Residenza-con-permesso-di-soggiorno-in-rinnovo)
  FAQs distinguish current permits from renewal cases. They also distinguish
  family-status certificates used for registering family relationships from
  mandatory documents. Do not flatten these into one universal checklist.
- **EU non-workers:** The [conditional FAQ](https://servizicrm.comune.milano.it/centro-supporto/KA-00491/)
  discusses sufficient resources and health coverage. Whether this applies
  to a person **already resident in Italy and merely changing address**
  must be separately established before the rule engine uses it.
- **TARI is a related but separate obligation:** The
  [domestic occupation service](https://www.comune.milano.it/servizi/tributi/tari-dichiarazione-di-occupazione-di-appartamenti-e-immobili)
  and [occupants-variation service](https://www.comune.milano.it/servizi/dichiarazione-tari-occupanti)
  require distinct procedural review. These were **not** added to the
  `milan_residence_change` source registry, to avoid mixing tax requirements
  into residence-application retrieval.
- **Foreign arrivals from abroad are outside this MVP's approved pathway.**
  The municipality uses a
  [separate service](https://www.comune.milano.it/servizi/anagrafe/richiesta-di-residenza-per-persone-straniere-provenienti-dall-estero)
  with a separate [modulistica page](https://www.comune.milano.it/servizi/anagrafe/richiesta-di-residenza-per-persone-straniere-provenienti-dall-estero/modulistica-richiesta-di-residenza-per-persone-straniere-provenienti-dall-estero).
  Do not merge its checklist into the within-Italy MVP.

## Official form/PDF leads — not imported

The municipality also publishes document links for
[Dichiarazione di residenza (Allegato 1)](https://www.comune.milano.it/documents/20126/526597/dichiarazione%2Bdi%2Bresidenza.pdf/cb7c0558-d61b-1968-7143-b549f0ab337d),
[non-EU document list (Allegato A)](https://www.comune.milano.it/documents/20126/526418/documentazione_cittadini_extra_u.e2.pdf/ba348f98-86db-faaf-7a96-852530d4be73),
and [EU document list (Allegato B)](https://www.comune.milano.it/documents/20126/526418/documentazione_per_cittadini_u.e..pdf/59339837-24ec-09ac-3352-0bd9d9c97599).
**These are leads, not current approved templates.** The exact original PDF
bytes, canonical redirect targets, applicable revisions and currency have
not been validated. Some web-indexed variants contain historical figures,
so avoid deriving current thresholds from them. The ingestion pipeline
now supports bounded original-PDF ingestion, but original bytes remain
unavailable in this environment. See [PDF Source Ingestion](PDF_SOURCE_INGESTION.md).

Two additional conditional FAQ candidates were identified: [documents for a minor's residence change](https://servizicrm.comune.milano.it/centro-supporto/KA-00434/Documenti-necessari-per-cambio-residenza-minori) and [a foreign worker staying with a property owner/tenant](https://servizicrm.comune.milano.it/centro-supporto/KA-00594/). They remain unapproved. An additional [download queue](OFFICIAL_DOCUMENT_DOWNLOAD_QUEUE.md) tracks landlord consent, two minor-related municipal forms, and the national ANPR guide. These are research leads, not stored documents.

## Safe acquisition and review procedure

1. In a normal browser, inspect an official candidate URL, identify the
   canonical page and any date/version notices, and check its reuse terms.
2. Obtain permitted *original* HTML or PDF bytes. Do **not** reconstruct content
   from a search preview, translation, OCR or AI-generated summary.
3. Verify source identity, redirects, declared media type and the extraction
   against the live official display. An inaccessible page stays a candidate.
4. On a local machine with a credential for **the isolated staging branch**,
   run a dry-run from `backend/`:
   `python -m app.knowledge.ingest_source --source-id <id> --file <original.html-or.pdf>`.
   Only after inspection run the same command with `--apply`.
5. Record exact SHA-256, the pending version, source URL and passages.
   Compare complex lists, tables, footnotes, and any caveats manually.
6. A separately authenticated, allowlisted human reviewer must inspect
   and approve the exact hash-bound revision; do not autoapprove.
7. Verify authenticated approved-only search, exact citation resolution,
   source-change invalidation and revocation. Enable no production
   personalized requirements until source/rule quality gates are satisfied.

Production migration, reviewer privileges, LangChain answer generation and
official source approval are **separate tasks**. The catalog alone does not
make PracticaMIA's knowledge engine ready for user-facing advice.
