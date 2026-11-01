# MVP boundaries

Task 4. This is the first-release list. It is a product boundary, not a certified reading of the law. Stage 2 still has to confirm documents, deadlines, and exceptions against official sources before any of this becomes a rule the agent may state.

The reference case is the one in the vision: an adult already living in Milan who has moved to a new apartment in Milan and must update their registered address. The example person is a Turkish citizen. Italian, EU, and non-EU residents fit the same case when the conditions below hold.

## Supported

All of these are required:

- The person is 18 or older and files only for themselves.
- They are already registered as a resident of the Comune di Milano.
- The new habitual address is also in the Comune di Milano.
- They will occupy that home as the owner, or as the person named on the lease.
- A non-EU resident already has a residence permit that can be attached. This release does not obtain or renew the permit.
- The assistant works in English and Italian.
- The person reviews the result and submits it themselves on the ANPR cambio di residenza service, with their own SPID or CIE.

What the release does for that case: identify this procedure, list the information and documents the declaration needs, check uploaded copies of the lease or ownership paper and the identity or permit document, say what is missing or inconsistent, and hand the person the official ANPR address. It keeps that case across sessions.

## Excluded

PaperPilot does not open a case for any of these. It names the official door when one is already known from Task 3, and it does not invent the steps.

| Case | Where the person goes instead |
|---|---|
| First registration in Milan by someone arriving from abroad | The Comune di Milano platform for foreigners arriving from abroad, described by YesMilano |
| Move into Milan from another Italian municipality | ANPR supports this declaration. It is out of this release because the reference case is a move inside Milan |
| Return to Italy of an Italian citizen registered with AIRE | ANPR, outside this release |
| Move into a convivenza, or a declaration made by a guardian | The municipal desk. The ANPR citizen guide says the online service does not take these |
| A declaration that includes another adult, or "residenza in famiglia esistente" (moving in with a partner or relatives already at the address) | ANPR. Other adults must confirm with their own digital identity. This is the first case to add after the single-adult release works |
| Occupying the home only as a guest, or under a title other than owner or named tenant | Not in this release. The document set is not confirmed |
| No residence permit, or a permit that cannot be attached, for a non-EU declarant | The permit has to be resolved before this declaration. Patronati and the Questura handle permit files. This release does not |
| Updating the permit, TARI, the health service, the identity card, the tax code, or citizenship because the address changed | Those procedures stay out. Milan's page links TARI. Task 13 keeps it out unless you approve it |
| Creating SPID or CIE | The person needs one to submit. This release does not create it |
| A language other than English or Italian for the assistant | Out of this release. Turkish is the reference person's language and is not a product language yet. Milan's own page already has other languages, and Turkish is not among them |

## Stop inside a supported case

- The story is ambiguous between "I already live in Milan" and "I just arrived." Ask once. If it is arrival from abroad, close the case as excluded.
- A required document is missing, unreadable, or contradicts the address or the name. Do not mark the case ready to submit.
- The person asks PaperPilot to sign in, file, or promise that the Comune will accept the declaration. Refuse. The ANPR check can still cancel the registration within 45 days.

## Done for this task

Supported and excluded cases are listed. The single-adult, already-resident, owner-or-named-tenant move inside Milan is the only case the first release runs. Reference requests are in `SCENARIOS.md`.
