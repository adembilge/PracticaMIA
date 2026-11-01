# Intake

Task 16. Written on 2 November 2026. The journeys are in [JOURNEYS.md](JOURNEYS.md). The document rows are in [DOCUMENTS.md](../research/DOCUMENTS.md). The conflicts are in [DOSSIER.md](../research/DOSSIER.md).

This file lists the fields those journeys ask for, and the one question an ambiguous story may ask. It is not a conversation script, a screen, or a rule the agent may state. A field already present in the story is not asked again. An unreviewed document row is not a question.

No field stores a SPID or CIE password.

## Asked

| ID | Field | When it is asked | Type | Validation | Source | Purpose | Requirement |
|---|---|---|---|---|---|---|---|
| F-01 | Language | When the message is not already English or Italian | English, Italian, or other | Other stops the case. English or Italian is kept. | Person | The case runs only in a release language. | U-03. Release languages in [MVP_SCOPE.md](MVP_SCOPE.md). |
| F-02 | Already registered in Milano | Only for A-01, and only when the story does not say | Yes, never registered in Italy, or registered in another municipality | Yes continues. The other two values do not open the case. | Person | Separate an intra-Milan change from the other doors. | A-01. [MVP_SCOPE.md](MVP_SCOPE.md). |
| F-03 | Who is named, and whether she files alone | Only for A-02, and only when the story does not say. One question, not two. | Owner, named tenant, guest, or another title; alone or with another adult | Owner or named tenant, already resident in Milan, filing alone, continues. Guest, another title, or another adult does not open the case. | Person | Keep the single-adult owner or named-tenant case. | A-02. [MVP_SCOPE.md](MVP_SCOPE.md). |
| F-04 | New address | When a supported story does not already contain it | One line | It must name Milano. Empty blocks the case from going on. This does not split DOC-07 into five fields. DOC-07 stays unreviewed. | Person | The new address has to be in Milan. | [MVP_SCOPE.md](MVP_SCOPE.md). |
| F-05 | Title | When a supported story does not already say | Owner, or named tenant | Any other title does not open the case. | Person | Only those two titles stay in this release. | [MVP_SCOPE.md](MVP_SCOPE.md). DOC-10 stays unreviewed. |
| F-06 | Permit can be attached | Only when the story says the person is a non-EU citizen and does not already say this | Yes or no | No does not open the case. | Person | A non-EU case needs a permit that can be attached. | [MVP_SCOPE.md](MVP_SCOPE.md). DOC-20 stays unreviewed. This does not choose copy or original. |
| F-07 | Title paper | After the case is open | One upload. Lease when F-05 is named tenant. Ownership paper when F-05 is owner. | Missing or unreadable blocks ready. | Upload | The paper is what the name and the new address are checked against. | I-01. [MVP_SCOPE.md](MVP_SCOPE.md). |
| F-08 | Identity or permit paper | When the person supplies one. Required for a non-EU case that reached F-06 yes. Not required for S-02. | One upload | Unreadable blocks ready when the upload was required. Compared on the name, and on the address when the paper shows one. | Upload | So the papers can be compared. | S-01. Not S-02. DOC-20 stays unreviewed. |
| F-09 | Name and address read from each upload | When an upload is present | The name, and the address if the paper shows one | Taken from the document, not typed over it. If two values differ, the case stays not ready until the person names which value is correct. The schema does not choose. | Upload | Show a mismatch instead of picking a value. | I-02. [MVP_SCOPE.md](MVP_SCOPE.md). |

## Not asked

These rows stay in the document catalog. This release does not collect them.

- DOC-03 kinship, DOC-04 driving licence, and DOC-05 vehicles. The journeys do not use them.
- DOC-08 optional address parts.
- DOC-09 registry data of a person already at the address. That declaration does not open a case.
- DOC-11 cadastral details, and DOC-12 the lease office, date, and registration number. The check uses the name and the address on the upload.
- DOC-13 the owner's identity card. It stays an example, not a requirement.
- DOC-18 contact details and the time band.
- DOC-19 the ANPR confirmation control. PaperPilot does not file.
- DOC-21 and DOC-22. The expired-permit pair is unresolved, so neither is asked.
- DOC-26 through DOC-47. Those are the other lists and the other door.

No password. No date of birth. [ELIGIBILITY.md](../research/ELIGIBILITY.md) says no opened page states an age minimum, so 18 is not an intake question. No day count.

## Where the nine requests use them

- S-01 uses F-04 through F-09 from the story and the three uploads.
- S-02 uses the ownership paper and does not require F-08.
- I-01 stops on F-07.
- I-02 stops on F-09.
- A-01 is F-02.
- A-02 is F-03.
- U-01, U-02, and U-03 collect nothing and open no case.
