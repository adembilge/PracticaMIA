# Official source acquisition — operator runbook

**Status:** Exact-source intake tooling, not an automatically approved
government knowledge base. A source URL is not equivalent to an ingested,
reviewed, current document.

## Last automated acquisition attempt (5 November 2026)

A controlled GitHub Actions job attempted all 14 registered HTML URLs
exactly once. **All 14 returned HTTP 403**, so none were imported.
The result and per-source URLs are recorded in
[the official HTML access audit](OFFICIAL_HTML_ACCESS_AUDIT_2026_11_05.md).

When run from an authorized local network, the same byte-preserving collector is:

```sh
python -m app.knowledge.audit_web_sources --output-dir ./official-audit
```

Only files that pass original-response and extraction checks may be used as
input to the existing `batch_import` workflow. A 403 means no source
file was obtained, not that a snapshot should be reconstructed.

## Current constraints

At the time of this change, staging contains 17 registered source URLs,
one original historical Allegato A PDF in `pending_review`, three extracted
passages, **zero approved versions**, and **zero embeddings**. The historical
PDF must not be approved just to enable the assistant.

Comune di Milano official website and support FAQ pages include:
- [Cambio di residenza service](https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza) (page last updated 16 June 2026)
- [Come chiedere/cambiare residenza](https://servizicrm.comune.milano.it/centro-supporto/KA-00330/Richiestacambio-residenza-come-procedere) (23 July 2026)
- [Verifica stato pratica](https://servizicrm.comune.milano.it/centro-supporto/KA-00325/Verifica-stato-pratica-di-residenza) (13 August 2026)

The registry uses some shorter paths such as `/KA-00330/`. These might
redirect to a canonical URL. **Never silently follow redirects:** inspect
the destination, then propose any curated URL change separately. Registered
URLs and content are deliberately reviewed independently.

## Browser-visible official content

If the official website remains inaccessible to automated HTTP fetches but
is readable in a normal browser, its substantive **rendered Italian article**
can be retained using the separately labeled
[browser capture review pipeline](BROWSER_CAPTURE_EVIDENCE.md).
It is never stored as original HTTP HTML or automatically approved.

## 1. View the acquisition queue

Run from `backend/`:

```sh
# Without DATABASE_URL: all 17 registered URLs, no database status
python -m app.knowledge.batch_import --queue

# With DATABASE_URL pointing to the isolated Neon staging branch:
python -m app.knowledge.batch_import --queue > knowledge-queue.json
```

The JSON includes the exact registered source ID and URL, expected file
extension, latest stored revision and status, and suggested next action.
It does not fetch, store, embed, or approve source material.

## 2. Obtain genuine original bytes

Preferred: when the official host permits requests, use the existing
single-source `--fetch` importer to retrieve an exact allowlisted
registered URL. It enforces HTTPS, original response bytes, MIME and size
limits, no redirects and HTTP 200. Blocks (403, 429, DNS or redirects) are
explicit failures, not a license to bypass access restrictions.

```sh
python -m app.knowledge.ingest_source \
  --source-id milano-residence-change --fetch
```

That example is a **dry-run**. Do not add `--apply` until the original
is verified and the target is confirmed isolated staging.

For manual originals supplied by an authorized operator, name each file
exactly `<registered-source-id>.pdf` for an official PDF or
`<registered-source-id>.html` for an HTML source. Preserve actual raw
official-server bytes, not text copied from search results, scraped snippets,
rewritten browser saves, machine-generated HTML or a rendered page screenshot.
Do not put user-submitted personal data in this directory.

The project cannot retrieve blocked municipal resources in the present
execution environment (DNS failures, prior HTTP 403). Operator network
access may differ. **Do not import a reconstructed substitute.**

## 3. Validate a batch without database changes

```sh
python -m app.knowledge.batch_import --directory ./official-originals
```

The default dry-run checks the exact curated IDs, expected source media
types, original size and extractability, SHA-256 and passage counts.
Unexpected filenames, symlinks, duplicates, corrupt PDFs, scanned-only
PDFs, oversized content and missing source IDs are rejected.

Keep `official-originals/` outside Git and the production frontend. Do
not commit originals without a separate public-domain/rights review.

## 4. Import only to isolated staging as pending review

Set your DB connection securely through your own local secret manager.
Do not paste connection strings or provider secrets in chat or commit them.

```sh
export PRACTICAMIA_KNOWLEDGE_TARGET=staging
# DATABASE_URL must reference the isolated Neon staging database
python -m app.knowledge.batch_import \
  --directory ./official-originals --apply
```

The CLI requires the explicit staging designation, rejects Vercel
production, requires PostgreSQL schema revision `20261105_0009`,
requires registered DB URLs to match the curated catalogue and processes
all validated originals inside **one transaction**. No partial import
is retained if any source fails. A changed version is marked
`pending_review` and invalidates any prior active approval; an unchanged
version is idempotent. No external LLM calls or embeddings are created.

The explicit environment designation and schema check are defensive gates;
operators must still verify the actual Neon branch in the console. A
migrated production database could have the same schema version.

## 5. Human evidence review

For each imported version:

1. Open the original URL and compare the saved source body/hash, heading,
   publisher, publication date and official updates against the municipal
   service pages.
2. Check whether the document remains applicable on the review date,
   including any superseded procedures or conflicting appendices.
3. Record review rationale through the existing authenticated review
   workflow and approve the **specific content SHA-256 and source version**.
   Otherwise keep it `pending_review` or revoke it.
4. Only after approval, produce embeddings using an evaluated, versioned
   embedding model and test citations on representative Italian and English
   queries.

Import success is **not evidence of current legal validity**.

## Useful SQL for review (staging only)

```sql
SELECT s.id, s.title, s.official_url,
       COALESCE(v.status, 'not_imported') AS latest_status,
       v.revision
FROM knowledge_sources s
LEFT JOIN LATERAL (
    SELECT status, revision
    FROM knowledge_source_versions
    WHERE source_id = s.id
    ORDER BY revision DESC
    LIMIT 1
) v ON TRUE
ORDER BY s.id;
```

No automatic fetching, approval, production schema migration, user-data
submission, or model configuration is performed by this milestone.
