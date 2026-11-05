# Browser-rendered official pages: evidence storage and review

**Purpose.** Retain official municipal article text that is visible in the
operator's connected browser when the official website rejects automated
HTTP clients. This is a different acquisition method from original-response
HTML. It is permissible to review the publisher's actual page text, but
the capture is **not** a cryptographically verified original HTTP response.

## How the system distinguishes sources

| Field | HTTP original | Browser-rendered evidence |
| --- | --- | --- |
| snapshot media type | text/html or application/pdf | text/plain |
| capture_method | original_http | browser_rendered_text |
| observed_url | null | Browser page's official URL, without tracking query parameters |
| observed_title | null | Actual browser page title |
| observed_last_updated | null | DD/MM/YYYY date stated on the displayed page |
| original bytes stored | HTTP body | Visible municipal article text only |
| reviewer approval | Required | Required, with explicit acquisition-method awareness |

Browser captures are bound to the existing source registry and exact article
code (e.g. KA-00330). No third-party host, wrong article code, redirected
unreviewed URL, fake HTML, screenshots, PDFs as text or missing update dates
are allowed. The body and every passage receive SHA-256 hashes, and their
immutable version metadata participates in later integrity checks.

**Neither capture nor ingestion grants approval.** A source is searchable by
RAG only once a human reviewer signs off on its exact pending version, and
the existing approval audit and per-query hash integrity gates pass.

## JSON capture schema

Use a directory with one JSON file named `<registered-source-id>.json`:

```json
{
  "source_id": "milano-residence-faq",
  "capture_method": "browser_rendered_text",
  "captured_url": "https://servizicrm.comune.milano.it/centro-supporto/KA-00330/Richiestacambio-residenza-come-procedere",
  "page_title": "Come chiedere/cambiare residenza?",
  "last_updated": "23/07/2026",
  "article_text": "Exact Italian body text displayed in the official browser page."
}
```

The `article_text` must be from the actual publisher page, not an LLM
summary, navigation elements, advertising, feedback widgets, user profile
data, article recommendations, or reconstructed server HTML. Linked official
forms remain separate resources and do not become approved merely because
an article references them.

### Preview and import

From `backend/`:

```sh
python -m app.knowledge.browser_capture_import --directory ./captures
```

If validation succeeds, an operator may explicitly import into the **isolated
Neon staging branch**, after applying Alembic migration `20261105_0009`:

```sh
export PRACTICAMIA_KNOWLEDGE_TARGET=staging
# DATABASE_URL must point to isolated staging. Keep secrets out of source control.
python -m app.knowledge.browser_capture_import --directory ./captures --apply
```

The importer does not approve or embed. It stores
`KnowledgeSourceVersion.status=pending_review`, with source hashes, exact
passage spans and original browser evidence metadata. If a changed capture
replaces an active version, the previous approval is invalidated by the
existing ingestion service.

## Review checklist before activating a browser capture

- Confirm the official publisher domain and exact article ID against the
  source registry; investigate shortened vs canonical URLs.
- Confirm the displayed Italian title, date and full **substantive** article
  text, including exception clauses and negations.
- Check for contradictions with newer municipal guidance and broader ANPR
  rules, especially changes since 2025.
- Record the reviewer, date, precise hash, reasons and capture limitation.
- Approve only with the existing authenticated review workflow, then verify
  citation spans on representative questions. Require re-review on page
  changes; do not assume older FAQ is current legal advice.

Original HTTP acquisition can replace browser text later; the provenance
of each historical version remains distinct.

The two previously observed pages `milano-residence-change` and
`milano-residence-faq` were **not open** in the browser when the other
12 capture records were prepared. A prior research summary is not a full
article capture; neither should be manufactured from memory.

## Authenticated mobile review

A preview-only, mobile-friendly [batch review screen](MOBILE_BROWSER_SOURCE_REVIEW.md)
can approve inspected browser-rendered source versions with their exact hashes
through a verified allowlisted Auth0 reviewer. The older historical PDF is
explicitly excluded; no database direct-approval shortcuts are permitted.
