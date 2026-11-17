# PracticaMIA 2.0 — Phase 2 · User research, scope, and product contract

**Roadmap tasks 11–20.** This phase identifies a real administrative obstacle PracticaMIA can help a user overcome and turns the findings into a development contract for the first release. Under the Italy-wide product scope, the first pilot tests one agent across different authorities, regions, and document types.

## 11. Collect real user cases

- **11.1** Aim for approximately 20 cases from people new to Italy, students, employees, families, and small business owners. Include different levels of Italian proficiency, locations, and ability to use digital services.
- **11.2** Study recently completed, ongoing, and abandoned tasks. Capture the completed route, the next uncertainty in ongoing work, and the point at which an abandoned task stopped.
- **11.3** Use the same core interview questions. Ask what the user did first, how they chose the authority, where they got stuck, whom they asked, and what remains. Record their opening sentence in their own words.
- **11.4** With permission, reconstruct the steps using a redacted official notice, portal screenshot, form, or receipt. Record what the screen showed and what the user understood.
- **11.5** Identify the underlying obstacle, such as choosing the authority, understanding Italian terminology, applying a document list, filling a field, or tracking a case.
- **11.6** Define the specific work the agent can take on. For example, highlight the requested attachment, match it against an available file, and find the submission channel.

**Output and acceptance.** Each case card contains an anonymous ID, opening sentence, authority, location, stage, obstacle, evidence, current workaround, and expected outcome. Each proposed feature relates to an observed obstacle. The case count is a discovery target and does not estimate demand across Italy.

