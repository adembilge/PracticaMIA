# Official Milan residence-source acquisition audit — 2026-11-05

**Outcome: no original HTML files acquired.** GitHub Actions performed one
unmodified GET request against each of the 14 registered official HTML/FAQ
sources, with no proxies, no redirects, no retries, and no login bypasses.
Every source returned **HTTP 403 Forbidden**.

- [Full auditable job log](https://github.com/adembilge/PracticaMIA/actions/runs/42102967940)
- [GitHub Actions acquisition artifact](https://github.com/adembilge/PracticaMIA/actions/runs/42102967940#artifacts) contains **only a JSON manifest** and an empty originals directory.
- The runner did not change Neon, approve documents, generate embeddings,
  configure an LLM, or publish government advice.
- The relevant status is *official source identified by its registered URL,
  raw original inaccessible from this runner*. Indexed search excerpts are
  not permissible original-source data.

## All 14 sources attempted

Each link below is the exact URL currently registered in
`backend/app/knowledge/candidate_sources.json`. The HTTP result was 403
for **all** of them. Dates are from indexed official FAQ/service pages and
are informational only, **not proof of original-byte capture**.

| Registered source | Official URL | HTTP result | Indexed last update |
| --- | --- | --- | --- |
| milano-residence-change | https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza | 403 | 2026-06-16 |
| milano-residence-faq | https://servizicrm.comune.milano.it/centro-supporto/KA-00330/ | 403 | 2026-07-23 |
| milano-foreign-rental-documents | https://servizicrm.comune.milano.it/centro-supporto/KA-00329/Residenza-stranieri-in-affitto-documenti-immobile | 403 | 2025-09-26 |
| milano-foreign-resident-change | https://servizicrm.comune.milano.it/centro-supporto/KA-00597/Cambio-residenza-per-stranieri-gia-in-Italia | 403 | 2026-07-01 |
| milano-italian-residence-change | https://servizicrm.comune.milano.it/centro-supporto/KA-00371/ | 403 | 2026-07-23 |
| milano-hospitality-consent | https://servizicrm.comune.milano.it/centro-supporto/KA-00367/Residenza-per-italiani-ospiti-documenti-immobile | 403 | 2026-07-23 |
| milano-free-loan-home | https://servizicrm.comune.milano.it/centro-supporto/KA-00428/Residenza-in-comodato-gratuito-documenti-immobile | 403 | 2025-09-26 |
| milano-foreign-homeowner | https://servizicrm.comune.milano.it/centro-supporto/KA-00429/Residenza-stranieri-proprietari-documenti-immobile | 403 | 2025-09-18 |
| milano-valid-residence-permit | https://servizicrm.comune.milano.it/centro-supporto/KA-00598/ | 403 | 2025-08-11 |
| milano-renewing-residence-permit | https://servizicrm.comune.milano.it/centro-supporto/KA-00370/Residenza-con-permesso-di-soggiorno-in-rinnovo | 403 | 2025-07-01 |
| milano-eu-not-working | https://servizicrm.comune.milano.it/centro-supporto/KA-00491/ | 403 | 2025-09-23 |
| milano-residence-application-status | https://servizicrm.comune.milano.it/centro-supporto/KA-00325/Verifica-stato-pratica-di-residenza | 403 | 2026-08-13 |
| milano-residence-minor-documents | https://servizicrm.comune.milano.it/centro-supporto/KA-00434/Documenti-necessari-per-cambio-residenza-minori | 403 | 2025-08-12 |
| milano-foreign-live-in-worker | https://servizicrm.comune.milano.it/centro-supporto/KA-00594/ | 403 | 2025-07-02 |

## Canonical URL candidates requiring human verification

Official search indexing indicates that the municipality has fuller,
human-readable paths for some registered shorthand links. **Do not
silently update URLs** in either the curated registry or the database:
review the exact final URL in a normal browser and compare it with the
registered source first. Potential candidates:

- `KA-00330`: https://servizicrm.comune.milano.it/centro-supporto/KA-00330/Richiestacambio-residenza-come-procedere
- `KA-00594`: https://servizicrm.comune.milano.it/centro-supporto/KA-00594/Residenza-stranieri-lavoratori-domestici-documenti
- `KA-00598`: https://servizicrm.comune.milano.it/centro-supporto/KA-00598/Documenti-per-residenza-con-permesso-di-soggiorno-valido

A canonical URL being indexed does not mean our server could retrieve
the original or that the page is approved RAG evidence.

## Two old PDF links return 'Pagina non trovata' for the operator

The user reports **Pagina non trovata** for the registered **Allegato 1**
and **Allegato B** direct document URLs. Search indexes may still contain
historical PDF content, which is not proof that the links are live or
administratively current.

Use the official 2026 forms index to find current replacement forms:
https://www.comune.milano.it/servizi/anagrafe/richiesta-di-residenza-per-persone-straniere-provenienti-dall-estero/modulistica-richiesta-di-residenza-per-persone-straniere-provenienti-dall-estero

That page is dated 2026-06-16 and explicitly lists the EU and non-EU
document lists and other forms. It is **not** equivalent to the old
Allegato 1 or Allegato B PDF until a reviewer establishes which exact
attachments replaced which. The one original Allegato A already stored
in staging remains historical and `pending_review`.

## Safe operator route for original HTML

Try the collector from the user's own permitted network (without
bypassing any web access controls):

```sh
cd backend
python -m app.knowledge.audit_web_sources --output-dir ./official-audit
```

The collector writes `official-audit/manifest.json` plus any exact
original HTTP-200 HTML bytes to `official-audit/originals/`.
If any URL returns 403, it records `unavailable` and does not save
substitute content. Do **not** commit cookies, authenticated session
transcripts, HAR files, screenshots, AI-reconstructed pages or personal data
as source originals.

Before importing, inspect the original and compare title, official host,
date and current municipal applicability. Then follow
[OFFICIAL_SOURCE_INTAKE.md](OFFICIAL_SOURCE_INTAKE.md) to import as
`pending_review` into the isolated Neon staging branch only.

The trusted RAG collection stays empty until actual, validated original
files are imported and a human reviewer approves the precise version.
