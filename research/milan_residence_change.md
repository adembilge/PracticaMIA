# Milan Residence Change — Initial Procedure Research

**Research date:** 3 November 2026  
**Status:** Draft for human review; not approved for production administrative rules.

## Initial supported scenario

One adult who is already registered as a resident in Milan moves to a rented apartment at a different address within Milan, without joining another household or including other applicants. Citizenship-specific documentation remains a question to verify before enabling individual cases.

## Official process — verified

- The applicant must declare a change of residence **within 20 days of moving**.
- Milan directs eligible applicants to the **ANPR online service**, accessed with **SPID or CIE**.
- Registry entry normally occurs within **two working days after the declaration**; the municipality subsequently verifies the requirements. Entry is not the same as final approval.
- A change in housing situation can require a separate **TARI (waste tax) declaration**.

## Information PracticaMIA should collect

- Whether the applicant was already registered in Milan and is moving within the city.
- Previous and new addresses, moving date, and whether other household members are involved.
- Whether the applicant rents, owns, or occupies under another arrangement.
- Applicant category only where needed to select verified document requirements.

These are **proposed intake fields**, not a confirmed exhaustive list of ANPR fields.

## Documents and exceptions

- For **foreign citizens renting accommodation**, Milan specifies a copy of the rental contract and any available contract-registration receipt.
- Other required identity, residence-status, and housing documents depend on applicant circumstances and must be mapped from official sources before becoming automated rules.
- Arrival from abroad, household aggregation, minors, and complex arrangements are **out of scope for this first workflow** and require separate research.

## PracticaMIA's initial outcome

1. Confirm that the case fits the supported scenario; otherwise explain the limitation.
2. Create a personalized checklist with direct citations to approved official sources.
3. Ask for missing facts and flag inconsistent information without guessing.
4. Explain the ANPR submission steps and separate TARI follow-up.
5. Mark the package **prepared for user review**, never automatically submitted or approved.

## Official sources

1. [Comune di Milano — Cambio di residenza](https://www.comune.milano.it/servizi/anagrafe/cambio-di-residenza) — scope, ANPR authentication, 20-day declaration, registry timing, TARI.
2. [Comune di Milano — Come chiedere/cambiare residenza?](https://servizicrm.comune.milano.it/centro-supporto/KA-00330/Richiestacambio-residenza-come-procedere) — residents already in Italy, households, exceptions; updated 23 July 2026.
3. [Comune di Milano — Foreign renter housing documents](https://servizicrm.comune.milano.it/centro-supporto/KA-00329/Residenza-stranieri-in-affitto-documenti-immobile) — rental contract and registration receipt; updated 26 September 2025.
4. [Comune di Milano — Residence change for foreign citizens already in Italy](https://servizicrm.comune.milano.it/centro-supporto/KA-00597/Cambio-residenza-per-stranieri-gia-in-Italia) — online route and TARI.

## Still to verify before coding administrative rules

- Exact ANPR form fields and supporting documents for each citizenship/residence category.
- Whether registration receipt, lease details, or additional permissions are required in each supported branch.
- The precise official TARI action for a move within Milan.
- Changes to any linked source after this research date.

**Policy:** No unreviewed requirement is allowed to drive an automated eligibility decision.