See the [11.1 sampling plan and case card](phase-02-user-case-sampling.md) for recruitment targets and collection status, the [11.2 outcome instructions](phase-02-user-case-sampling.md#record-the-case-outcome) for what to capture at each stage, the [11.3 core interview questions](phase-02-user-case-sampling.md#core-interview-questions) for the shared English and Italian prompts, and the [11.4 evidence instructions](phase-02-user-case-sampling.md#reconstruct-steps-with-redacted-evidence) for reconstructing steps from redacted material.

Use the [11.5 obstacle instructions](phase-02-user-case-sampling.md#identify-the-underlying-obstacle) to record what impeded the participant’s progress and the evidence for that assessment. The [11.6 agent work instructions](phase-02-user-case-sampling.md#define-what-the-agent-can-do) connect the obstacle to a specific action the agent could take.

## 12. Map Italian administrative domains

- **12.1** Include immigration and residence permissions, civil registration and identity, healthcare, education, employment, social benefits, tax, family, transport, and business procedures.
- **12.2** Map everyday expressions to official procedure candidates. Record examples where one expression can refer to several procedures.
- **12.3** Record national, regional, and municipal responsibilities. Identify what location or situation detail is needed to determine the competent body.
- **12.4** Map official portals, authority pages, offices, appointments, and in-person services using observed cases.
- **12.5** Identify actual prerequisites, shared documents, and parallel tasks where a life event initiates multiple procedures.

**Output and acceptance.** The map contains a domain, user phrasing, procedure candidate, authority, jurisdiction, channel, and open questions. It includes cases where the same phrasing leads to different routes by place or circumstance.

The [administrative domain map](phase-02-administrative-domains.md) lists a reference task and an official source for each of the ten domains in 12.1. The [12.2 procedure candidates](phase-02-administrative-domains.md#map-everyday-phrasing-to-procedure-candidates) map everyday Italian and English to official procedures and show how to clarify ambiguous goals.

## 13. Define how conversations start and progress

| User input | Agent's first job | Visible result |
| --- | --- | --- |
| Question | Identify the term and context | Explanation, source, and a follow-up if needed |
| Goal | Identify relevant procedures and priorities | First action and a question that could change it |
| Official notice or screenshot | Identify the authority and request | Action and its location in the document |
| Form | Identify the form, field, and version | Field meaning and a value the user can verify |
| Receipt | Determine what the document proves | Submission evidence and tracking step |

- **13.1** Write ordinary, incomplete, and wrong-context conversations for each input type.
- **13.2** Ask clarifying questions for information that changes the answer. Give general explanations directly when possible.
- **13.3** When the user does not know, show where the information can be found and continue with what can be done.
- **13.4** Identify multiple tasks in one message. Show the active task and support returning to its context after switching topics.

**Acceptance.** A user starts with free text. The agent advances the task or asks only for missing information that changes the outcome.

## 14. Score the first workflows to develop

| Criterion | Proposed weight |
| --- | ---: |
| Observed need | 30 |
| Concrete progress the agent can provide | 25 |
| Official evidence quality | 20 |
| Reusability across procedures | 15 |
| Feasibility in the first pilot | 10 |

- **14.1** Score each criterion from 0–5 and record the supporting evidence. Reconsider weights as pilot findings arrive.
- **14.2** Assess discovery, document checks, form preparation, and tracking independently.
- **14.3** Record the consequences of wrong answers and external dependencies. Prioritize wrong dates, recipients, and unverified forms.
- **14.4** Check diversity by authority, jurisdiction, and document type. Explain any case added for coverage.

**Acceptance.** The rationale for the first workflows and the evidence needed for deferred capabilities are visible.

## 15. Assemble the first pilot case set

- **15.1** Cover at least three authorities and multiple regions. Include national, locally implemented, and cross-authority procedures.
- **15.2** Include wrong authority, missing attachment notice, unreadable date, obsolete form, and ongoing application scenarios.
- **15.3** Write the expected next action and its official basis. Define acceptable alternatives and unacceptable responses.
- **15.4** Define completion for each case, such as opening the right service, identifying a missing attachment, or confirming a field.
- **15.5** Specify what the agent must reassess when the location changes, a document belongs to another procedure, or a new notice arrives.

**Acceptance.** The pilot tests routing, document-assisted work, and recovery across multiple authorities. Completion can be observed.

## 16. Define a capability contract for each procedure

- **16.1** Record discovery, sourced explanation, document checking, form preparation, and status tracking capabilities per procedure.
- **16.2** Define inputs, evidence, output, and approval conditions for every enabled capability.
- **16.3** When a capability is unverified, define the next useful action. An unverified field mapping can still provide the current official form and explain fields supported by the available evidence.
- **16.4** Define how to show a user-reported status, a submission receipt, and a status verified by the authority.

**Acceptance.** The procedure record tells developers what inputs are accepted, what users will see, and where approval is required.

## 17. Define success metrics and a comparison test

- **17.1** Use unassisted arrival at the correct next step as the primary outcome. The user should identify the correct authority and explain their next action in their own words.
- **17.2** Track time, misrouting, unnecessary questions, wrong documents, and successful return to ongoing work.
- **17.3** Run comparable cases using the current method and PracticaMIA. Record prior experience and moderator help.
- **17.4** Measure assisted and unassisted completion separately.
- **17.5** Set thresholds before the first test. Report case and participant counts alongside percentages in a small pilot.

**Acceptance.** The results show how far users advanced their actual tasks.

## 18. Design critical-error and recovery behaviour

- **18.1** Define distinguishing questions for the wrong authority, municipality, or a procedure with the same name.
- **18.2** Specify what users must verify when they encounter an obsolete form, broken link, conflicting source, or different form version.
- **18.3** Define visible evidence and recovery for missing pages, blurry dates, and documents from a different case.
- **18.4** Use separate examples for PDF creation, a user's statement, a receipt, and an authority decision. Specify the state transition each supports.
- **18.5** Record input, expected behaviour, unacceptable output, and preservation of existing records for each case.

**Acceptance.** Critical cases can become agent, document, source, and UI regression tests.

## 19. Define language, tone, and interface rules

- **19.1** Start with Italian and English. Test equivalent cases reaching the same authority and next step in both languages.
- **19.2** Preserve official Italian field names and show the explanation in the user's language.
- **19.3** Answer the question in the first sentence. Show the next task as an action and make source and document details expandable.
- **19.4** Preserve case, document, and field links when language changes mid-conversation.
- **19.5** Define clear clarification behaviour for another language or an ambiguous expression.

**Acceptance.** Users in both evaluation languages reach the same next action and recognise the original labels on the official portal.

## 20. Test the single-chat prototype and close the phase

- **20.1** Use chat as the main screen. Make the next action, official source, and document or form review accessible from the same case.
- **20.2** Start from an actual official notice. Observe the agent explain the request, point to the passage, ask for missing information, and help prepare the next action. Let the user correct a value.
- **20.3** Try a free-text question involving another authority to verify reuse of the same chat, source, and next-action components.
- **20.4** Close and reopen the case. Let the user find the prior correction, next step, and official channel without explaining the case again.
- **20.5** Connect each observed bottleneck to catalogue, agent, document reading, or interface requirements. Turn findings into inputs for phases 3 and 4.
- **20.6** Record pilot scope, uncertainty, and retest requirements. Make clear which observed behaviours used a prototype and which worked end to end.

**Acceptance.** A user can start with an observed need and reach the right next step. Phase 3 receives anonymised case cards, the procedure map, capability contracts, prioritised pilot cases, the measurement plan, critical-error tests, and single-chat prototype findings.
