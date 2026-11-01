# Reference scenarios

Task 5. These are fictional requests for the first release. Names, addresses, and document numbers are made up. Each scenario states the class, the facts the person has already given, and what PaperPilot does. It does not state a document checklist beyond `MVP_SCOPE.md`. Stage 2 still has to confirm the official requirements.

Classes:

- **Successful.** The case is in scope and the papers agree. PaperPilot can hand over a review package and the ANPR address.
- **Incomplete.** The case is in scope. Something required is missing or inconsistent, so it is not ready to submit.
- **Ambiguous.** One question decides whether the case is supported. Ask that question once.
- **Unsupported.** The request is outside `MVP_SCOPE.md`. Do not open the address-change case. Name the official door when Task 3 already recorded one.

PaperPilot never signs in to ANPR, never files the declaration, and never says the Comune will accept it.

## Successful

### S-01 Tenant, English

> I'm a Turkish citizen living in Milan. I was registered at Via Padova 10. Last week I moved to a new apartment at Via Torino 20, Milano. The lease is in my name. I have SPID, my passport, and a valid permesso di soggiorno. Help me update my registered address.

Facts: one adult, already resident in Milan, new address in Milan, named tenant, permit can be attached, English. Uploads of the lease, passport, and permit show the same name, and the lease address is Via Torino 20.

Does: open the case, treat it as an intra-Milan change filed only for her, check the three uploads, produce the review package, give the ANPR cambio di residenza address, keep the case.

Does not: submit the declaration or update the permit.

### S-02 Owner, Italian

> Sono residente a Milano in via Solari 4. Ho comprato un appartamento in via Savona 12, sempre a Milano, e ci abito da dieci giorni. Ho la CIE e l'atto di proprietà. Devo aggiornare la residenza, solo per me.

Facts: one adult, already resident in Milan, new address in Milan, owner, Italian, CIE. The ownership paper shows her name and via Savona 12.

Does: the same path as S-01, in Italian, with the ownership paper instead of a lease.

## Incomplete

### I-01 No proof of title

> I live in Milan and I moved to a new place in Milan. I need to change my residence. I have my passport and my permesso. I don't have the contract on my phone.

Facts: the story matches the supported case, but there is no lease or ownership paper.

Does: keep the case open, ask for the lease or the ownership paper, and say whose name must be on it. Leave the case not ready.

Does not: tell her to send the ANPR declaration anyway.

### I-02 Papers disagree

> Here is my lease for Via Torino 20 and my permesso. Please finish my Milan address change. My permesso has my old address, Via Padova 10, and the surname on the lease is spelled differently from the passport.

Facts: supported case, documents uploaded, name or address does not match across them.

Does: show the mismatch and leave the case not ready until she confirms which value is correct. Do not silently pick one.

## Ambiguous

### A-01 Already here, or just arrived

> I moved to Milan last month. I need residence.

Facts: "Milan" and "residence" are not enough. This may be a first registration from abroad, a move from another municipality, or an intra-Milan change.

Does: ask once whether she is already registered as a resident of Milano. If yes, continue as a supported case and collect the rest. If she arrived from abroad and was never registered in an Italian municipality, close it as unsupported and point to the Comune platform YesMilano describes. If she was registered in another Italian municipality, close it as unsupported for this release and point to ANPR without running the case.

### A-02 New lease, or moving into someone's home

> I moved in with my girlfriend in Isola. The apartment is in Milan. Can you do my residence?

Facts: the new address is in Milan. It is not yet known whether she is already registered in Milan, whether she is the named tenant or only a guest, and whether the girlfriend must be on the declaration.

Does: ask once who is named on the lease or the ownership paper, and whether the declaration is only for her. Named tenant or owner, already resident in Milan, filing alone: continue. Guest, or a declaration that includes the girlfriend: unsupported for this release. Point a family move-in to ANPR and say each adult confirms with their own identity.

## Unsupported

### U-01 Just arrived from Turkey

> I landed in Milan two weeks ago from Ankara. I have never been registered in Italy. I rented a room and need my first residence.

Does: do not open the case. Point to the Comune di Milano service for foreigners arriving from abroad.

### U-02 Whole household, and the permit

> My wife and I both moved from our old Milan apartment to a new one. Put both of us on the declaration, file it with my SPID, and update our permessi and the TARI.

Does: do not open the address-change case, because another adult is on the declaration. Do not take the SPID password. Do not start a permit case or a TARI case. Say that ANPR requires the other adult to confirm with her own identity, that permit updates go through the Questura path, and that Milan's TARI page is separate.

### U-03 Turkish only

> Milano'da yeni bir daireye taşındım. İkamet adresimi güncellemem gerekiyor.

Facts: the words describe an address update in Milan. The message is Turkish.

Does: not run the case in Turkish. Ask her to continue in English or Italian. Milan's service page does not include Turkish either, so do not send her to a Turkish version of that page.

## Count

Nine requests: two successful, two incomplete, two ambiguous, three unsupported. U-02 is one request that tries to cross three excluded lines at once. A later test run can split it.
