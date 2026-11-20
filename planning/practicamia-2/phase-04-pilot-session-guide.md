# Phase 4 pilot session guide

Use this guide with the [three-authority pilot scope](phase-04-three-authority-pilot.md) for Task 40. The briefs are fictional rehearsal material. Keep participant notes and held-out cases in the approved private research location.

## Before the session

- Record the exact isolated Preview build and language. Check that the agent can open and resume a synthetic task on that build.
- Confirm the product owner's scope decision and the applicable reviewed sources for each participant case. Verify the approved IDs on the same build. For Torino and Questura, use the recorded scoped human decisions from the [claim review worksheet](phase-04-claim-review-handoff.md). If a required claim remains pending, keep that case in staff rehearsal and test that the application withholds unsupported guidance.
- Use a dedicated Preview test account and fictional case data. Ask permission to record de-identified usability observations through the [existing consent process](phase-02-user-case-sampling.md#screening-and-intake). Keep consent records separately from the observations.

## Give the participant one brief

Start every scenario in the same chatbot with its composer empty. Show the brief in the participant's preferred language. Ask them to describe the goal in their own words, answer every follow-up in the conversation using the brief, and identify the next step from its inline action card. Do not navigate to a separate PracticaMIA dashboard, saved-case details, source page, document workspace or Preview UI. The selected Phase 4 scenarios finish at the in-chat handoff; actual government sign-in, payment and submission are external and untested here. Later phases will exercise in-chat document uploads, field reviews, form preparation and case tracking.

| Scenario | English brief | Brief in italiano |
| --- | --- | --- |
| Milan residence change | You are an adult Italian citizen already registered in Italy. You are moving alone to Comune di Milano. The registered private rental agreement is in your name and you are creating a new household. Find out how to start your address change. | Sei un cittadino italiano maggiorenne già iscritto all’anagrafe in Italia. Ti trasferisci da solo nel Comune di Milano. Il contratto di affitto privato è registrato e intestato a te, e formerai un nuovo nucleo. Scopri come avviare il cambio di residenza. |
| Torino marriage banns | You and your partner are adults, live in Torino, are registered residents there and have never been married. You plan a civil ceremony in Collegno. Find out where to start the banns request and how the other municipality is involved. | Tu e la persona che vuoi sposare siete maggiorenni, residenti a Torino e non siete mai stati sposati. Avete in programma un matrimonio civile a Collegno. Scoprite dove iniziare la richiesta delle pubblicazioni e come interviene l’altro Comune. |
| Milano Questura appointment | You are an adult registered in the province of Milano. You already filed the renewal of your code 16 employment permit at a postal branch with Sportello Amico. Your fictional letter gives the date, time and place of an appointment. Find out where you are in the process and what you would do next. | Sei maggiorenne e risiedi nella provincia di Milano. Hai già presentato la domanda di rinnovo del permesso per lavoro subordinato, codice 16, in un ufficio postale con Sportello Amico. Una lettera di esempio indica la data, l’ora e il luogo di un appuntamento. Scopri a che punto sei e cosa faresti dopo. |

For the appointment case, supply a plainly fictional summons marked as a test exercise. Use a synthetic date, time and venue label and name the Milano Questura immigration office. Omit personal details, real addresses, tracking codes and identity numbers.

## Observe the task and resumption

1. Give the same opening instruction for each run. Let the participant use normal product controls without hints. If help is needed, record the first hint and when it was given.
2. Ask the participant to explain the next step and the responsible body in their own words before sharing the expected outcome.
3. Ask them to close the task and reopen it. Record the state before and after and whether they can continue independently. A reopened task should retain the same confirmed facts and guidance, or the same unanswered question if interrupted earlier. Record a changed or stale handoff explicitly.

| Scenario | Expected participant outcome on a reviewed build | Staff rehearsal variant |
| --- | --- | --- |
| Milan | Identifies Milan's registry office and reaches the signed ANPR handoff after confirming the saved intake. Explains that the applicant submits in ANPR. | Keep the intake as a draft. The application requests confirmation and withholds the verified handoff. |
| Torino | Identifies Torino's banns office and municipal service as the starting point. Explains that the registrar sends the delegation to Collegno after publication. | Provide only the ceremony municipality and omit registered residence. The application asks for residence before choosing the receiving office. |
| Questura | Distinguishes the completed postal intake from the immigration office appointment and uses the fictional summons for the date, time and venue. | Provide only a receipt or a letter saying an appointment will follow. The application leaves the date, time and venue unresolved. |

A participant run meets the primary outcome when the participant reaches the expected action within the same chat UI without a hint, explains the competent body and next step, and the application shows current reviewed citations for that action. Report resumption separately. Record an assisted, incorrect or stopped attempt with the outcome observed. Keep a run blocked before launch by a missing review or an unavailable build separate from started attempts. A safe clarification or withholding result in a staff variant provides rehearsal evidence.

## Record one row per attempted scenario

| Record | Fields |
| --- | --- |
| Run context | Anonymous session ID, scenario, session date, stage (staff or participant), language, device, exact build and warm or cold start |
| Task outcome | Expected and observed authority and next action, unassisted or helped, first help point, whether the participant could explain the result, and any unresolved misroute |
| Evidence and resumption | Displayed version and passage IDs, whether they supported the result, state before closing, state at reopen, and whether the participant continued unaided |
| Performance | Elapsed time to the first visible response and to verified guidance, model calls, tool calls and billed cost as defined in [pilot measurements](../../docs/MILAN_PILOT.md#agent-performance-observations). Mark missing measurements and any guidance that never appeared. |
| Follow-up | Short de-identified issue description, failure step, fix reference and retest outcome when available |

Report counts of attempted cases and unassisted successes by authority with the build and language coverage. Include blocked cases, failures and unavailable guidance. Keep the submitted messages, credentials, notices, screenshots and consent records out of shared results. This guide records zero participant sessions.
