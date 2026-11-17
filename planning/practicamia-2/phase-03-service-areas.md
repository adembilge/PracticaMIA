# Phase 3.10 — Office addresses and service areas

[PracticaMIA 2.0 task 22.4](phase-03-official-sources-and-catalog.md#22-import-italian-authority-and-geography-identifiers) keeps the physical place of an office independent from the area in which a body handles a procedure. An address is endpoint information for an office visit. It is not evidence that the office accepts every request from its municipality, province or region.

## Catalogue contract

| Record | Required information and boundary |
| --- | --- |
| Office address | Stable office and authority IDs, address line, physical municipality ID, source and version. Address changes do not rewrite a service-area assignment or historical case reference. A case-specific appointment address remains in the private case, not the shared catalogue. |
| Service-area assignment | Stable assignment ID, authority ID, procedure ID, named case-location role, covered territorial-unit type and IDs, source-version passage, review decision and active state. A single procedure may have several assignments; the same authority may cover different areas for different procedures. |
| Case location | User-confirmed municipality, province, region or country IDs for a specific purpose: destination, residence, activity location, ceremony location or another defined role. An office address and inferred IP location cannot fill this fact. |

Resolve the procedure first, then obtain the case location required by each candidate assignment. Match the assignment's territorial-unit type against the corresponding confirmed ID; a province-wide assignment needs a confirmed province ID, and a multi-municipality assignment lists its covered municipality IDs. If a required location role or territorial ID is missing, request it. If no reviewed, applicable assignment matches, leave the competent authority unresolved. If distinct authorities match, return candidates and seek the condition that distinguishes them. A physical office can be located outside the served municipalities.

Only a human-approved assignment supported by a currently trusted, applicable [source passage](phase-03-claim-evidence.md) may support routing. A directory name, office address or source URL alone does not grant a procedure role. Revalidate the passage on source withdrawal or version change and preserve the older assignment evidence in case history. [Service-channel scope](phase-03-service-channels.md) still determines whether an office, portal or appointment is an available action for a specific step.

## Implementation boundary

The isolated [service-area resolver](../../backend/app/knowledge/service_areas.py) stores office addresses and service areas in separate types. It accepts only explicitly approved assignments whose evidence reference is in the caller's trusted-passage set. It returns `supported`, `ambiguous`, `needs_information` or `unresolved`, and withholds an authority result when required location facts are missing. [Nine synthetic tests](../../backend/tests/test_service_areas.py) cover an office outside its service area, procedure-specific coverage, multiple municipalities, province matching, missing facts, competing authorities and revoked/unapproved evidence.

The general authority/geography catalogue, persisted service-area assignments, official import, source-review binding and user-facing API are not implemented. The caller that supplies trusted passages and confirmed case locations must be integrated and verified before this resolver can guide a real user. No official assignment is approved by this document or the synthetic fixtures.
