# Residence-change procedure

Task 8. Mapped on 1 November 2026 from the service pages re-opened that day. Source ids are in [SOURCES.md](SOURCES.md). This is the sequence those pages show. It is not the dossier, and it is not a rule the agent may state.

The eligibility branches, the document checklist, the deadline table, the authentication detail, and TARI stay in Tasks 9–13. Where two pages do not use the same words, both are kept.

## 1. The door

SRC-01 is the ANPR cambio di residenza page. It addresses people already registered in the Anagrafe Nazionale who have changed home inside the same comune, moved to another comune, or returned to Italy from abroad as Italian citizens registered with AIRE. The service sends a declaration, for the person and for the members of their registered family who move with them, to the comune that receives the new address.

SRC-06 is the Comune di Milano page for the same ANPR service. It addresses Italian and foreign people who arrive from another Italian comune or change address inside Milan, and Italian people who have returned from abroad and are registered with AIRE. It does not say the person must already be registered in ANPR.

SRC-08 is a different Milan page. It addresses foreign people arriving from abroad, and its request button leaves ANPR. This map stops at that door.

SRC-01 does not name a door for a foreign national arriving from abroad, a move into a convivenza, or a declaration by a guardian. SRC-02, the citizen guide, says those three go to the municipal desk. SRC-06 points the from-abroad case at SRC-08, which is an online Milan form, not a desk. The guide was not linked from SRC-01 on this date.

## 2. Sign in

The first heading on SRC-01 is "Vai al servizio": open the services and select "Cambio di residenza". That link and the "Richiedi" link on SRC-06 both go to SRC-03.

SRC-06 says access requires SPID or CIE. SRC-03 shows four ways in: CIE, SPID, CNS (and it also names the Tessera Sanitaria), and eIDAS. SRC-01 does not name a method. This map does not decide which of the four SRC-03 shows can be used for this declaration.

## 3. The declaration

SRC-01 then shows four headings, in this order:

1. Choose the type. "Nuova residenza" is a home where nobody else lives, or where the other people are not relatives or partners. The page's example is students sharing an apartment. "Residenza in famiglia esistente" is a home where the other people are relatives or partners. The page's example is a couple.
2. Select the members of the current registered family who are moving, and enter the data the form asks for each of them.
3. Enter the new address, the title to occupy the home, and contact details.
4. Attach what the person considers useful for the comune, check the summary, and send.

SRC-01 also has a "Cosa serve" section with examples of what to have at hand. The checklist is Task 10. It is not copied here.

SRC-02 uses the same two types, with the same examples, and the same stretch: people, new address, title to the home, attachments, summary, send. It splits the new-home step into an address section, a title section, and a separate contact section. SRC-01 puts contact details in the new-home step and does not describe that contact section. The guide's contact section mentions a time band for a check by the municipal messenger. SRC-01 and SRC-06 do not.

SRC-02 also says the service will not send a new declaration while an earlier one is still unfinished, and that changing the declaration type deletes what was already entered. SRC-01 does not say either of those.

## 4. Other adults

After the data is entered, SRC-01 splits the send:

- If the declarant is the only person moving, or the only adult among the people moving, the declarant sends the declaration to the comune.
- If other adults in the family are also moving, each of them must enter their own ANPR area and confirm the data. The declaration is sent automatically when every adult has confirmed.

SRC-02 has the same split in its summary sections. The solo case uses "Invio dichiarazione". The case with other adults uses "Invio dichiarazione per convalida", stays waiting, and is sent to the comune only after every adult confirmation. An opening sentence of the same guide says every adult must confirm, without that split. The later sections match SRC-01. This map does not choose which sentence in the guide governs.

SRC-02 says those other adults sign in with CIE, CNS, or SPID. SRC-01 does not name the method.

## 5. After it is sent

SRC-01 says the competent anagrafe office handles the declaration. The person follows it under "Le tue richieste". The page also says a notice arrives by email, if an email is in the contacts, and through the IO app. It says the declaration is free. SRC-06 does not say where the person looks, and it does not mention email, IO, or a fee.

SRC-04 says that from 29 January 2024 a person registered on the IO app receives there the updates for an address-change declaration, and for a data-rectification request, submitted through ANPR. It says this is in addition to email, which can be set in the user profile of the reserved area, and to a digital domicile elected on INAD. SRC-05 is the Interior Ministry circular, DAIT n. 3/2024, that SRC-04 cites for that IO channel. The older circulars linked from SRC-05 were not opened.

SRC-06 says the legal effects of the registration start on the date the declaration is presented. If the checks are negative, the procedure stops. The Comune sends a communication, and the person can reply with memories or documents useful to the file. A false declaration is reported to the judicial authority. SRC-01 does not describe that negative path.

SRC-02 says the person watches the file under "Le tue richieste" and names working states there. SRC-01 names the section and does not list states. Those state names stay in the guide. They are not steps of this map.

## 6. Where the pages do not say the same thing

These are left side by side. Task 11 is the deadline table. This file does not decide which wording applies.

- Who may use the ANPR service. SRC-01 says people already registered in ANPR. SRC-06 says Italian and foreign people, and does not say they are already registered. Both name a move inside the comune, a move from another comune, and an AIRE return.
- What happens at the Comune. SRC-01 says the comune must register the declaration and accept it with reserve within 2 days of receipt, then a verification phase of at most 45 days. If the outcome is positive, the comune accepts it definitively with effect from the date of presentation. SRC-06 says the registration happens in the two working days after the declaration, and that the Comune then checks the requirements. It does not say "with reserve" or "45 days".
- The 20-day communication. SRC-06 says a person who changes city or address must tell the anagrafe office within 20 days of the move. SRC-01 does not say that.
- The from-abroad door. SRC-02 sends it to the municipal desk. SRC-06 sends it to SRC-08.

## 7. What the first release uses

[MVP_SCOPE.md](../product/MVP_SCOPE.md) keeps one stretch of the ANPR path: one adult already registered in Milan, moving to another address in Milan, occupying it as the owner or as the person named on the lease. The official service, on SRC-01 and SRC-06, also names a move from another comune and an AIRE return. Those remain on this map. They are not cases the first release opens. The two declaration types in section 3 stay on the map because they are the form's first question. The household branches are Task 9.

## 8. Not mapped here

SRC-06 names the TARI housing declaration, SRC-10, as something to file when the address changes. That form is Task 13 and is outside this release.

SRC-16 is a pointer, not a step. The English Milan service page did not open. The statutes SRC-12 through SRC-15 were not used for this sequence.
