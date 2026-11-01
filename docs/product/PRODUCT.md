# PaperPilot product specification

Task 6. Accepted on 1 November 2026. This file is the Stage 1 specification. It consolidates the product documents below. It does not add procedures.

- Problem, audience, and objectives: [VISION.md](VISION.md)
- Evidence and untested assumptions: [USER_PROBLEMS.md](USER_PROBLEMS.md)
- What already exists, and the three open gaps: [EXISTING_SOLUTIONS.md](EXISTING_SOLUTIONS.md)
- The only supported case, and the exclusions: [MVP_SCOPE.md](MVP_SCOPE.md)
- The nine reference requests: [SCENARIOS.md](SCENARIOS.md)

## Audience and promise

The first release is for an adult already registered as a resident of the Comune di Milano who has moved to another address in Milan and occupies it as the owner or as the person named on the lease. The reference person is a foreign resident, such as a Turkish citizen. Italian, EU, and non-EU residents fit the same case when the conditions in `MVP_SCOPE.md` hold. A non-EU resident must already have a residence permit that can be attached.

The person describes the move in English or Italian. PaperPilot decides whether the intra-Milan declaration is the right door, asks only for what is still missing, checks the papers they upload, and returns a review package plus the official ANPR address. They sign in with their own SPID or CIE and submit themselves.

English and Italian stay the assistant languages for this release. Turkish is the reference person's language and is not a product language yet. Whether a later release adds it depends on the interviews in `USER_PROBLEMS.md`, not on this specification.

## First-release features

Only the three gaps in `EXISTING_SOLUTIONS.md`:

1. **Choose the door.** Separate the supported intra-Milan change from an arrival from abroad, a move from another municipality, a family declaration, and a guest stay. Open a case only for the single-adult intra-Milan change.
2. **Check the papers.** Compare the lease or ownership paper and the identity or permit document with the name and the new address before the case can be marked ready.
3. **Keep the case.** Remember the conversation, the uploads, what is missing, and the review package across sessions, until the person has the official ANPR address. This does not replace ANPR status or the IO app.

## Requirements

- A requirement the agent states about documents, deadlines, or eligibility must come from the Stage 2 dossier. Until that dossier exists, the agent must not state one.
- A missing, unreadable, or contradictory paper blocks "ready to submit." The agent must not pick a value when two documents disagree.
- An ambiguous story gets one question, then a classification. The questions are the ones in A-01 and A-02.
- An excluded request does not open the address-change case. When `EXISTING_SOLUTIONS.md` already names an official door, the agent points to that door and does not invent the steps.
- The agent does not take a SPID or CIE password, does not file the declaration, and does not promise that the Comune will accept it. The municipality can still cancel a registration during its check.

## User outcomes

- A person in the supported case can see whether their papers agree, what is still missing, and the ANPR address they will use.
- A person outside the case is stopped before a checklist is built, and is told where to go when that door is already known.

## Success metrics

The release passes only when all nine requests in `SCENARIOS.md` behave as specified:

- S-01 and S-02 become ready to hand over only when the uploaded papers agree on the name and the new address.
- I-01 and I-02 stay not ready.
- A-01 and A-02 ask one question, then classify the answer as supported or excluded.
- U-01, U-02, and U-03 do not open the address-change case and do not invent a procedure.

After the Stage 2 dossier exists, every procedural claim in a review package traces to a source in that dossier. A claim with no source fails the release. Numeric model-accuracy targets are not set here. They belong to the later evaluation stage.

## Not in this release

Exclusions are the list in `MVP_SCOPE.md`. They are not repeated here. The first case to add later is a declaration that includes another adult.

## Still open

The seven assumptions in `USER_PROBLEMS.md` are untested. No interview has been done. Stage 2 must confirm documents, deadlines, and exceptions before the agent may state them. The wording of this specification was accepted on 1 November 2026, so Stage 1 is complete.
