# PracticaMIA — First Interface Design

**Version:** 0.1 — 3 November 2026  
**Status:** Proposed UX specification for review. Not implemented.  
**Basis:** `docs/FIRST_USER_JOURNEY.md` and `research/milan_residence_change.md`.

## 1. Product experience and scope

Design one coherent workflow for an adult already registered in Milan who moves alone to a rented apartment elsewhere in Milan. PracticaMIA helps the user establish whether the case matches a supported workflow, collect relevant facts, understand verified requirements, and prepare for **user-controlled ANPR submission**. It is not an official government service.

**First interactive prototype:** Steps 1–4 of the journey—start, scope check, targeted intake, and requirements checklist—with **synthetic data and explicitly labeled mock guidance**. Document upload, PDF generation, accounts, live agent calls, and official submission are represented by non-functional previews or omitted at this stage.

**Design principles:** one next action at a time; visible progress and blockers; sources beside claims; distinguish entered, extracted, and confirmed facts; save/resume in the later functional version; no invented document requirements or official completion statuses.

## 2. Information architecture

| Route / screen | Purpose | First prototype? |
|---|---|---|
| `/` — Welcome | Explain purpose, limits, and start action; EN/IT switch | Yes |
| `/cases/new` — New case | Natural-language goal and short routing intake | Yes |
| `/cases/demo` — Case workspace | Guided questions, case facts, requirements, next action | Yes (synthetic case) |
| `/cases/demo/review` — Review | Read-only preparation summary and unresolved issues | Preview only |
| `/cases/demo/documents` — Documents | Upload/extraction/confirmation journey | Later milestone |
| `/cases` — Dashboard | Authenticated list of saved cases | Later milestone |
| `/settings` — Account/privacy | Profile, consent, export/deletion | Later milestone |

The workspace, not a generic chat screen, is the central product surface.

## 3. Desktop workspace layout

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ PracticaMIA                         [EN | IT]    Demo case   [Help]      │
├─────────────────────────────────────────────────────────────────────────┤
│ Milan residence change      Draft · In progress         [Exit demo]      │
│ Step 2 of 4: Confirm your situation                                  │
├───────────────────────────────────────────┬─────────────────────────────┤
│ MAIN: Guided assistant                    │ CASE SUMMARY                │
│                                           │ Previous municipality: Milan│
│ "Are you moving alone?"                   │ New municipality: Milan     │
│ [ Yes ]   [ No ]   [ Not sure ]            │ Housing: To confirm         │
│                                           │ Facts: User-entered         │
│ Why we're asking [expand]                 ├─────────────────────────────┤
│                                           │ REQUIREMENTS                │
│ [Back]                      [Continue]    │  ○ Route needs confirmation │
│                                           │  ○ Document rules pending   │
│ Source evidence (when available)          │  ○ Review before handoff    │
└───────────────────────────────────────────┴─────────────────────────────┘
```

**Desktop:** 2/3 main panel, 1/3 side rail; the side rail remains visible while questions change. **Mobile:** main panel first, then collapsible “Case details” and “Checklist” sections; a persistent but non-obscuring next-action control. Avoid three equal columns or a chat transcript that obscures progress.

## 4. Screen details

### A. Welcome

- Heading: **Make Italian paperwork easier to prepare.**
- Supporting copy: “Understand the procedure, organize your information, and review what to do before using the official government service.”
- Primary action: **Start a residence-change case**.
- Secondary: **How PracticaMIA works**; language EN/IT.
- Explicit note: “PracticaMIA is independent of government authorities. You submit the application yourself.”

### B. Start a case

- One text box seeded with optional example: “I moved to a new apartment in Milan.”
- The product proposes the supported procedure, but does **not** assume the user qualifies.
- Continue into short typed routing questions, one at a time. Use deterministic mock branching for the prototype, not simulated model judgment.
- Allow **Not sure** when a missing answer legitimately prevents routing.

### C. Scope-check questions

| Order | Prototype question | Valid responses | UI behavior |
|---|---|---|---|
| 1 | Were you already registered as a resident in Milan? | Yes / No / Not sure | No → unsupported; Not sure → needs information |
| 2 | Is your new address also within Milan? | Yes / No / Not sure | No → unsupported in this slice |
| 3 | Are you applying only for yourself? | Yes / No / Not sure | No → unsupported in this slice |
| 4 | Are you joining an existing registered household? | Yes / No / Not sure | Yes → unsupported in this slice |
| 5 | Are you renting the new home? | Yes / No / Not sure | No → unsupported in this slice |

These are **product scope filters**, not a complete or official eligibility determination. Passing them moves the demo to `provisionally_in_scope`; production support still requires validated applicant-category rules.

### D. Guided intake and case facts

Ask for prior address, new address, date of move, and any additional verified requirements **only as needed**. For the prototype, use clearly synthetic example addresses. Show source and review status next to each field: **Entered**, **Needs confirmation**, or **Confirmed by user**. Editing a confirmed value reopens dependent checklist items rather than silently retaining completion.

Use inline validation for empty inputs, invalid formats, and mismatches. Do not infer precise legal requirements from an unverified date or user category.

### E. Checklist and evidence

Each item has: title, status, reason, source link (only for genuinely approved evidence), and action. Distinguish **Required**, **Conditional**, and **Information pending verification**. No unchecked statement becomes a mandatory document requirement. Show missing information and blockers prominently, but do not confuse an unfinished checklist with government rejection.

In prototype mode, label checklist data **Illustrative / synthetic**. Real source excerpts must be linked to their original institution and review date once evidence infrastructure is implemented.

### F. Review and handoff preview

Display confirmed facts, unresolved blockers, and an explanation of next steps. **Prepared for review** does not mean **submitted**, **received**, or **approved**. The final official ANPR destination is a user-operated external link and should only be enabled once its source has been verified. TARI appears as a **separate potential follow-up**, not an automatically asserted obligation for every user.

## 5. Main interaction state machine

```text
welcome → new_case → scope_check
                       ├─ missing/unsure → needs_information (save progress, ask again)
                       ├─ outside demo scope → unsupported (show explanation)
                       └─ all scope checks pass → provisional_intake
                                                   ↓
                                               checklist_preview
                                                   ↓
                                               review_preview
