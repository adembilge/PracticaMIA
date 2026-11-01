# Existing solutions

Task 3. Compared on 1 November 2026. The question is what a person already has when they need to change a registered address in Milan, and which part of that job is still open.

## What already does the job

**The filing channel is the national registry.** ANPR's citizen service accepts an address change inside the same municipality, a move from another municipality, and the return of an Italian citizen registered with AIRE. It does not accept, through that service, a foreigner arriving from abroad, a move into a convivenza, or a declaration made by a guardian. Those go to the municipal desk. The form asks the user to choose "nuova residenza" or "residenza in famiglia esistente", name the household members, state the title to the home, and attach the residence permit when one is required. Every other adult on the declaration must sign in with their own SPID, CIE, or CNS and confirm it. A second declaration cannot be sent while an earlier one is still open. After sending, "Le tue richieste" shows the file as draft, open, waiting for confirmation, in progress, accepted with reserve, suspended, integrated, finally accepted, cancelled, or inadmissible. Inadmissible includes a wrong address, a missing or unsuitable permit, and an incomplete property section. From 29 January 2024 the Interior Ministry also sends those status changes to the IO app, beside email. Sources: [ANPR cambio di residenza](https://www.anagrafenazionale.interno.it/area-cittadino/cambio-di-residenza/), the [citizen operating guide](https://public-anpr.github.io/anpr-docs-cittadino/src/docs/guide/guida_compilazione_cambio_residenza.pdf), and the [IO notification notice](https://www.anagrafenazionale.interno.it/anpr/notizie/dichiarazioni-di-cambio-di-residenza-e-richieste-di-rettifica-dati-attive-le-notifiche-su-app-io-2/).

**Milan already explains the local door.** The Comune page, updated 16 June 2026, points at that ANPR service, requires SPID or CIE, states the 20-day duty, and links the TARI housing declaration. The page exists in English and nine other languages. Turkish is not one of them. [YesMilano](https://www.yesmilano.it/en/work/getting-started-guide/registering-resident-milano) tells newcomers the other door: people arriving from abroad use a separate municipal platform, while someone already in Italy uses ANPR. The city's 02.02.02 line can book an in-person anagrafe appointment, and YesMilano says that line speaks English.

**People already explain the procedure in English.** [Civiko](https://civiko.it/en) publishes a guide for registering or changing residence: declare within 20 days, on ANPR or at the town hall, free, registration in two working days, checks within 45 days. Its assistant answers from those guides with numbered sources, in English or another language, and finds offices. It says it will not submit an application, will not give legal advice, can be wrong, and asks the user not to type personal data. Commercial explainers such as Spotahome and Trasferirsi in Italia repeat the same fork between the from-abroad form and ANPR.

**A migrant chatbot already answers in the user's language.** [Sportellino](https://sportellino.it/), from the nonprofit Associazione Buonsenso in Rome, is a free assistant on WhatsApp and Telegram. The site says it draws on public sources, checks them with help-desk operators and migration specialists, and publishes only reviewed answers. Global Voices reported on 24 April 2026 that it launched in July 2025, had reached about 10,000 users by March 2026, and is anonymous by design: no account, and it does not ask for sensitive data. Two features that would move it toward PaperPilot are marked "in sviluppo": Passo Passo, guided help filling a form such as the residence-permit postal kit, and Capito, a document scanner that would read a photo and explain deadlines. Neither is offered as a shipped service.

**Permit paperwork already has human and app help.** Patronato and CAF immigration desks in Milan, including the CUB desk and Patronato CAF Milano near Via Padova, prepare permesso, family-reunification, and citizenship files in person and in languages other than Italian. A Questura vademecum treats an address change as a reason to update the permit, and that update asks for a residence certificate that already exists. The [Stato](https://apps.apple.com/us/app/stato-permesso-di-soggiorno/id6752132225) app checks a permit file number against public portals, finds offices, and explains an uploaded letter in the user's language. ItaliaHello's 2025 toolkit points people at Portale Immigrazione and the Questura for permit status.

## Comparison

| Job | Who already does it | What they leave open |
|---|---|---|
| Submit the Milan address change and show its official status | ANPR, with IO and email | The user must already know this is the right door, and must already have SPID or CIE |
| Explain the 20-day, 2-day, and 45-day rules in English | Comune di Milano, YesMilano, Civiko | A general explanation, not a file built from this person's papers |
| Answer a migrant's question in their language, from reviewed sources | Sportellino | Anonymous chat. No stored case. Document reading and guided form-filling are marked in development |
| Answer from a cited guide and refuse to submit | Civiko | The user is told not to enter personal data, so the answer cannot be checked against their lease or permit |
| Update the permit after the address exists, or explain a letter that already arrived | Patronati, Stato | This starts after the anagrafe result, or after a document is in hand |
| Read the lease and the permit, say what is missing, and keep that list until ANPR says suspended, cancelled, or finally accepted | Nobody in this set | This is the open job |

## Gaps worth building

1. **Choose the door before anyone opens ANPR.** The national guide itself says the online service is only the in-Italy move and the AIRE return. Arrival from abroad is a different Milan platform. A shared flat and a move in with a partner are different declarations on the same form. Guides mention the fork. They do not keep a record of which fork was chosen for this person and why.

2. **Check the papers before the file is inadmissible.** ANPR can refuse a file for a missing or unsuitable permit, a wrong address, or an incomplete property section, and it can suspend a file to ask for more documents. That feedback arrives after submission. Sportellino's document scanner and guided kit are not shipped. Civiko asks users not to paste personal data. The open product is a check of the lease, the permit, and the owner's identity document against the declaration this person is about to send.

3. **Stay with the file after it is sent.** ANPR already stores the official status. An anonymous chatbot cannot remember that this user is waiting on another adult's confirmation, a home visit, or a suspension. The open product is the user's copy of the case: which documents were uploaded, what is still missing, and what the latest official status means. It does not replace "Le tue richieste" or IO.

## What is not a gap

- Building another way to submit the declaration. ANPR is the channel, and the vision already leaves authentication and submission with the user.
- A general multilingual FAQ for life in Italy. Sportellino and Civiko already do that, and Sportellino already has users and a reviewed knowledge base.
- Filing the permesso postal kit. Patronati do it in person. Sportellino has aimed Passo Passo at that kit, and it is still in development. The Questura update also depends on a residence certificate, so it sits after this procedure.
- Status notifications. Email and the IO app already carry ANPR state changes.

## Assumption this comparison adds

The useful product is the case around one Milan declaration, not a better chatbot. That assumption fails if people who can read Civiko's residence guide and sign in to ANPR complete the change without a document check or a stored case. The Task 2 interviews should ask what people already used, including a patronato, YesMilano, a WhatsApp bot, or the ANPR form alone.
