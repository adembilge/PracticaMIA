# Phase 4 pilot source acquisition · 20 November 2026

This record supports human review of claims T1–T3 and Q1–Q3 in the [three-authority pilot](phase-04-three-authority-pilot.md#evidence-for-source-review). Five pages yielded original HTML and eleven selected passages pinned to version IDs in a local review catalogue. Human claim decisions are pending.

## Captured sources

The acquisition requested each exact HTTPS URL without following redirects. The originals below returned HTTP 200 and `text/html` and contained the expected publisher content. The SHA-256 covers the exact response body. Displayed dates come from the publisher page. All captures took place on 20 November 2026 UTC.

| Capture label | Publisher page and displayed update date | UTC time and byte count | Original SHA-256 |
| --- | --- | --- | --- |
| `torino-banns-office` | [Città di Torino office page](https://www.comune.torino.it/amministrazione/ufficio-pubblicazioni-matrimonio-0), 26 June 2025 | 14:27:38 · 64578 bytes | `e7fdc3626542170333ae6aeafbf08fc8f2ed8a3eaccaef6a0756683312d0d8c3` |
| `torino-banns-service` | [Città di Torino service page](https://www.comune.torino.it/servizi/richiedere-pubblicazioni-matrimonio), 13 October 2026 | 14:27:37 · 74456 bytes | `c57e3b219288b77fb5f7af63c74b005cb471b1538423af1dea04f179282537d4` |
| `portale-immigrazione-code-16` | [Portale Immigrazione code 16](https://www.portaleimmigrazione.it/ITA/lavoroSubordinato.html), 22 July 2024 | 14:27:33 · 8109 bytes | `02bb7a627c0e3836d87b65c9f76b798bac5c8cd813a88659c3208ea381c1975e` |
| `portale-immigrazione-procedure` | [Portale Immigrazione procedure](https://www.portaleimmigrazione.it/ITA/nuovaProcedura.html), no explicit page update date identified | 14:27:33 · 21463 bytes | `6c4715686b3d89f641c91fa302308a2f374f87a611ebd1b8c2f3e2fbe97be6f1` |
| `poste-residence-permit-appointments` | [Poste Italiane permit guide](https://www.poste.it/guida-rilascio-e-rinnovo-permesso-di-soggiorno/), no explicit page update date identified | 15:32:03 · 221961 bytes | `73f54fe10c5b18f207b3da0271f83216a92b8591e5e2e9540688d39929080a5f` |

The [Milano Questura office listing](https://questure.poliziadistato.it/it/servizio/orari/5730dc9d4a8fc591672053) returned the *Accesso negato* page again at 15:32:02 UTC. The captured Poste guidance applies to what the postal appointment letter states. Local office venue and entry rules remain pending.

## Passage references for reviewer comparison

The [repository extractor](../../backend/app/knowledge/html_extraction.py) uses `html-v1` for the four baseline originals and `html-v2` for the pinned Poste page. The latter skips void elements inside ignored containers when tracking exclusion depth. Each row identifies an exact extracted passage by the capture label, zero-based ordinal and start-inclusive, end-exclusive character offsets in the normalized text. SHA-256 covers the entire UTF-8 passage.

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
| Q3 | `poste-residence-permit-appointments` · *Conserva la ricevuta e la lettera di convocazione* · “il luogo in cui presentarsi” | 80 · 7532–7789 | `76c14f96a6bee582a67585cbbca1eac595b892479d6dfd321d401f83394b15f9` |
| Q3 | `poste-residence-permit-appointments` · *Conserva la ricevuta e la lettera di convocazione* · “verrà inviata una raccomandata” | 81 · 7791–8043 | `8afcbde4d26364599ac5a36f1b0ab9d88232c1ec86ca59c27af930e7bfec5950` |

## Claim decisions to record

| Claim | Verify against the original and pilot scope | Reviewer decision |
| --- | --- | --- |
| T1 | Check the office's stated intake and processing role. The service describes residence, adult age and civil-status conditions. The pilot uses two adult Torino residents who report never having married. | Pending |
| T2 | Verify the public online-service entry point and that the resident applicant uses it. Inspect the linked public entry point separately before asserting signed-in behavior. | Pending |
| T3 | Verify that the delegation is sent after publication, by the civil registrar, to the ceremony municipality. Check the adjacent guidance for people who marry in Torino but reside elsewhere. | Pending |
| Q1 | Review the code 16 heading, enabled postal network and renewal row together. Limit the claim to postal intake for the scoped renewal. | Pending |
| Q2 | Check the post-filing summons paragraph and its exception when an appointment is unavailable at filing. Date and time remain unresolved when the applicant has only a receipt. | Pending |
| Q3 | Verify the stated date, time and place against the applicant's supplied summons. If the first letter says a later summons will follow, leave the appointment details pending. Review local office access separately. | Pending |

## Isolated source catalogue

From `backend/`, use the [pilot import command](../../backend/app/knowledge/pilot_source_review.py) with the four baseline HTML originals and the additional Poste original for Q3, named after their capture labels. Keep the originals and database outside Git.

```sh
python -m app.knowledge.pilot_source_review \
  --originals /path/to/pilot-originals \
  --catalogue /path/to/PracticaMIA-Phase4-Source-Review.sqlite3
```

The command stores original bytes and extracted passages through the existing snapshot service. It requires the pinned capture hashes and verifies each selected passage before committing. The target is a standalone SQLite file marked for pilot review. Reopening the same catalogue preserves its IDs. Creating another catalogue generates new IDs.

| Source ID | Local version ID, revision 1 | Extracted passages | Claim ordinals |
| --- | --- | --- | --- |
| `torino-banns-office` | `62a13693-281e-46ac-8d4e-e962dd9f7add` | 54 | T1 `0009` |
| `torino-banns-service` | `5267e0b4-da08-442d-be06-14404a24e177` | 119 | T1 `0011`, `0012` · T2 `0017` · T3 `0014`, `0015` |
| `portale-immigrazione-code-16` | `c3541590-d130-47b9-ba8b-01213fa7a37e` | 19 | Q1 `0003`, `0005` |
| `portale-immigrazione-procedure` | `c98ec604-a0d9-438b-99e8-1ecb1dc4d418` | 80 | Q2 `0035` |
| `poste-residence-permit-appointments` | `9ef316bb-a2ae-4a9b-9fea-8dd8ced7655e` | 92 | Q3 `0080`, `0081` |

The extended 20 November import and repeat preserved the four baseline version IDs and produced five `pending_review` versions, 364 passages and eleven claim references. The integrity and foreign-key checks passed. The review audit contained zero approval events. The extended SQLite file's SHA-256 is `a539ddb3c1b1a34deb7c1001b095a0532342c517bd00f60e862d5056568d6b9a`.

These IDs refer to the offline review copy. The [verified Preview mapping](#verified-preview-registration) links them to the hosted versions by original and passage hashes. The authorized reviewer can inspect the six pending claims against the published sources and record the scoped rationale using the [claim-specific process](phase-03-claim-evidence.md#claim-and-evidence-contract). [Authenticated approval](../../docs/OFFICIAL_SOURCE_INTAKE.md#5-human-evidence-review) remains pending.

The [claim review worksheet](phase-04-claim-review-handoff.md) lists the exact claims, case boundaries and eleven pinned references in a read-only query. It also provides the fields for recording a human decision.

## Import into the isolated Preview registry

Verify the protected reviewer deployment's Git revision and its database binding. Use the non-default `preview-preparation-mvp-20261107` branch from the [deployment record](../../docs/VERCEL_NEON_DEPLOYMENT.md#isolated-preview). The database engine must be PostgreSQL with an existing schema accepted by the [staging guard](../../backend/app/knowledge/staging_guard.py). The reviewer deployment needs the current snapshot verifier, including support for the pinned Poste capture's `html-v2` extraction.

Set the following values in the operator's local environment. Obtain the hostname and database name from the confirmed branch and direct compute, separately from the connection string. Supply `DATABASE_URL` securely using the direct matching connection.

```sh
export PRACTICAMIA_KNOWLEDGE_TARGET=staging
export PRACTICAMIA_PILOT_PREVIEW_HOST='verified-direct-preview-host'
export PRACTICAMIA_PILOT_PREVIEW_DATABASE='verified-preview-database'
python -m app.knowledge.pilot_source_review --preview --originals /path/to/all-five-originals
```

The command accepts the five pinned original files in one transaction. It checks their hashes, scopes, the database identity and schema, and all eleven passage fingerprints. A failed check rolls back the transaction. A successful run prints the hosted source-version and passage IDs for the review worksheet. Repeating the same pending import preserves those IDs. The separate reviewer workflow owns the approval decisions.

### Verified Preview registration

On 20 November 2026 the work environment could reach Neon through its control plane, while direct database host resolution failed. The operator used one control-plane transaction scoped to the existing `preview-preparation-mvp-20261107` branch (`br-broad-sea-ba61e95a`), database `practicamia`, and Alembic revision `20261116_0017`. The transaction copied the verified offline originals, snapshots and passages into the existing candidate registry. The source and claim pins were checked against the `ff2967167b59f68b07f58c30085bd5e81c3ea058` tree. Temporary tables backed exact row comparisons before commit.

| Source ID | Preview version ID, revision 1 |
| --- | --- |
| `torino-banns-office` | `0e7ae724-e6cc-5dd7-8606-019bf8876f73` |
| `torino-banns-service` | `3d8c045e-f51b-55e6-b7e6-da217236d815` |
| `portale-immigrazione-code-16` | `5923cbd1-4247-57e1-9437-5696faf01f7d` |
| `portale-immigrazione-procedure` | `63a2e1ca-42af-5fd2-a327-4f6983f07cf0` |
| `poste-residence-permit-appointments` | `67fb7666-c037-5b98-aa33-34f3173373ad` |

An independent read after commit verified five `candidate` sources, five `pending_review` versions, five matching original byte hashes, 364 matching passage hashes and all eleven pinned references. The pilot sources had zero active version pointers and zero review events. Preview passage IDs use the listed version ID followed by `:` and the same four-digit ordinal as the offline copy.

### Protected reviewer Preview

[PR #198](https://github.com/adembilge/PracticaMIA/pull/198) brought the pinned `html-v2` verifier from `main` to `preview/auth-review-isolated`. A local signed API test against a disposable copy of the five captured records returned integrity-verified previews for all five sources and matched 364 passages and all eleven claim pins. Anonymous and non-reviewer reads were denied. Changing the Q3 extraction version caused the inspection to fail its integrity check.

On 20 November 2026 both protected branch aliases served Git revision `a8e612141cf51b4d2503bc2663b49a80d8cbd2e1`. The API health endpoint responded and the anonymous Q3 read returned `Authentication required`. After the reviewer signed in, the protected web proxy returned all five expected candidate versions in its queue. The version endpoints returned `integrity_verified: true` and the expected original hash for every version, with passage totals of 54, 119, 19, 80 and 92 in the order listed above. All eleven pinned passage IDs and hashes matched, including Q3 ordinals `0080` and `0081`. These branch-specific version IDs confirm that the application read the registered Preview data. The checks used read-only requests and all five versions were `pending_review`. The disposable PostgreSQL import exercise runs in backend CI.

After signing into the [protected reviewer Preview](https://practicamia-git-preview-auth-review-d32a00-firatadembilge-4729.vercel.app/knowledge/review) with an allowlisted account, open the [read-only Q3 version](https://practicamia-git-preview-auth-review-d32a00-firatadembilge-4729.vercel.app/api/knowledge/review/versions/67fb7666-c037-5b98-aa33-34f3173373ad) in the same browser. Check that it returns `integrity_verified: true`, the pinned original hash and Q3 ordinals `0080` and `0081`. The [read-only queue](https://practicamia-git-preview-auth-review-d32a00-firatadembilge-4729.vercel.app/api/knowledge/review/queue) should include all five version IDs above with `pending_review` status. Record the six claim outcomes separately in a private copy of the [worksheet](phase-04-claim-review-handoff.md).