```

**UI statuses:** `draft`, `needs_information`, `provisionally_in_scope`, `unsupported`, `review_required`, and (later) `submission_ready`. Never display `submitted` because a user clicked an external link. Do not use `eligible` or `verified` without a reviewed rule/evidence basis.

## 6. Important alternate states

- **Unknown registration:** Show a targeted question and explain that route selection is paused.
- **Out of scope:** Explain exactly which boundary failed and allow a new case; do not create a submission package.
- **Unverified source:** Display “Requirements pending review”; do not fabricate checklist conditions.
- **Conflicting values:** Show both values and ask the user to resolve them before downstream preparation.
- **Unavailable service or save failure (later):** Clearly report that the action did not complete and preserve user-entered text where possible.
- **No documents yet:** Show a neutral placeholder until a verified rule makes a document necessary.

## 7. Visual and accessibility direction

Clean civic-tech interface: warm off-white canvas, dark slate typography, muted blue interactive accents. Reserve red for blocking issues; green for actual verified/complete states, not general decoration. Use accessible contrast and a readable body size (16px minimum recommended for form inputs), consistent focus outlines, keyboard-reachable controls, descriptive error text, visible field labels, and responsive layouts. The design must not resemble an official municipality portal or imply government affiliation.

A language switch must change interface copy without altering the saved facts or application status. Retain exact Italian official terms such as *cambio di residenza*, *residenza*, and *ANPR* when useful.

## 8. Prototype fixtures and acceptance checks

Prepare at least four synthetic scenarios:

1. **Happy path:** Adult moving alone within Milan to a rented home → reaches illustrative checklist.
2. **Missing fact:** Prior registration unknown → cannot advance to checklist as if confirmed.
3. **Unsupported path:** Moving from outside Milan or joining a household → clear supported-scope boundary.
4. **Edit/reconfirm:** User changes a previously confirmed answer → dependent review status resets.

**Design milestone complete when:**
- All four first-prototype screens are described and desktop/mobile hierarchy is consistent.
- Each primary action has a defined result; no decorative buttons masquerade as functioning features.
- Supported, unsupported, and uncertain paths are understandable.
- No label implies the government has received or approved an application.
- Legal and document requirements remain placeholders until independently approved.
- A developer can implement steps 1–4 using deterministic fixture data without inventing behavior.

## 9. Open decisions before actual implementation

- Is an account required before the first question, or can an anonymous demo precede signup? **Recommendation:** anonymous demo; require authentication only for persistent real cases.
- Final applicant categories and document conditions: **pending administrative verification**.
- Exact field labels, required addresses and date handling: **pending ANPR field research**.
- Official submission and TARI links: **source review required before activation**.

**Next milestone:** Implement a responsive, fixture-driven Next.js prototype of Welcome → New Case → Scope Check → Case Workspace with no backend/LLM dependency. Review it with several users before implementing the persistence and rules services.
