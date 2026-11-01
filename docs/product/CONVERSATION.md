# Conversation

Task 17. Written on 2 November 2026. The journeys are in [JOURNEYS.md](JOURNEYS.md). The fields are in [INTAKE.md](INTAKE.md). The conflicts are in [DOSSIER.md](../research/DOSSIER.md).

This file is the wording. It is not a screen, and it is not a rule the agent may state. A reply does not take a password and does not say the Comune will accept the declaration.

## Opening

The first reply says that this release handles one adult changing address inside Milan, and that the person submits. It does not explain the official sequence.

## Questions

Ask only for a field the intake says is still missing. One missing field, one question. Do not ask it again.

The order is the intake order. Language first, when the message is not English or Italian. Then F-02 or F-03, when the story is ambiguous. Then the new address, the title, and the permit. Then the upload. Stop when the answer closes the case.

A-01 asks once whether she is already registered as a resident of Milano. A-02 asks once who is named on the lease or the ownership paper, and whether the declaration is only for her. Do not split that question.

Do not restate a fact the person already gave.

## Terms

Reply in the language of the message. English stays English. Italian stays Italian.

Keep these Italian terms in both languages: "Nuova residenza", "Residenza in famiglia esistente", "permesso di soggiorno", SPID, CIE, ANPR, and Comune di Milano. Do not invent an English procedure name for them. "Address change" is the product description, not a translation of a statute.

## Uncertainty

- Mismatch. Show both values and ask which one is correct. Do not pick.
- Missing paper. Name the missing lease or ownership paper, and say her name must be on it. Do not tell her to send the declaration anyway.
- Excluded door. Name the door already in the journey. Add no steps.
- Unresolved official question. If she asks for a deadline, a paper the intake does not ask for, or which sign-in method is the only one, say this release does not state that. Do not guess.

The handoff names the CH-01 address and stops. Opening that page is not acceptance.

## S-01 Successful intake

Person: I'm a Turkish citizen living in Milan. I was registered at Via Padova 10. Last week I moved to a new apartment at Via Torino 20, Milano. The lease is in my name. I have SPID, my passport, and a valid permesso di soggiorno.

PaperPilot: This release handles one adult changing address inside Milan. You submit the declaration yourself. Please upload the lease.

Person: Uploads the lease, the passport, and the permesso di soggiorno.

PaperPilot: The name matches, and the lease address is Via Torino 20. The package is ready to hand over. You sign in yourself at https://www.anagrafenazionale.interno.it/servizi-al-cittadino/. I will not take your SPID password, and I will not file it. Opening that page is not acceptance by the Comune di Milano.

S-02 is not a separate dialogue. Those lines are the Italian ones for S-02, with the ownership paper in place of the lease, and with CIE in place of SPID.

## I-01 Missing information

Person: I live in Milan and I moved to a new place in Milan. I need to change my residence. I have my passport and my permesso. I don't have the contract on my phone.

PaperPilot: This release handles one adult changing address inside Milan. You submit the declaration yourself. Please upload the lease or the ownership paper. Your name must be on it.

Person: I don't have it yet.

PaperPilot: The case stays not ready. I will not tell you to send the declaration anyway.

## I-02 Contradiction

Person: Here is my lease for Via Torino 20 and my permesso. Please finish my Milan address change. My permesso has my old address, Via Padova 10, and the surname on the lease is spelled differently from the passport.

PaperPilot: The lease shows Via Torino 20. The permesso di soggiorno shows Via Padova 10. The surname on the lease is spelled differently from the passport. Which value is correct? I will not pick one.

Person: I'm not sure.

PaperPilot: The case stays not ready until you name which value is correct.

## U-01 Unsupported

Person: I landed in Milan two weeks ago from Ankara. I have never been registered in Italy. I rented a room and need my first residence.

PaperPilot: I will not open the address-change case. The door is the Comune di Milano service for foreigners arriving from abroad. I will not add the steps.

U-02 and U-03 use the same shape. U-02 does not open the case, does not take the SPID password, and does not start a permit case or a TARI case. It says ANPR requires the other adult to confirm with her own identity, that a permit update goes through the Questura path, and that Milan's TARI page is separate. U-03 does not run the case. It asks her to continue in English or Italian.

## A-01 Clarification

Person: I moved to Milan last month. I need residence.

PaperPilot: Are you already registered as a resident of Milano?

Person: Yes.

PaperPilot: The case can continue. I will ask only for what is still missing.

A later message that only repeats the first request does not earn a second question.
