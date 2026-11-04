# PracticaMIA — Frontend Usability and Accessibility Review

**Reviewed:** 4 November 2026  
**Scope:** Next.js prototype source and successful Vercel builds  
**Limit:** Source-code review; not yet a completed cross-browser or screen-reader usability study.

## Findings and changes

| Priority | Finding | Action |
| --- | --- | --- |
| High | No keyboard skip-to-content link | Add EN/IT skip link to every route |
| High | Wizard transitions lacked focus management | Focus the active question or phase heading |
| High | Form validation errors lacked programmatic associations | Add stable error IDs and `aria-describedby` |
| Medium | Mobile input font size was 14px | Use 16px for mobile form inputs |
| Medium | Progress bar lacked current-step semantics | Add `aria-current="step"` |
| Deferred | Mobile sidebar does not collapse | Review and update after mobile user testing |
| Deferred | No browser-level E2E tests | Introduce Playwright coverage in a future milestone |

## Manual preview checklist

Open the Vercel preview attached to the pull request. Do not enter actual personal details.

- [ ] Keyboard: Tab from the top; skip link appears and navigates to the main landmark
- [ ] Scope: new questions receive focus; Yes/No/Not sure states work
- [ ] Intake: incomplete fields, invalid dates, same address, and missing acknowledgment remain blocked
- [ ] Form: validation errors are associated with their inputs
- [ ] EN and IT: navigation, skip link, and error text use the selected language
- [ ] Desktop: check 1280px and 1440px widths for layout and clipping
- [ ] Mobile: check 320px, 390px, and 760px widths for horizontal overflow and legibility
- [ ] Review: appears only after completed demo intake; no government submission is claimed
- [ ] Refresh: clears synthetic case information; official links remain external

## Definition of done

- GitHub Actions tests, type checks, and build pass.
- Vercel preview is ready and manually reviewed before merging.
- No administrative draft guidance is promoted into a real eligibility or document requirement.

**Administrative sources:** The residence-change research is still a draft requiring official-source review.
