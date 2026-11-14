# PracticaMIA — implementation and release evidence

**Updated:** 14 November 2026. The production checks below used a fictional saved case.

## Verified engineering evidence

| Item | Evidence | Limits of the check |
| --- | --- | --- |
| Saved case, intake and workflow | PRs [#64](https://github.com/adembilge/PracticaMIA/pull/64) and [#67](https://github.com/adembilge/PracticaMIA/pull/67) | Checklist acknowledgements record the user's review. They do not record administrative completion. |
| Private document review and PDF preparation | PRs [#65](https://github.com/adembilge/PracticaMIA/pull/65), [#66](https://github.com/adembilge/PracticaMIA/pull/66) and [#72](https://github.com/adembilge/PracticaMIA/pull/72) | Production personal-document upload is disabled. The exported PDF is a reviewable preparation draft. |
| Isolated private-document acceptance | The localhost Chromium/FastAPI/PostgreSQL 17 run passed 15 scenarios, including D1–D5. Tesseract extracted the expected housing basis and move-in date from generated PNG, JPEG and image-only PDF samples. The draft UI and downloaded PDF preserved review and handoff semantics. | Uses synthetic identities, generated files, a harmless ClamAV test signature and an in-process scanner transport. No live Auth0, scanner vendor, hosted OCR runtime or personal data was used. See [acceptance coverage](ACCEPTANCE_TESTING.md#acceptance-scenarios). |
| Isolated browser acceptance | [PR #68](https://github.com/adembilge/PracticaMIA/pull/68), eight synthetic browser scenarios passing | This suite uses synthetic identities and covers different behavior from the live Auth0 check. |
| Production deployment at the time of the Auth0 check | Web and API both reported Ready on [`24ee003`](https://github.com/adembilge/PracticaMIA/commit/24ee003050c13eab6b5ca40e14f7f3ff87a93514). [Web deployment](https://vercel.com/firatadembilge-4729/practicamia/9W8k1ZXLPybxsfCVUXsMUtxU3wh1) · [API deployment](https://vercel.com/firatadembilge-4729/practicamia-api/AAo41VkywCJQk8Ac9J5uA7oumkMu) | Production revision `20261109_0016` was previously recorded on 9 November. The migration revision was outside the 14 November browser check. |
| Live Auth0 and case isolation | Two distinct authenticated identities verified on 14 November. The owner reopened the fictional case with 5/5 acknowledgements and confirmed successful PDF download. The second account could not list, open or download that case. [Manual run and limitations](ACCEPTANCE_TESTING.md#manual-production-auth0-check) | Covers read access to the selected fictional case and PDF. Write, upload, and reviewer permission paths require separate evidence. |
| Milan scope alignment | [PR #74](https://github.com/adembilge/PracticaMIA/pull/74) aligns the entry questions with the signed route for moves within Milan and moves into Milan from another Italian municipality. Both paths passed browser acceptance. The production frontend and API reached [`8449440`](https://github.com/adembilge/PracticaMIA/commit/8449440469d79cea48543076cb2204dd23b15f4b). | The post-deployment smoke check covered homepage copy and API health. The full scope scenarios ran in CI. |
| Official source and AI evaluation preparation | The 14 November review compared public Comune di Milano and ANPR materials, prepared 14 cases with 28 EN/IT inputs, and ran 15 offline scope and quotation checks. The companion review is titled *PracticaMIA Milano MVP kaynak incelemesi ve AI değerlendirme seti*. | Live ANPR form behavior and current upload limit remain unconfirmed. Live model quality was not measured. |

## Outstanding MVP and release gates

| Gate | Remaining acceptance evidence |
| --- | --- |
| Staging acceptance and bilingual AI | Establish a matched, isolated frontend/API Preview for the reviewed commit. Run the EN/IT evaluation and record actual answer correctness, citation and source-version validity, and abstention. Complete staging evidence for the supported journey and unsupported fallback. No matching Preview was listed for either project on 14 November. |
| Document processing and access controls | Repeat the document acceptance flow in isolated hosted staging with two Auth0 accounts and the intended scanner and OCR runtime. Broaden OCR evaluation beyond the generated acceptance fixtures. The earlier production check covers case and PDF read access. |
| Personal-document beta | Keep production uploads disabled until the responsible review and operational checks for privacy, malware scanning, key management, retention/deletion, backup/restore, and monitoring are evidenced. Complete the consented beta and document findings before broader release. [Document vault release checklist](PRIVATE_DOCUMENT_VAULT_RELEASE.md) |
| Roadmap and release decision | Reconcile the [task registry](TASKS.yaml) against evidence and required approvals. Record staging results, rollback readiness and explicit owner go/no-go under [specification §26](../PracticaMIA_Complete_Project_Specification.md#26-mvp-acceptance-criteria-and-release-gates). |

For implementation details see [the documentation index](README.md).
