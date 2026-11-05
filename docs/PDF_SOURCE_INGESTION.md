# Official Milan PDF ingestion — safe manual source workflow

**Status:** Code support added in PR #15; original official PDF bytes have **not**
been acquired, ingested, approved or released. The 15 source registry records
are still unapproved candidates on isolated Neon staging. Production is
unchanged.

## What the importer now supports

- Original **UTF-8 HTML** and **PDF** source bytes, recorded unchanged in
  `knowledge_source_snapshots.raw_body` with SHA-256 source version binding.
- Media-aware deterministic extraction (`html-v1`, `pdf-v1`); PDF passages
  indicate **Page N**, with text offsets and individual SHA-256 hashes.
- An individual registered HTTPS source URL, strict host allowlist, no
  redirects, no proxies, no crawling and no HTTP 403 bypass.
- Maximum HTML input **512 KiB**; maximum PDF input **4 MiB**, **20 pages**,
  **250,000 extracted characters** and **300 passages**.
- Rejects malformed, encrypted, textless/image-only, unbounded or incorrectly
  typed source files. PDFs whose tables, small print or checkboxes are
  inaccurately rendered require manual review even when text extraction works.
- Human-review, audit, latest-revision, citation and tamper checks apply
  identically to both formats. Import only creates `pending_review` versions.
- Tests generate synthetic PDF files; no test fixture is authentic legal
  evidence. None are inserted into Neon outside isolated test transactions.

## Three additional original-document leads

These URL entries are registered as `official_document` candidates, **not**
validated as current approved versions:

1. [Dichiarazione di residenza — Allegato 1](https://www.comune.milano.it/documents/20126/526597/dichiarazione%2Bdi%2Bresidenza.pdf/cb7c0558-d61b-1968-7143-b549f0ab337d)
2. [Documentazione non UE — Allegato A](https://www.comune.milano.it/documents/20126/526418/documentazione_cittadini_extra_u.e2.pdf/ba348f98-86db-faaf-7a96-852530d4be73)
3. [Documentazione UE — Allegato B](https://www.comune.milano.it/documents/20126/526418/documentazione_per_cittadini_u.e..pdf/59339837-24ec-09ac-3352-0bd9d9c97599)

Indexing these links does **not** establish that they are the latest versions or
that their applicability has been legally reviewed. They are historic
municipal document leads. If a browser redirects to a different host or the
PDF looks outdated, stop and verify the canonical official document before
using it. The existing importer refuses redirects intentionally.

## Authorized acquisition on a local machine

1. Open the official source's page in a normal browser, check publication
   date, official publisher, reuse terms and scope. Obtain a permitted
   original PDF download. Do not edit, OCR, reprint or recreate it before
   import. If it is blocked, stop and use a permitted government channel.
2. Install dependencies locally from `backend/`:

   ```bash
   python -m pip install -e '.[dev]'
   ```

3. Test original byte extraction **without a database connection**:

   ```bash
   python -m app.knowledge.ingest_source \
     --source-id milano-residence-form-allegato-1 \
     --file /absolute/path/to/original.pdf
   ```

   This prints the original source SHA-256 and extracted passage count. It
   writes no database state.

4. Set `DATABASE_URL` **privately** to the isolated Neon staging branch,
   never production. Do not paste passwords into ChatGPT, commit them or
   include them in terminal transcripts.
5. After inspecting the actual PDF and its extracted text, run the same
   command with `--apply`. This creates a new **pending_review** revision,
   not a trusted or approved official document.
6. Independently compare every critical condition, table, footnote and
   page layout with the PDF. Only an authorized human reviewer may approve the
   exact hash-bound snapshot. Keep the review API disabled elsewhere.
7. Confirm citation resolution, jurisdiction filters, revocation and source
   change behavior before enabling any user-facing LangChain answer.

## Known limitations

- The current execution environment could not download the official Milan
  HTML/PDF originals: the sites rejected automated access, and alternate
  download attempts failed. This is an **external acquisition blocker**, not
  a database migration issue.
- Text extraction cannot certify the meaning of visual page structure,
  fillable fields, scanned text, diagrams or multi-column layouts. Such PDFs
  may need a separately reviewed workflow.
- The source URL, PDF revision, language and applicability must be manually
  verified; a legitimate original downloaded elsewhere is not automatically
  current or reusable.
- A pass in the synthetic test suite is not evidence of real-world government
  document completeness or legal advice quality.
- No LangChain RAG or embeddings are enabled by this work.
