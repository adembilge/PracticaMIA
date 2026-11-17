# Phase 3.1 — Authority roles in the procedure catalogue

[PracticaMIA 2.0 task 21.1](phase-03-official-sources-and-catalog.md#21-model-procedures-authorities-sources-and-evidence) defines how to record the role a body plays in a procedure. The examples build on the [Phase 2 authority map](phase-02-administrative-domains.md#identify-the-responsible-authority).

## Role assignment

Record one relationship for each procedure, body, role and scope. A procedure can involve several bodies, and the same body can hold several roles. Use an office or unit ID when the evidence names that unit. Record an authorised intermediary under its own identity and organisation type when it plays a documented role. A portal, form or counter is a service channel linked to the relevant step.

| Field | Meaning |
| --- | --- |
| `procedure_id` | Stable catalogue ID for the procedure. |
| `authority_id` | Stable catalogue ID for the body or organisational unit. The display name comes from its catalogue record. |
| `role` | One of the roles below. Each assignment makes a single claim. |
| `scope` | Applicable service jurisdiction and any condition that affects the assignment, such as application category, procedure variant or school year. Keep a missing location or condition unresolved. |
| `evidence` | One or more references to the source version and passage supporting the role and scope. Store a URL and section locator on a research candidate until it can be linked to a version and passage. |

| Role | Assign when the source establishes that the body… |
| --- | --- |
| `publishes` | Publishes the service instructions or official procedure material. |
| `receives_application` | Receives the user's submission for the applicable step. |
| `processes_application` | Reviews the filing or performs the documented administrative step. |
| `decides_application` | Is explicitly responsible for the administrative decision. |
| `receives_referral` | Receives a delegation or file from another body for a later step. |

Different role assignments may cite the same passage if it supports each claim. The publisher on a `KnowledgeSource` and the geographical scope of that source can help identify a candidate. Confirm every additional role against the relevant passage. Reuse existing procedure and source IDs where the records refer to the same entities, such as `milan_residence_change` and `milano-residence-change`. See the [current registry and trust checks](../../docs/OFFICIAL_SOURCE_REGISTRY.md).

An assignment can support user-facing guidance when a human review covers that exact role and scope and its cited versions and passages pass the registry's current approval, applicability and integrity checks. When the evidence leaves the receiving body or its jurisdiction ambiguous, keep the candidate unresolved and identify the missing case detail. When a cited version loses approval, revalidate the assignment before using it again. Preserve the old reference in case history.

## Worked catalogue examples

These research examples show how to represent the published roles. The [Phase 2 collection record](phase-02-user-case-sampling.md#collection-status) has no enrolled participants or eligible cases. The evidence below uses public page locators and awaits review for these catalogue assignments.

| Procedure and scope | Body | Role | Evidence locator |
| --- | --- | --- | --- |
| Change of registered residence, destination Milan | Comune di Milano | `publishes` | [Cambio di residenza](https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza), municipal service page |
| Change of registered residence, destination Milan and prior registration in Italy | Ufficio Anagrafe, Comune di Milano | `receives_application` | [Come chiedere/cambiare residenza?](https://servizicrm.comune.milano.it/centro-supporto/KA-00330/), opening paragraph on the route for people already registered in Italy |
| Change of registered residence, destination Milan | Comune di Milano | `processes_application` | [Cambio di residenza](https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza), passage on checks after the declaration |
| Marriage banns, Torino handles the request | Ufficio pubblicazioni di matrimonio, Città di Torino | `receives_application` | [Ufficio pubblicazioni di matrimonio](https://www.comune.torino.it/amministrazione/ufficio-pubblicazioni-matrimonio-0), *Competenze* |
| Marriage banns, Torino handles the request | Ufficio pubblicazioni di matrimonio, Città di Torino | `processes_application` | [Ufficio pubblicazioni di matrimonio](https://www.comune.torino.it/amministrazione/ufficio-pubblicazioni-matrimonio-0), *Competenze* |
| Marriage banns, ceremony elsewhere | Municipality of celebration, identity pending the celebration location | Candidate for `receives_referral` | [Richiedere le pubblicazioni di matrimonio](https://www.comune.torino.it/servizi/richiedere-pubblicazioni-matrimonio), *Descrizione*, paragraph on sending the delegation |
| Residence permit, request already identified as eligible for postal filing | Poste Italiane, enabled Sportello Amico branch to be resolved for the case | `receives_application` | [Portale Immigrazione · La Procedura](https://www.portaleimmigrazione.it/ITA/nuovaProcedura.html), section on where to present the request |

The Milan example points to the registry office as the receiving body and captures ANPR as the online channel. The Torino example keeps both assignments for the same office. The municipality receiving the delegation is resolved from the place of celebration. The permit example records the postal intermediary's intake role. An unspecified permit category leaves the receiving route unresolved.
