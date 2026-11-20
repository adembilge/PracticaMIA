# Phase 4 pilot claim review worksheet

This worksheet is for the authorized reviewer of Torino marriage banns and the Milano postal renewal pilot. The [acquisition record](phase-04-pilot-source-acquisition-2026-11-20.md#isolated-source-catalogue) identifies the five captured originals, their hashes and their SQLite versions. The six proposed decisions below are pending. The signed Milan residence-change route has its own review record.

## Claims to decide

Review each proposition within the stated scope, using the linked publisher page and the pinned passages. Record whether the page is current and whether its context supports that precise claim. If a material restriction is missing, record a narrower statement or leave the claim pending.

| Claim | Proposed statement and scope | Check before deciding |
| --- | --- | --- |
| T1 | Torino's banns office receives and processes the request for the pilot's two adult registered Torino residents who report never having married. | Confirm the office role, place of residence, who submits, and civil-status context. The ceremony municipality alone does not determine the office for the banns. [Office](https://www.comune.torino.it/amministrazione/ufficio-pubblicazioni-matrimonio-0) · [Service](https://www.comune.torino.it/servizi/richiedere-pubblicazioni-matrimonio) |
| T2 | The Torino resident can start the banns request through the municipality's online service. | Confirm the public service entry point and its relation to T1's scope. Record any unverified signed-in step separately. [Service](https://www.comune.torino.it/servizi/richiedere-pubblicazioni-matrimonio) |
| T3 | When the pilot's civil ceremony is in another named municipality, the civil registrar sends the delegation to that municipality after publication. | Confirm the timing and responsible official. Check the separate case where the ceremony is in Torino and neither applicant resides there. [Service](https://www.comune.torino.it/servizi/richiedere-pubblicazioni-matrimonio) |
| Q1 | An enabled Sportello Amico accepts a renewal submission for the pilot's code 16 employment permit. | Check the permit category and renewal row together. Keep an unspecified permit or a different filing route unresolved. [Code 16](https://www.portaleimmigrazione.it/ITA/lavoroSubordinato.html) |
| Q2 | The immigration office handles the appointment after the reported eligible postal filing. | Confirm the distinction between postal intake and the immigration appointment. A receipt alone leaves appointment details unresolved. [Procedure](https://www.portaleimmigrazione.it/ITA/nuovaProcedura.html) |
| Q3 | After the pilot's postal renewal, follow the date, time and place in the applicant's appointment letter once those details are given. | If a later summons will follow, leave the details pending. General Milano Questura addresses, hours and entry rules remain outside this claim. [Poste Italiane guide](https://www.poste.it/guida-rilascio-e-rinnovo-permesso-di-soggiorno/) |

## Public-source comparison for the reviewer

On 20 November 2026, the passages below were compared with the publishers' public pages. Use these observations when drafting the private claim decisions. Each decision still requires the reviewer's independent assessment.

| Claim | Pinned passages | Evidence and wording to consider |
| --- | --- | --- |
| T1 | Office `0009`, service `0011`–`0012` | The office receives requests and checks declarations and documents. The service page assigns submission to a Torino resident and requires both applicants to be legally free to marry. Both adults being registered in Torino and reporting no prior marriage are conditions of this pilot case. [Torino office](https://www.comune.torino.it/amministrazione/ufficio-pubblicazioni-matrimonio-0) · [Torino service](https://www.comune.torino.it/servizi/richiedere-pubblicazioni-matrimonio) |
| T2 | Service `0017` | Torino directs the resident applicant to the municipal online service and lists SPID, CIE and CNS. The public page links to service `438`. The destination returned no readable text in the public check, so use the published entry route as the scope and leave authenticated steps unverified. [Torino service](https://www.comune.torino.it/servizi/richiedere-pubblicazioni-matrimonio) · [Linked service](https://serviziweb.comune.torino.it/servizi/438) |
| T3 | Service `0014`–`0015` | For banns handled by Torino with a civil ceremony in a named other municipality, include that municipality in the request. The civil registrar sends the delegation after publication. For a ceremony in Torino with neither applicant resident there, the public page directs the couple to a municipality of residence. [Torino service](https://www.comune.torino.it/servizi/richiedere-pubblicazioni-matrimonio) |
| Q1 | Code 16 `0003`, `0005` | The code 16 employment permit page lists renewal among the applications accepted by the Sportello Amico network. Poste Italiane's table also marks renewal for code 16. Limit the wording to filing the specified renewal at an enabled branch. [Portale Immigrazione](https://www.portaleimmigrazione.it/ITA/lavoroSubordinato.html) · [Poste Italiane table](https://www.poste.it/guida-rilascio-e-rinnovo-permesso-di-soggiorno/) |
| Q2 | Procedure `0035` | Use the appointment venue and role stated in the procedure. After an applicable postal filing, the summons directs the applicant to the competent Questura's immigration office for the appointment. Appointment availability and details remain unresolved until communicated. [Portale Immigrazione procedure](https://www.portaleimmigrazione.it/ITA/nuovaProcedura.html) |
| Q3 | Poste `0080`–`0081` | The summons gives the date, time and place when the appointment has been set. If it only announces a later registered letter, leave those fields pending until that letter supplies them. General Milano Questura hours, locations and entry rules remain outside this claim. [Poste Italiane appointment guidance](https://www.poste.it/guida-rilascio-e-rinnovo-permesso-di-soggiorno/) |

## Read the eleven pinned passages

Open the review copy in read-only mode with `sqlite3 -readonly PracticaMIA-Phase4-Source-Review.sqlite3` or an equivalent SQLite viewer. Use the file hash recorded in the acquisition record. For a read-only query on the verified isolated Preview database, substitute the [five Preview version IDs](phase-04-pilot-source-acquisition-2026-11-20.md#verified-preview-registration) for their SQLite counterparts and retain the same ordinals. The query returns the stored text, version and passage identifiers, both hashes and the capture time for each expected reference. Missing rows or changed hashes require investigation before a decision.

```sql
WITH expected(claim, version_id, ordinal) AS (
  VALUES
    ('T1', '62a13693-281e-46ac-8d4e-e962dd9f7add', 9),
    ('T1', '5267e0b4-da08-442d-be06-14404a24e177', 11),
    ('T1', '5267e0b4-da08-442d-be06-14404a24e177', 12),
    ('T2', '5267e0b4-da08-442d-be06-14404a24e177', 17),
    ('T3', '5267e0b4-da08-442d-be06-14404a24e177', 14),
    ('T3', '5267e0b4-da08-442d-be06-14404a24e177', 15),
    ('Q1', 'c3541590-d130-47b9-ba8b-01213fa7a37e', 3),
    ('Q1', 'c3541590-d130-47b9-ba8b-01213fa7a37e', 5),
    ('Q2', 'c98ec604-a0d9-438b-99e8-1ecb1dc4d418', 35),
    ('Q3', '9ef316bb-a2ae-4a9b-9fea-8dd8ced7655e', 80),
    ('Q3', '9ef316bb-a2ae-4a9b-9fea-8dd8ced7655e', 81)
)
SELECT e.claim, v.source_id, v.id AS version_id, s.official_url,
       v.retrieved_at, v.status, v.content_sha256 AS original_sha256,
       p.id AS passage_id, p.section_path, p.content_sha256 AS passage_sha256,
       p.content
FROM expected e
JOIN knowledge_source_versions v ON v.id = e.version_id
JOIN knowledge_sources s ON s.id = v.source_id
JOIN knowledge_source_passages p ON p.version_id = v.id AND p.ordinal = e.ordinal
ORDER BY e.claim, v.source_id, p.ordinal;
```

## Record the human decision

Use a private review copy. Record the outcome, exact approved wording and scope if supported, verification date, reviewer, and rationale for each claim. Include any exceptions or competing official evidence. If a newer original differs, record the new version and verify its passages before reusing the claim. Leave the initial worksheet here as a record of the review request.

| Claim | Outcome (supported as scoped, revise, or pending) | Reviewer and verification date | Rationale or revised scope |
| --- | --- | --- | --- |
| T1 | Pending | | |
| T2 | Pending | | |
| T3 | Pending | | |
| Q1 | Pending | | |
| Q2 | Pending | | |
| Q3 | Pending | | |

For a hosted decision, record the Preview source version and passage IDs with the verified original and passage hashes. Use the [authenticated source approval workflow](../../docs/KNOWLEDGE_REVIEW_WORKFLOW.md#approval-invariants) for any activation. A claim also needs its own scoped review record under the [claim-evidence contract](phase-03-claim-evidence.md#claim-and-evidence-contract). The current reviewer API records source-version decisions. This worksheet prepares the separate claim review record.
