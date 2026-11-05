# Residence-change official document acquisition queue (5 November 2026)

**Status: candidate links / download requests only.** No original HTML/PDF
bytes were acquired in this investigation, no hashes were computed for original
documents, and no source was ingested or approved. This queue is **not** a
mandatory document checklist or a substitute for official instructions.

## Scope and current portal

For a change of address **within Milano** or **from another Italian
municipality to Milano**, the [Comune di Milano service
page](https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza)
directs users to **ANPR**, using SPID or CIE. The service includes Italian
citizens returning from abroad if registered AIRE. Applicants arriving from
abroad who are not covered by the current MVP use a different municipal
service. Individual supporting documents depend on the household, property
title, age and citizenship.

The [ANPR citizen guide](https://public-anpr.github.io/anpr-docs-cittadino/src/docs/guide/guida_compilazione_cambio_residenza.pdf)
is a national *workflow guide*, not Milan-specific legal evidence. The
source has an indexed PDF on a public ANPR documentation repository and is
also available at the [Ministry ANPR PDF
URL](https://sc.anpr.interno.it/serviziCittadino/dist/docs/guida_compilazione_cambio_residenza.pdf).
Its edition and instructions must be checked against the live portal.

## Newly discovered original-file leads (download by a person)

| Priority | Official source file | Why it matters | Status / caveat |
| --- | --- | --- | --- |
| High | [Assenso del proprietario o dell'affittuario (PDF)](https://www.comune.milano.it/documents/20126/526418/ASSENSO%2B%2BProprietario%2B%2BAffittuario.pdf/11c32ca7-8084-a40f-5543-da0f59a86006?t=1705660051113) | Permission to request residence while staying with a tenant or owner | Comune-indexed PDF; original bytes **not downloaded**; confirm current form |
| High for households with minors | [Consent of the non-moving parent, Mod. 1 (PDF)](https://www.comune.milano.it/ru/documents/20118/42443/Dichiarazione%2Bdi%2Bconsenso%2Bdel%2Bgenitore%2Bche%2Bnon%2Btrasferisce%2Bla%2Bresidenza.pdf/fb9da10d-ccba-f43b-b11b-c8bd169215a7?download=true&t=1743091608070&version=1.0) | Minor moves without both parents changing residence | Older Comune-indexed form; verify validity and version |
| High for households with minors | [Declaration of absent parent's particulars, Mod. 2 (PDF)](https://www.comune.milano.it/fr/documents/20118/42443/Dichiarazione%2Bdelle%2Bgeneralit%C3%A0%2Bdel%2Bgenitore%2Bassente.pdf/956f5b82-6707-6aaf-d1f0-be3b2b11dad8?download=true&t=1743091608065&version=1.0) | Conditional alternative when another parent's particulars must be declared | Older Comune-indexed form; verify validity and version |
| High | [ANPR operational guide for residence change (PDF)](https://public-anpr.github.io/anpr-docs-cittadino/src/docs/guide/guida_compilazione_cambio_residenza.pdf) | How to complete the online process, attach evidence and request validation | National online-service manual, **not** Milan requirements |
| Optional historical example | [Filled residence declaration example (PDF)](https://www.comune.milano.it/documents/20126/526597/fac%2Bsimile%2Bcompilazione%2Bmodulo%2Bcambio%2Bresidenza-indirizzo.pdf/e3df564c-39c9-1659-c7d5-a856845f3266?t=1546955378897) | Explains older paper form fields | Historical example, not a current application template |

**Why the two minor forms:** The municipality's [minor residence-change
FAQ](https://servizicrm.comune.milano.it/centro-supporto/KA-00434/Documenti-necessari-per-cambio-residenza-minori)
lists an identity-document copy and the non-moving parent's consent *or* a
declaration of an absent parent's particulars. The original PDFs were
located through municipal-indexed official URLs, but their current status
must be confirmed before treating them as operative forms.

**Why the landlord form:** The municipality's [guest FAQ](https://servizicrm.comune.milano.it/centro-supporto/KA-00367/Residenza-per-italiani-ospiti-documenti-immobile)
describes the owner's/tenant's assent. A more recent FAQ states this form
is also provided in the appointment-summary email or at a municipal desk;
not all applicant pathways require downloading it.

## Already known leads (not duplicates)

| Source | Status |
| --- | --- |
| [Non-EU documentation, Allegato A (PDF)](https://fareimpresa.comune.milano.it/documents/20126/526418/documentazione_cittadini_extra_u.e2.pdf/ba348f98-86db-faaf-7a96-852530d4be73?t=1649410999191) | User reports **successful local download**. The original file has **not been uploaded into this conversation** and is **not in Neon**. Verify revision and scope first. |
| [EU documentation, Allegato B (PDF)](https://www.comune.milano.it/documents/20126/526418/documentazione_per_cittadini_u.e..pdf/59339837-24ec-09ac-3352-0bd9d9c97599?t=1649410999191) | User could not download. Indexed copy quotes **2012** financial figures; mark historical, do not use for current thresholds. |
| [Residence declaration, Allegato 1 (PDF)](https://www.comune.milano.it/documents/20126/526597/dichiarazione%2Bdi%2Bresidenza.pdf/cb7c0558-d61b-1968-7143-b549f0ab337d?t=1560355046111) | User could not download. Older paper form, not proof this is the current ANPR pathway. |

## Newly indexed HTML FAQ candidates added to staging

- `milano-residence-minor-documents`:
  [official minor documents FAQ](https://servizicrm.comune.milano.it/centro-supporto/KA-00434/Documenti-necessari-per-cambio-residenza-minori).
- `milano-foreign-live-in-worker`:
  [official workers living with an owner/tenant FAQ](https://servizicrm.comune.milano.it/centro-supporto/KA-00594/).
  This describes a conditional employment-contract situation. Do not apply it
  to ordinary rented housing.

The exact above URLs are added to the version-controlled registry, and
corresponding **candidate metadata only** was inserted in isolated Neon
staging. No screenshot, search-index excerpt or reconstructed page is
presented as an original.

## Acquisition and integrity outcome

1. Browser-independent public search/index retrieval exposed page text and
   titles, but **not trusted original PDF bytes** in a downloadable format.
2. Direct original-file HTTP requests from the execution container failed
   at the network/DNS layer. Direct document download using the platform's
   URL downloader also failed. Attempts to read the PDF from the public
   ANPR GitHub repository returned no usable binary content. Screenshots
   of some indexed PDFs were unavailable; the ANPR guide's first page
   could be inspected.
3. Therefore, **zero** original sources were stored in Neon. Do not claim
   that an indexed PDF text excerpt is a source snapshot.
4. An intact user-downloaded original (no print-to-PDF, OCR, rewriting or
   translation) can be supplied through a trusted file attachment.
5. On the isolated staging database, the existing importer is designed to
   produce a `pending_review` snapshot using the official bytes; a
   separately authorized reviewer must check version, scope, extraction,
   source, and integrity before activation.
6. Old PDFs can be retained as **historical reference only** if appropriate,
   but they must not be approved as current procedural requirements
   without direct confirmation by the publisher.

## Operational next step

Ask for the user's locally downloaded **Allegato A** PDF and, if accessible,
the **owner/tenant assent**, **minor consent**, **absent-parent particulars**
and **ANPR guide** PDFs above. Confirm canonical publisher and validity
before registering any further PDF URLs: the imported files currently
require exact catalog URL matching, which some cache-parameterized or
redirecting public links do not satisfy. Keep production disabled.
