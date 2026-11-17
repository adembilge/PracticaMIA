# Phase 3.2 — Service channels in the procedure catalogue

[PracticaMIA 2.0 task 21.2](phase-03-official-sources-and-catalog.md#21-model-procedures-authorities-sources-and-evidence) records the channels available for each procedure step and the scope in which they apply. It uses the [authority-role contract](phase-03-authority-roles.md) to identify which body handles the step and the [Phase 2 channel map](phase-02-administrative-domains.md#map-service-channels-by-step) to identify candidate routes.

## Channel assignment

Record one assignment per procedure, step, channel and applicability scope. Several assignments can share a public portal or office. Give each use its own purpose, scope and evidence so a link that helps with one step cannot silently become the filing route for another.

| Field | Meaning |
| --- | --- |
| `procedure_id`, `step`, `purpose` | Stable procedure ID, step identifier and one intended action, such as reading instructions, obtaining a form, filing, getting help, booking, attending or checking status. |
| `channel_id`, `kind`, `destination` | Stable endpoint ID and kind (`portal`, `downloadable_form`, `appointment`, `office` or `official_contact`). Store the official entry URL, document URL, office reference or public contact as applicable. A case-specific appointment location can be unresolved in the catalogue. |
| `authority_role` | Reference to the procedure's authority-role assignment relevant to the step when that role is evidenced. Record any different channel operator separately from the body responsible for the procedure. |
| `scope` | Service jurisdiction and the case conditions that affect the route, such as destination municipality, application category, procedure variant or prior step. Record a physical address as endpoint information. An unknown scope stays unresolved. |
| `access` | Access described by the source, such as public, authenticated by the user, walk-in, user-booked or by summons. For office visits, record the applicable access mode. Case-specific notices and credentials stay out of the public catalogue. |
| `evidence` | One or more official source-version and passage references covering the action, scope and access claims. A URL and section locator can record a research candidate while linkage and review are pending. |

Match the requested step first, then jurisdiction and case conditions. Return all supported alternatives for that step if each applies. An appointment after filing belongs to a later step. When an unknown condition could change the route, identify the missing detail. When the scope is known and no channel has reviewed evidence, surface the gap and offer a separately supported information or assistance channel when available.

Promotion to trusted guidance requires human review of the assignment and current, approved, applicable source versions and passages. If a source changes or loses approval, use the [registry's trust checks](../../docs/OFFICIAL_SOURCE_REGISTRY.md#trust-model) before suggesting that route again. Prior case references retain the evidence used at the time.

## Worked catalogue examples

These examples use public material and are proposed catalogue assignments. The [Phase 2 collection record](phase-02-user-case-sampling.md#collection-status) records zero participants and eligible cases. Signed-in portal screens and actual appointments were outside this desk review.

| Procedure and applicable step | Kind and action | Scope and access | Official evidence locator |
| --- | --- | --- | --- |
| Milan change of residence, find the service | `portal` · read instructions | Destination Milano. Public municipal page. | [Cambio di residenza](https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza), opening service description. Read from indexed public text after direct retrieval returned HTTP 403. |
| Milan change of residence, submit the declaration | `portal` · file via ANPR | Example covers an Italian citizen moving within Milan or into Milan from another Italian municipality. User signs in to ANPR. Ufficio Anagrafe is the receiving body. | [Comune di Milano · Cambio di residenza per italiani già in Italia](https://servizicrm.comune.milano.it/centro-supporto/KA-00371/Cambio-residenza-per-italiani-gia-in-Italia), first paragraph. |
| Milan change of residence, inspect the declaration | `downloadable_form` · obtain the PDF | Public municipal copy of Allegato 1. The form itself supports inspection of declared fields. Its applicability as a filing method stays unverified. | [Dichiarazione di residenza · Allegato 1](https://www.comune.milano.it/documents/20126/526597/dichiarazione%2Bdi%2Bresidenza.pdf/cb7c0558-d61b-1968-7143-b549f0ab337d?t=1560355046111), first page. |
| Torino marriage banns, ask the office for help | `official_contact` · request information | Torino banns office contact for service enquiries. | [Ufficio pubblicazioni di matrimonio](https://www.comune.torino.it/amministrazione/ufficio-pubblicazioni-matrimonio-0), *Contatti* and *Ulteriori informazioni*. |
| Torino marriage banns, request publication | `portal` · file the request | Torino resident filing with Torino. The municipal service describes a user sign-in. | [Richiedere le pubblicazioni di matrimonio](https://www.comune.torino.it/servizi/richiedere-pubblicazioni-matrimonio), *A chi è rivolto* and *Come fare*. |
| Torino marriage banns, follow up after filing | `appointment` · follow the office's instructions | The filing was sent to Torino. The office contacts the applicant. The case-specific instructions determine the appointment details. | [Richiedere le pubblicazioni di matrimonio](https://www.comune.torino.it/servizi/richiedere-pubblicazioni-matrimonio), *Come fare* and the reference to the appointment under *Cosa serve*. |
| Residence permit, postal application | `office` · file with an enabled Sportello Amico | Request already identified as applicable to the postal route. Resolve the enabled postal branch for the case. | [Portale Immigrazione · La Procedura](https://www.portaleimmigrazione.it/ITA/nuovaProcedura.html), sections on where to apply and postal intake. |
| Residence permit, direct application | `office` · file with the competent Questura immigration office | Request already identified as applicable to direct filing. Resolve the competent office before naming a destination. | [Portale Immigrazione · La Procedura](https://www.portaleimmigrazione.it/ITA/nuovaProcedura.html), section on where to apply, table link for direct filing. |
| Residence permit, after a postal submission | `appointment` · attend at the Questura | Postal route filed and a summons received. Use the office named in the case's summons. | [Portale Immigrazione · La Procedura](https://www.portaleimmigrazione.it/ITA/nuovaProcedura.html), *Informazioni generali*, paragraph on the post-filing summons. |

## Applicability checks

| Scenario | Expected decision |
| --- | --- |
| The same address-change request names another destination municipality. | Exclude Milan-scoped channels. Resolve the destination's applicable service independently. |
| A Torino applicant asks how to submit after seeing the office contacts. | The filing candidate is the municipal online service. The contact remains available for information. |
| The residence permit request category or route remains unclear. | Ask for the detail that determines postal or direct filing and withhold a specific destination. |
| A postal filing is complete and the summons has yet to arrive. | Leave the appointment details pending. The public instructions can explain the expected summons when approved for that use. |
| Only the public PDF is cited for a filing claim. | Keep the PDF available as a preparation candidate and require evidence of an applicable filing channel. |
