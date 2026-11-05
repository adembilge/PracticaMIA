# Comune di Milano — browser-observed residence guidance (5 November 2026)

**Evidence class: browser-rendered text observed through the user's connected
browser, not an original HTTP response or an approved knowledge snapshot.**
This research note is **not** input to the trusted RAG passage tables. It is
intended to help a human reviewer reconcile an eventual verified original
with the current official procedure.

## Browser access result

Both pages were open and readable in the user's browser. The independent
GitHub-runner HTTP audit returned 403 for all 14 registered webpages, so
browser readability must not be misrepresented as successful original-byte
acquisition. No source records, approvals, embeddings, or production data
were modified during this review.

### 1. Cambio di residenza

- Registry ID: `milano-residence-change`
- Official page: https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza
- Browser page heading: **Cambio di residenza**
- Page's stated last update: **16/06/2026**
- Observed in the user's connected browser on **05/11/2026**.

**Information visible in the page:**

- The described service covers Italian and foreign people moving from
  another Italian municipality or within Milan, and Italian nationals
  returning from abroad who were registered with AIRE.
- Its request link points to the national registry service (ANPR); the
  page indicates SPID or CIE for authentication.
- The move should be declared to the registry office within 20 days.
- The page describes initial registration in two working days and subsequent
  municipal checks of eligibility.
- It separately reminds people moving to update their TARI residential
  occupancy declaration.
- Its legal-effects section describes the declaration date as the start of
  registration's legal effects, subject to municipal verification.
- It links to the distinct service for foreign people **arriving from abroad**.

**Engineering note:** The assistant must not conflate *changing address
within Italy* with *foreign residents newly arriving from abroad*. The latter
is directed to a separate municipal service.

### 2. Come chiedere/cambiare residenza?

- Registry ID: `milano-residence-faq`
- Official full URL visible in the browser:
  https://servizicrm.comune.milano.it/centro-supporto/KA-00330/Richiestacambio-residenza-come-procedere
- Registry previously stored the shorter path ending `/KA-00330/`.
  Compare the canonical destination before editing curated source metadata.
- Browser page heading: **Come chiedere/cambiare residenza?**
- Page's stated last update: **23/07/2026**
- Observed in the user's connected browser on **05/11/2026**.

**Information visible in the page:**

- Italian nationals, AIRE returnees and foreign citizens already residing
  in Italy are directed to apply within 20 days using ANPR online.
- Foreign citizens arriving from abroad are directed to a **dedicated**
  municipal application service.
- When an application is made during an appointment at the registry desk,
  all relevant adult household members must attend.
- An adult unable to attend must authorize the person attending with a
  special proxy form (`procura speciale`).
- When joining an existing household at the same registered address,
  consent (`assenso`) of the already registered person may be needed.
- The page points to municipal-hosted proxy and hospitality consent forms
  and refers people to the Contact Center for additional assistance.

**Engineering note:** Appointment delegation and household aggregation
consent are separate conditional questions and should not automatically
be presented as universal required documents.

## Next evidence acquisition step

The 12 other registered FAQ webpages were not opened in the connected
browser at this review. Their original HTTP contents also remain uncollected.

To ingest official evidence in the current approved-only system:

1. Collect original server-response HTML through an authorized source and
   record its precise URL, response type, time and SHA-256.
2. Confirm that the response matches the current municipal document,
   including the last-updated date and applicability.
3. Import into isolated Neon staging as `pending_review`.
4. Approve only after source-by-source human checks and evaluation.
5. Generate embeddings only from approved versions.

**Do not ingest this Markdown note as if it were an original official source.
Do not infer approval or legal validity merely from browser readability.**
