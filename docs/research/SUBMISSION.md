# Submission channel

Task 12. Written on 1 November 2026. SRC-01, SRC-02, SRC-03, SRC-04, and SRC-06 were opened again that night. SRC-11 is the channel sentence opened earlier the same night. Source ids are in [SOURCES.md](SOURCES.md). The sequence is in [PROCEDURE.md](PROCEDURE.md). What may be attached stays in [DOCUMENTS.md](DOCUMENTS.md).

A row is a destination, a sign-in method, a send control, or a confirmation one of those pages states. No opened page describes an interface by which another system can submit the declaration. `Not stated` in the machine column means that. The words "sent automatically" on SRC-01 are the portal acting after the adults confirm. They are not such an interface.

This file is not the dossier, and it is not a rule the agent may state. Task 14 is still the human review. The review status of every row is unreviewed.

SRC-05 is the circular SRC-04 cites. SRC-04 itself states the notice channels, so SRC-05 was not opened. No submission method is taken from it.

The guide's warning that a change of declaration type deletes what was entered is already in the procedure file. It is not a row.

## Where the supported declaration goes

SRC-06 says access requires SPID or CIE. SRC-03 shows four ways in. SRC-01 names none. This file does not decide which of the four can be used for this declaration.

| ID | Item | Who | Machine integration | First release | Evidence | Review |
|---|---|---|---|---|---|---|
| CH-01 | The ANPR services page, SRC-03 | The declarant | Not stated | This is the destination. | SRC-01 links "ACCEDI AI SERVIZI" to https://www.anagrafenazionale.interno.it/servizi-al-cittadino/. SRC-06 links "Richiedi" to the same address. The page is the sign-in page. It does not itself say that every method on it can be used for this declaration. | unreviewed |
| CH-02 | CIE | The person signing in | Not stated | Does not choose. | SRC-03 shows "Entra con CIE". SRC-06 says access requires SPID or CIE. SRC-01 does not name a method. | unreviewed |
| CH-03 | SPID | The person signing in | Not stated | Does not choose. | SRC-03 shows "Entra con SPID" and entry buttons for Namirial, Aruba, Poste, Titt, Lepida, Infocert, SPIDItalia Register.it, Sielte, TeamSystem, Etna, Infocamere, and Intesi. It says a person who has no SPID requests one from a provider. SRC-06 names SPID. SRC-01 does not. | unreviewed |
| CH-04 | Tessera Sanitaria and CNS | The person signing in | Not stated | Does not choose. | SRC-03 says access is allowed with the Tessera Sanitaria and the Carta Nazionale dei Servizi, and shows "Entra con CNS". SRC-06 does not name either. SRC-02 names CNS only for the other adults in CH-07. | unreviewed |
| CH-05 | eIDAS | The person signing in | Not stated | Does not choose. | SRC-03 shows "Login with eIDAS" and says a European citizen can access Italian online public services with a national digital identity. It also says that a person who has SPID or CIE should use that to access all available services. It does not say eIDAS is refused for this declaration. SRC-01 and SRC-06 do not name it. | unreviewed |
| CH-06 | Send, when the declarant is the only person moving or the only adult | The declarant | Not stated | This is the send the release hands to the person. The release does not press it. | SRC-01 says that person can send the declaration directly to the comune. SRC-02 names the button "Invio dichiarazione", then "Conferma". A message says that once sent, the declaration can no longer be deleted. "Annulla" cancels the send. After "Conferma", a message says the declaration has been sent, and the person can download a copy. SRC-01 does not name the buttons. | unreviewed |
| CH-07 | Send, when other adults are moving too | The declarant starts it. Each other adult confirms in their own ANPR area. | Not stated | Does not open a case. | SRC-01 says each of those adults must confirm, and the declaration is sent when all of them have confirmed. SRC-02 names "Invio dichiarazione per convalida", then a waiting state, and says those adults sign in with CIE, CNS, or SPID. An opening sentence of the same guide says every adult must confirm, without that split. The later sections match SRC-01. This file does not choose which sentence governs. | unreviewed |
| CH-08 | A new declaration while an earlier one is unfinished | The declarant | Not stated | Records the guide's block. SRC-01 does not state it. | SRC-02 says the service will not send a new declaration until the earlier one has finished. | unreviewed |
| CH-09 | Follow the file, and the notices | The person looks under "Le tue richieste". The notices come to the person. | Not stated | Names the places the pages name. A notice is not acceptance by the comune. | SRC-01 says the person follows the file under "Le tue richieste", and that a notice arrives by email, if an email is in the contacts, and through the IO app. SRC-02 says the person watches the file there. SRC-04 says a person registered on the IO app receives there the updates for an address-change declaration, and for a data-rectification request, submitted through ANPR. It adds that email, set in the user profile of the reserved area, and a digital domicile elected on INAD, remain active. SRC-06 does not say where the person looks, and it does not mention email or IO. | unreviewed |

## The other channels

| ID | Item | Who | Machine integration | First release | Evidence | Review |
|---|---|---|---|---|---|---|
| CH-10 | The Milan form for a foreign national arriving from abroad | Not stated on the link | Not stated | Does not use. That door does not open a case. | SRC-06 gives that service its own "Richiedi" link, to a comune form, not to SRC-03. The steps of that form are not in this file. | unreviewed |
| CH-11 | A form presented to the comune | The applicant. An adult who is moving signs the form. | Not stated | Does not choose this instead of CH-01. | SRC-11 says the anagrafic application is a form presented in person, or sent by registered mail, by fax, or electronically, to addresses published on the comune's site. It does not say those addresses are SRC-03. | unreviewed |

## Product boundary

`MVP_SCOPE.md` says the person reviews the result and submits it on the ANPR cambio di residenza service with their own SPID or CIE. PaperPilot gives the review package and the address in CH-01. It does not take the password, does not press CH-06, and does not file. Opening that page, or receiving a notice under CH-09, is not acceptance by the comune. The product names SPID or CIE. CH-02 through CH-05 do not decide that the other methods on SRC-03 are closed.

## Left for later tasks

TARI stays in Task 13. The day counts stay in [DEADLINES.md](DEADLINES.md).
