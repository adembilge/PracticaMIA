# Phase 4 pilot source acquisition · 20 November 2026

This record supports human review of claims T1–T3 and Q1–Q3 in the [three-authority pilot](phase-04-three-authority-pilot.md#evidence-for-source-review). Four pages yielded original HTML and nine selected passages, now pinned to version IDs in a local review catalogue. The Milano Questura local page returned an access-denied document and remains an acquisition gap. Human claim decisions are pending.

## Captured sources

The acquisition requested each exact HTTPS URL without following redirects. The four originals below returned HTTP 200 and `text/html` and contained the expected publisher content. The SHA-256 covers the exact response body. Displayed dates come from the publisher page. All captures took place on 20 November 2026 UTC.

| Capture label | Publisher page and displayed update date | UTC time and byte count | Original SHA-256 |
| --- | --- | --- | --- |
| `torino-banns-office` | [Città di Torino office page](https://www.comune.torino.it/amministrazione/ufficio-pubblicazioni-matrimonio-0), 26 June 2025 | 14:27:38 · 64578 bytes | `e7fdc3626542170333ae6aeafbf08fc8f2ed8a3eaccaef6a0756683312d0d8c3` |
| `torino-banns-service` | [Città di Torino service page](https://www.comune.torino.it/servizi/richiedere-pubblicazioni-matrimonio), 13 October 2026 | 14:27:37 · 74456 bytes | `c57e3b219288b77fb5f7af63c74b005cb471b1538423af1dea04f179282537d4` |
| `portale-immigrazione-code-16` | [Portale Immigrazione code 16](https://www.portaleimmigrazione.it/ITA/lavoroSubordinato.html), 22 July 2024 | 14:27:33 · 8109 bytes | `02bb7a627c0e3836d87b65c9f76b798bac5c8cd813a88659c3208ea381c1975e` |
| `portale-immigrazione-procedure` | [Portale Immigrazione procedure](https://www.portaleimmigrazione.it/ITA/nuovaProcedura.html), no explicit page update date identified | 14:27:33 · 21463 bytes | `6c4715686b3d89f641c91fa302308a2f374f87a611ebd1b8c2f3e2fbe97be6f1` |

The [Milano Questura office listing](https://questure.poliziadistato.it/it/servizio/orari/5730dc9d4a8fc591672053) returned HTTP 200 at 14:27:27 UTC with the title *Accesso negato | Polizia di Stato*. HTTP status alone is insufficient to establish a successful capture. Q3 retains its local source locator. Keep local venue and access guidance pending until the substantive office content can be inspected.

## Passage references for reviewer comparison

The [repository's `html-v1` extractor](../../backend/app/knowledge/html_extraction.py) accepted all four originals. Each row identifies an exact extracted passage by the capture label, zero-based ordinal and start-inclusive, end-exclusive character offsets in the normalized text. SHA-256 covers the entire UTF-8 passage. The short Italian locator helps find the text on the publisher page. The local version IDs below anchor these ordinals in the review catalogue.

| Claim | Capture, section and locator | Ordinal and character offsets | Passage SHA-256 |
| --- | --- | --- | --- |
| T1 | `torino-banns-office` · *Competenze* · “Riceve le richieste di pubblicazione di matrimonio” | 9 · 269–482 | `0a37ae3b0e8be8a02574f6f55450d6f9b89eed993efc1f61b62a0b959fc1acd4` |
| T1 | `torino-banns-service` · *A chi è rivolto* · “residente nel Comune di Torino” | 11 · 397–687 | `067ab354e26f0e48a9831213af153236754a4c8dc5cba4a57b75b72ba31d9020` |
| T1 | `torino-banns-service` · *A chi è rivolto* · “stato libero” | 12 · 689–768 | `4759a9ca53a8689520008ea0c65e89687530b495e8b51500b186a49ffc3edd89` |
| T2 | `torino-banns-service` · *Come fare* · “accedendo al servizio online” | 17 · 1406–1497 | `ca0a35937a0ccae67a3a2ac4b49e8561ad3f245256f894faf6a8dbc9438a0761` |
| T3 | `torino-banns-service` · *Descrizione* · “inviare la delega” | 14 · 1002–1244 | `862afa54f370ce5bed4bf877be118b8bcd51475900f0e59968e73a8fcf879621` |
| T3 | `torino-banns-service` · *Descrizione* · “pur non essendo qui residenti” | 15 · 1246–1393 | `0965848e11327d68d6f3933d5b773460a0c0b32f9aff8172cb61df8e4d2a99d2` |
| Q1 | `portale-immigrazione-code-16` · *Codice 16* · “Rete Sportello Amico” | 3 · 189–269 | `d4f618deccae2e9a8e86cd6a7c79ec3e5cfbd38a3b604320c62ca3a53dfecd01` |
| Q1 | `portale-immigrazione-code-16` · *Codice 16* · “Rinnovo” | 5 · 281–288 | `b9be6dc48a32161f6f7a26fb19a1385e76fcd9991a9fa01e99b3296899438c23` |
| Q2 | `portale-immigrazione-procedure` · *Informazioni generali* · “data e ora di convocazione” | 35 · 5624–6045 | `1fef9aa6247abf32b2d36dadf3087ab988c56a4e46f2824b9a535cd4c90af9c3` |

## Claim decisions to record

| Claim | Verify against the original and pilot scope | Reviewer decision |
| --- | --- | --- |
| T1 | Check the office's stated intake and processing role. The service describes residence, adult age and civil-status conditions. The pilot uses two adult Torino residents who report never having married. | Pending |
| T2 | Verify the public online-service entry point and that the resident applicant uses it. Inspect the linked public entry point separately before asserting signed-in behavior. | Pending |
| T3 | Verify that the delegation is sent after publication, by the civil registrar, to the ceremony municipality. Check the adjacent guidance for people who marry in Torino but reside elsewhere. | Pending |
| Q1 | Review the code 16 heading, enabled postal network and renewal row together. Limit the claim to postal intake for the scoped renewal. | Pending |
| Q2 | Check the post-filing summons paragraph and its exception when an appointment is unavailable at filing. Date and time remain unresolved when the applicant has only a receipt. | Pending |
| Q3 | Acquire the substantive Milano Questura office listing for local access guidance and review it alongside the case's supplied summons. Q2 supports the general appointment step. | Acquisition pending |

## Isolated source catalogue

From `backend/`, use the [pilot import command](../../backend/app/knowledge/pilot_source_review.py) with a directory containing just the four exact HTML originals, named after their capture labels. Keep the originals and database outside Git.

```sh
python -m app.knowledge.pilot_source_review \
  --originals /path/to/pilot-originals \
  --catalogue /path/to/PracticaMIA-Phase4-Source-Review.sqlite3
```

The command stores original bytes and extracted passages through the existing snapshot service. It requires the four pinned capture hashes and verifies each selected passage before committing. The target is a standalone SQLite file marked for pilot review. The command outputs each claim's source ID, version ID and full passage IDs for review. Reopening the same catalogue preserves its IDs. Creating another catalogue generates new IDs.

| Source ID | Local version ID, revision 1 | Extracted passages | Claim ordinals |
| --- | --- | --- | --- |
| `torino-banns-office` | `62a13693-281e-46ac-8d4e-e962dd9f7add` | 54 | T1 `0009` |
| `torino-banns-service` | `5267e0b4-da08-442d-be06-14404a24e177` | 119 | T1 `0011`, `0012` · T2 `0017` · T3 `0014`, `0015` |
| `portale-immigrazione-code-16` | `c3541590-d130-47b9-ba8b-01213fa7a37e` | 19 | Q1 `0003`, `0005` |
| `portale-immigrazione-procedure` | `c98ec604-a0d9-438b-99e8-1ecb1dc4d418` | 80 | Q2 `0035` |

The 20 November import and repeat produced four `pending_review` versions, 272 passages and nine claim references. The integrity and foreign-key checks passed. The approved citation resolver withheld all nine references, and the review audit contained zero approval events. The SQLite file's SHA-256 is `e04624db23e5002ba224211c78bf19894d8f83899d931e1d1f1238c37eabcf99`.

These IDs refer to the offline review copy. A hosted import will have its own version and passage IDs, to be bound by the original and extracted hashes. The authorized reviewer can inspect the five pending claims against the published sources and record the scoped rationale using the [claim-specific process](phase-03-claim-evidence.md#claim-and-evidence-contract). Hosted candidate registration and [authenticated approval](../../docs/OFFICIAL_SOURCE_INTAKE.md#5-human-evidence-review) remain pending. Q3 still requires the local page's substantive content.
