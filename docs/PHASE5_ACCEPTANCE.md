# Phase 5 acceptance — decision support, orientation, sensitivity and science

**Executed:** 14 November 2026 against the real FastAPI backend and the running Vite app.

```bash
cd backend && uvicorn app.main:app --port 8000
cd frontend && npm run dev
cd frontend && npm run acceptance:phase5
```

The runner is `frontend/scripts/acceptance-phase5.mjs`. It uses the installed
Chrome through `playwright-core` and does not mock the backend. Screenshots can be
kept with `ACCEPTANCE_SHOTS=1`.

## Result

**6/6 passed.**

| ID | Check | Evidence |
| --- | --- | --- |
| P5-1 | Engineering orientation and sensitivity API | A fixed 45°/180° array is selected, the battery follows its 657 Wh generation, all three designs are returned, the seven sensitivity cases are present and the solar/load bounds move in the expected direction. |
| P5-2 | Decision orientation and science mode API | Every decision row carries `panel_design=fixed`, the science weight is 0.4, and each explanation names PSR proximity without claiming water ice or rover access. |
| P5-3 | Energy panel and built-in sensitivity | The browser selected **Fixed tilt/azimuth**, rendered the energy timeline, opened the sensitivity table showing the base, solar −10 %, load +20 % and other cases, and reported no page or API errors. |
| P5-4 | Science exploration mode UI | The **Science exploration** button sends the science weights, shows the mode card, lists nearest mapped PSRs and displays the traverse/water-ice limit. |
| P5-5 | Delay power and requirement comparison UI | The reschedule view rendered requirement verdict changes, array energy, minimum battery and unserved-load deltas for the committed 1 Dec → 11 Dec 2026 windows with no page or API errors. |
| P5-6 | Date and power changes refresh the recommendation | On the live decision page, the censored blackout check started advisory. Selecting 11 Dec 2026 produced a top-ranked site; raising the average load to 100 kW removed every eligible site, and restoring 40 W recovered the recommendation. All responses came from the real API with no page errors. |

The run also confirmed the app never used an unsupported safety/approval claim in
the power view.

## What this proves

- The orientation control is not cosmetic: the selected design changes the
  battery trace and the decision power check.
- The sensitivity analysis is computed from the same committed series and
  reported with its limits.
- Science exploration is a visible, deterministic ranking mode that keeps the
  operational checks as the eligibility gate.
- The delay panel exposes the power comparison rather than only visibility.
- The key Phase 5 milestone works end to end: changing the date or a spacecraft
  requirement refreshes the ranking, and the UI never keeps showing the previous
  winner while the new evaluation is pending.

## Limits

These are still engineering estimates under the configured assumptions, not a
flight power budget, a measured uncertainty distribution, a traverse plan or a
landing-safety assessment. The Phase 4 13/13 browser matrix remains the record for
the underlying planner, comparison and terrain workflows. The committed-window
limit still applies: dates outside 1–8 and 11–18 Dec 2026 return UNDECIDED for
battery survival instead of extrapolating power.
