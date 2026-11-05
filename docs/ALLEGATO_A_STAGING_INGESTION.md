# Staging source ingestion record: Non-EU Allegato A

**Recorded:** 2026-11-05  
**Source identifier:** `milano-residence-non-eu-allegato-a`  
**Document:** *Dichiarazione di residenza — Allegato A: documentazione necessaria per l'iscrizione anagrafica di cittadini di Stati non appartenenti all'Unione Europea*  
**Environment:** Neon `staging-knowledge-0003-0006-2026-11-05` (migration `20261105_0006`)  
**Trust:** UNAPPROVED — `pending_review`; source remains `candidate` with no active approved version.

## Acquisition provenance and limitations

The bytes were **uploaded by the project owner into the ChatGPT conversation** as `documentazione_cittadini_extra_u.e2.pdf`. The original bytes were **not retrieved directly from the Comune di Milano server** by the staging ingestion process. The text matches an indexed Comune di Milano PDF at the published official-source lead. The raw PDF's authenticity and whether this edition remains authoritative in 2026 have **not been independently verified against the publisher's live download**.

The canonical candidate registry URL is:
`https://www.comune.milano.it/documents/20126/526418/documentazione_cittadini_extra_u.e2.pdf/ba348f98-86db-faaf-7a96-852530d4be73`

The user reports a successful download via a municipality-hosted `fareimpresa.comune.milano.it` URL. The snapshot's `fetched_url` column inherits the registered canonical URL; **this field must not be interpreted as proof of a direct successful automated fetch**.

The PDF's embedded **CreationDate and ModDate are 9 October 2013**. Its scope includes valid or renewing residence permits, first permits for employed work, and family-reunification permits. These categories may extend beyond the project's initial within-Italy residence-change scope. Current Comune di Milano guidance and form editions must be checked before any approval or eligibility rule extraction.

## Recorded staging database facts

| Property | Value |
| --- | --- |
| Version ID | `ca4cab89-f97f-4aff-9ec0-91a01d8ed792` |
| Revision | `1` |
| Version status | `pending_review` |
| Source status | `candidate` |
| Active version | `NULL` |
| MIME type | `application/pdf` |
| Original bytes | `7739` |
| Original SHA-256 | `653e55f062211daa3f938bdd61179e0f3b0910e9dbe71869372b8589ba966b11` |
| Extractor | `pdf-v1` |
| Pages | `1` |
| Normalized text length | `2421` characters |
| Stored passages | `3`, all labeled `Page 1` |
| Approval events | `0` |

The SQL import created the version, original `bytea` snapshot, and all three passages atomically after checking the source was still an unapproved candidate and the raw bytes matched the expected digest. A separate read-back verified the complete stored-byte SHA-256, source version SHA-256, original byte size, and each passage's normalized-text offsets and SHA-256.

**No production database changes, approval events, or trusted RAG retrieval exposure occurred.** The raw PDF has deliberately *not* been committed to the public GitHub repository.

## Pending independent review

1. Verify the original PDF against a current official Comune di Milano or national government publication, including any newer replacements.
2. Confirm whether its four residence-permit situations apply to the project's within-Italy residence-change MVP or only to first registrations/foreign arrivals.
3. Compare every footnote and mandatory-vs-conditional distinction against the original PDF. In particular, the `**` family-status documents are described as necessary for registering family relationships and issuing corresponding certificates, not universally mandatory.
4. If historic or superseded, **do not approve it as current authoritative RAG evidence**. Preserve it as an unapproved archival snapshot if useful for traceability.
5. If independently verified current and within scope, an authorized human reviewer may consider approving the exact hash-bound revision using the established approval and audit workflow.
