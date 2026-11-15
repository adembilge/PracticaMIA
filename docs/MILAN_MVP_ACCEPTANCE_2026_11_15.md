# Milan MVP acceptance evidence — 15 November 2026

The paired isolated staging aliases reported Ready at [`90abb8b`](https://github.com/adembilge/PracticaMIA/commit/90abb8bae6a98986b39ca9581276e0570319ff1c). This run used a signed-in synthetic saved case and the enabled evidence assistant. It records the observed behavior of this deployment.

## Saved case and PDF

| Check | Observation |
| --- | --- |
| Case owner opens saved case | Workspace loaded. All five requirements were still marked read. |
| Desktop and 390 px viewport | The draft PDF control and official ANPR handoff were available. The project owner later confirmed that the PDF downloaded. The confirmation did not specify a viewport or whether the file was opened. |
| Second Auth0 account | The project owner signed in with a different account. That session could list its own cases, but the owner’s case was absent. The direct workspace showed `Case unavailable`, the case GET returned `Case not found`, and the PDF GET returned `Preparation package unavailable`. The current repeat did not exercise a write. |
| Local contract checks | Package, checklist, assistant and Milan evaluation tests passed together (`31 passed`). The prior PR CI passed the full synthetic Chromium/API suite. |

The repeat confirms the owner download and cross-account read isolation. An opened-file check at each viewport and a two-account scope PATCH remain unverified on this revision. The earlier staging run covered scope PATCH denial. See [acceptance history](ACCEPTANCE_TESTING.md#manual-staging-case-and-document-checks).

## Bilingual evaluation

The [evaluation fixture](../evals/fixtures/milan_mvp_bilingual.json) contains three classes of scenarios. MIL-01 to MIL-07 were submitted in both UI languages against the live staging endpoint. MIL-08 to MIL-11 use the typed state machine. MIL-12 to MIL-14 require controlled evidence withdrawal or injected provider behavior. These last two groups were exercised locally by [the existing API tests](../backend/tests/test_milan_mvp_evaluation.py).

| ID | English | Italian | Source or expected behavior |
| --- | --- | --- | --- |
| MIL-01 | Quoted evidence | Quoted evidence | Milano FAQ `:0000`, 20 days from the move and ANPR. |
| MIL-02 | Quoted evidence | Quoted evidence | Milano FAQ `:0005`, separate TARI occupancy declaration. |
| MIL-03 | Quoted evidence | Quoted evidence | ANPR guide `:0015`, registration-office municipality, contract date and registration number. |
| MIL-04 | Quoted evidence | Quoted evidence | ANPR guide `:0018` and `:0017`, optional supporting files and the lease example. The displayed guidance directs users to the current form for case-specific requirements. |
| MIL-05 | Withheld with ANPR/registry links | Withheld with ANPR/registry links | No numerical limit was asserted. The English result was verified on a fresh page after an initial run captured a stale result. |
| MIL-06 | **Failed generated-answer check.** The answer was withheld. The page still showed its fixed, correct draft and self-submission notice. | Quoted evidence, with the fixed draft and self-submission notice | ANPR guide `:0021`, review and submit. In the English attempt a reviewed source was returned, while the model output did not pass validation. |
| MIL-07 | Withheld with ANPR/registry links | Withheld with ANPR/registry links | No automatic rejection was asserted. |

Nine of ten support prompts returned the requested reviewed evidence, and four of four abstention prompts withheld the answer and directed the user to official channels. All nine emitted answer bundles used the expected fixture citation IDs and source URLs. Exact excerpts are Italian source text in both interface languages. This small, single-pass sample does not establish translation quality, robustness to rephrasings, or general RAG quality.

The four workflow cases passed local API assertions for supported scope, missing registration evidence, household exclusion and out-of-jurisdiction exclusion. Those cases use typed facts and scope answers. The six controlled fault cases passed locally for both languages: unavailable evidence, invalid quotations and model timeout. No live approved sources were withdrawn and no live provider outage was induced.

## Public source check

- The [Comune di Milano service](https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza) and [Milano FAQ](https://servizicrm.comune.milano.it/centro-supporto/KA-00371/) support the move timing, ANPR channel and separate TARI declaration. The information was available through indexed official text. The direct automated page opens returned HTTP 403.
- The [citizen guide](https://public-anpr.github.io/anpr-docs-cittadino/src/docs/guide/guida_compilazione_cambio_residenza.pdf) supports title 2 rental details and describes a limit per attached file. The indexed [older guide](https://sc.anpr.interno.it/serviziCittadino/dist/docs/guida_compilazione_cambio_residenza.pdf) describes a total limit. The public material does not establish the current total limit in the signed-in form.
- The [national service page](https://innovazione.gov.it/dipartimento/focus/servizi-digitali-anagrafe-nazionale/) confirms that the actual ANPR service requires digital identity. The live form and its current attachment behavior remain for a human to inspect in their own session. No source approval was changed by this run.
