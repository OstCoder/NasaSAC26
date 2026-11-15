# Phase 4 — Website Acceptance Testing

**Result: 13 / 13 PASS** · 2026-11-14

Tested the running LunaNav frontend against the real FastAPI backend in **JPL live**
mode. The automated run exercises every acceptance test below and compares displayed
values with `/api/scenario`, `/api/snapshot`, `/api/requirements`, `/api/reschedule`,
`/api/compare` and the committed Phase 3 `/api/phase3/windows` results.

## Environment and scope

- App: `http://127.0.0.1:5173` (Vite), backend: `http://127.0.0.1:8000` (FastAPI).
- Browser: locally installed Google Chrome, controlled with Playwright.
- Viewports: 1440 × 1000 desktop and 390 × 844 mobile.
- Data mode: **JPL live** (default), using the cached JPL Horizons tables and the
  committed LOLA horizon masks. No demo or substituted values were accepted as
  scientific results.
- **Deployment limitation:** this repository contains no hosted deployment URL, so
  Test 1 was run against the local application. No remote deployment was verified.
- Reproduce with both servers running:

```bash
cd frontend
npm run acceptance
# optional: ACCEPTANCE_SHOTS=1 npm run acceptance
```

The runner is `frontend/scripts/acceptance.mjs`; the existing `npm run smoke` remains
the shorter critical-workflow check.

## Final results

| Test | Status | Key evidence |
|------|--------|--------------|
| 1. Website Loading | **PASS** (local) | Dashboard, map, site selector, UTC date control and live backend status loaded; `/api/config` and `/api/sites` returned 200; no console/page errors. |
| 2. Landing-Site Selection | **PASS** | A, B and C each loaded their own published coordinates, map label and scenario; marker A followed the selection. |
| 3. Mission Date Selection | **PASS** | 1 Dec 2026 + 168 h produced 1–8 Dec; 11 Dec produced 11–18 Dec; both analyses reloaded. |
| 4. NASA Data Integration | **PASS** | Sun/Earth az/el, terrain skyline and clearance matched `/api/snapshot`; JPL/LOLA provenance displayed; UTC used throughout. |
| 5. Sun/Earth Visualization | **PASS** | Sun and Earth markers/tracks, geometric horizon and LOLA skyline rendered; positions matched the series; custom coordinates were labelled **geometric only**. |
| 6. Visibility Timeline | **PASS** | Sun, Earth and Both bands/totals matched the API; UTC interval titles; timeline click and keyboard scrubbing updated the sky/snapshot; all-blocked and missing values were explicit. |
| 7. Mission Metrics | **PASS** | All seven required metrics matched `/api/scenario` exactly; units, lower-bound markers and Phase 3 committed values agreed. |
| 8. Landing-Site Comparison | **PASS** | A/B side-by-side used the same window; all three candidates showed separate values and per-check PASS/FAIL; differences and no-ranking disclaimer shown. |
| 9. Mission Delay Comparison | **PASS** | 1–8 vs 11–18 Dec table showed A/B/C changes and both verdicts; Site B recompute returned the API’s 240 h shift and metrics. |
| 10. Mission Requirements | **PASS** | 60/50/12 produced matching FAILs; changed thresholds updated results; invalid 101% was blocked; NASA disclaimer present. |
| 11. Error Handling | **PASS** | Invalid dates, unavailable scientific site, aborted requests, HTTP 500 and full boot failure were handled; **Try again** recovered each failed request. |
| 12. Responsive/Accessibility | **PASS** | 1440 px and 390 px had no page overflow; charts/controls remained usable; keyboard, text status labels, terminology, sources and limitations present. |
| Critical End-to-End | **PASS** | A/B/C delay workflow ran with no crash; no candidate met all 60/50/12 targets; the app explained the trade-offs rather than assuming a winner. |

## Detailed checks

### Test 1 — Website loading

- [x] Open the website — opened the local app; no hosted deployment is configured.
- [x] Dashboard loads successfully.
- [x] Lunar map is displayed.
- [x] Site selector is visible.
- [x] Mission date controls are visible.
- [x] Browser console has no errors on load.
- [x] Backend connection works: `/api/config` and `/api/sites` return 200 and the UI shows **JPL connected**.

### Test 2 — Landing-site selection

- [x] Site A (Shackleton Rim) selected: 89.780° S, 155.730° W.
- [x] Coordinates displayed for Site A.
- [x] Site B (Connecting Ridge) selected: 89.450° S, 137.310° W.
- [x] Displayed coordinates changed.
- [x] Site C (de Gerlache Rim) selected: 88.670° S, 68.100° W.
- [x] Selected site is highlighted on the map (marker A and permanent label).
- [x] Each site loaded its own scenario and metrics.

### Test 3 — Mission date selection

- [x] Selected 1 Dec 2026 at 00:00 UTC.
- [x] Set duration to 7 Earth days (168 h).
- [x] Analysis ran automatically after the inputs changed.
- [x] Correct range displayed: 1 Dec 2026 00:00 → 8 Dec 2026 00:00 UTC.
- [x] Changed landing date to 11 Dec 2026.
- [x] Analysis ran again.
- [x] New range and results displayed: 11 Dec 2026 00:00 → 18 Dec 2026 00:00 UTC.

### Test 4 — NASA astronomical data integration

- [x] Verified lunar site selected (`shackleton-rim`).
- [x] Requested Sun position data (`POST /api/snapshot`, `/api/scenario`).
- [x] Requested Earth position data.
- [x] Azimuth values displayed (Sun 75.8°, Earth 162.4° at the landing sample).
- [x] Elevation values displayed (Sun 1.52°, Earth −1.82°).
- [x] Timestamps use UTC.
- [x] Results match backend outputs: snapshot values matched exactly; displayed Sun/Earth shares and blackout agreed with committed Phase 3 data within 1 percentage point / 1 hour where cross-checked.
- [x] No fabricated values presented as NASA measurements; JPL/LOLA provenance and “Sourced scientific data” are visible, and absent event times show `—`.

### Test 5 — Sun and Earth visualization

- [x] Opened the sky/horizon visualization.
- [x] Sun marker appears (76° azimuth, 1.5° elevation at the first sample).
- [x] Earth marker appears (162° azimuth, −1.8° elevation).
- [x] Geometric horizon and terrain skyline are displayed.
- [x] Selected a different timestamp with **Next sample** and the timeline.
- [x] Sun and Earth markers updated to the new series sample.
- [x] Marker positions match the calculated azimuth/elevation.
- [x] Visibility status is correct (“Blocked by terrain”, “Above terrain horizon” or “Below geometric horizon” as applicable).
- [x] Terrain is labelled only where supported; custom coordinates display **Geometric only, no terrain** and “No LOLA horizon mask for this location”.

### Test 6 — Visibility timeline

- [x] Opened the mission visibility timeline.
- [x] Sunlight intervals appear where the Sun is visible (Site B, 11–18 Dec: 100%, 7 d 0 h).
- [x] Darkness periods are shown as hatched tracks; Site A’s window is fully blocked and reports a ≥7 d Sun blackout.
- [x] Earth visibility intervals appear (Site B: 20.5%, 34.5 h).
- [x] Earth obstruction periods appear as the hatched remainder and longest-blackout metric.
- [x] Simultaneous visibility appears (Site B: 20.5%, 34.5 h).
- [x] Timestamps are accurate and use UTC; interval tooltips match the API boundaries.
- [x] Timeline selection updates the inspected time.
- [x] Sky view/snapshot updates with the timeline selection.
- [x] Missing data is explicit: absent event times show `—`; empty intervals show `0 min`; no assumed samples are drawn.

### Test 7 — Mission metrics dashboard

For Site A, 1–8 Dec, displayed values matched `/api/scenario` exactly:

- [x] Sunlight availability: 0.0%.
- [x] Total sunlight: 0 min.
- [x] Longest continuous darkness: ≥7 d 0 h.
- [x] Earth visibility: 0.0%.
- [x] Total Earth visibility: 0 min.
- [x] Longest Earth communication blackout: ≥7 d 0 h.
- [x] Simultaneous visibility: 0.0%.
- [x] Units are correct and shown (`%`, minutes/hours/days, degrees).
- [x] Displayed values agree with the validated Phase 3 committed window.

### Test 8 — Landing-site comparison

- [x] Selected Site A and Site B.
- [x] Used the same mission date range for both (1 Dec 2026, 168 h).
- [x] Ran the comparison.
- [x] Both sites displayed separate results and provenance.
- [x] Compared sunlight availability (A 0.0%, B 100.0%).
- [x] Compared Earth visibility (A 0.0%, B 0.0%).
- [x] Compared longest darkness (both ≥7 d 0 h at this window).
- [x] Compared longest Earth blackout (both ≥7 d 0 h at this window).
- [x] Results match backend calculations.
- [x] Differences are explained in the trade-off panel; the app explicitly says the table does not combine measures into a ranking.
- [x] All three candidates at 1 Dec were shown as separate rows with PASS/FAIL per 60/50/12 target.

### Test 9 — Mission delay comparison

- [x] Selected Site A.
- [x] Original landing date: 1 Dec 2026.
- [x] Ran a seven-day analysis.
- [x] Recorded visibility metrics.
- [x] Changed landing date to 11 Dec 2026.
- [x] Ran the analysis again.
- [x] Compared original and delayed results.
- [x] Differences calculated correctly from the API.
- [x] Compared Site B for the delayed date: Earth visibility 0% → 20.5%, longest blackout 168 h → 133.5 h.
- [x] The delay table shows both initial and after-delay requirement verdicts; it explains that the change is a property of the dates, not a site ranking. No candidate meets all 60/50/12 targets.

### Test 10 — Mission requirement evaluation

- [x] Entered/selected 60% minimum sunlight, 50% minimum Earth visibility and 12 h maximum Earth blackout.
- [x] Ran the analysis for Site A.
- [x] Sunlight requirement result: FAIL (0.0%).
- [x] Earth visibility requirement result: FAIL (0.0%).
- [x] Maximum blackout requirement result: FAIL (168 h).
- [x] Failed requirements are marked by text and icons, not colour alone.
- [x] PASS/FAIL results match the measured metrics and API.
- [x] Changed requirements and reran: 0/0/200/200 produced Sun PASS, Earth PASS, darkness PASS, and blackout **UNDECIDED** because the 168 h value touches the window edge and is a lower bound.
- [x] Feasibility results updated correctly.
- [x] The UI states these are demonstration targets, not NASA flight requirements, and never calls a site NASA-approved or fully safe.

### Test 11 — Error handling

- [x] Invalid date range (2031) produced a helpful supported-window message.
- [x] Unsupported date is constrained by the displayed range (2026-01-01 to 2030-12-31).
- [x] Requested unavailable scientific site data (Peak Near Shackleton without a LOLA mask) and received “Scientific data is not loaded”; no values were substituted.
- [x] Simulated backend unavailability and the UI showed “Backend not reachable”.
- [x] Simulated an API 500 and the UI showed the calculation error message.
- [x] Helpful error messages appeared.
- [x] The website did not crash.
- [x] Missing values were not replaced with fabricated measurements (`—`, no mission summary on failure).
- [x] **Try again** recovered both an aborted request and an HTTP 500; the boot screen also recovered from a full backend outage.

### Test 12 — Responsive design and accessibility

- [x] Tested at 1440 px desktop.
- [x] Tested at 390 px mobile.
- [x] Charts remain within the viewport and readable.
- [x] Buttons and controls remain usable.
- [x] No horizontal page overflow at either width.
- [x] Tables keep semantic headers on desktop; the candidate comparison switches to readable stacked cards on phones.
- [x] Keyboard navigation works: nav buttons activate with Enter, tabs with Enter, and timeline bands with ArrowLeft/ArrowRight.
- [x] Important information is presented as text (`PASS`, `FAIL`, `UNDECIDED`, visibility statuses), not colour alone.
- [x] Technical terms are explained in tooltips and the Data & methodology page.
- [x] NASA data sources, assumptions and limitations are visible in the footer and methodology page.

## Critical end-to-end result

Scenario: **does a ten-day delay change the preferred site?**

| Site | Window | Sun | Earth | Longest Earth blackout | 60/50/12 verdict |
|------|--------|-----|-------|------------------------|------------------|
| A · Shackleton Rim | 1–8 Dec 2026 | 0% | 0% | 168 h (≥7 d) | fails all |
| A · Shackleton Rim | 11–18 Dec 2026 | 0% | 0% | 168 h (≥7 d) | fails all |
| B · Connecting Ridge | 11–18 Dec 2026 | 100% | 20.5% | 133.5 h (5 d 14 h) | fails Earth + blackout |
| C · de Gerlache Rim | 11–18 Dec 2026 | 100% | 60.0% | 67.2 h | meets Sun + Earth, fails 12 h blackout |

**Conclusion shown by the app:** no candidate meets all three selected demonstration
targets. A ten-day delay changes the numbers substantially, and different measures
point to different sites: C has the most Earth visibility and shortest blackout, while
B is fully sunlit but has less Earth visibility. The application does not declare a
single “best” site, does not assume the same site always wins, and does not claim NASA
approval. All three candidate rows and every selected constraint are visible.

## Scientific validation

- Sun/Earth azimuth, elevation, skyline and clearance matched `/api/snapshot` exactly
  at the inspected time.
- The seven required mission metrics matched `/api/scenario` exactly, including units
  and lower-bound (`≥`) markers.
- Site A’s displayed shares and blackout agreed with the committed Phase 3
  `/api/phase3/windows` values within 1 percentage point / 1 hour.
- JPL live mode was used throughout, with NASA JPL Horizons and LOLA provenance shown.
- Missing values remained `—`; no synthetic or demo values were substituted in
  scientific mode.

Phase 2/3 independent validation remains the source of scientific accuracy. This
acceptance run verifies frontend/backend integration and honest presentation; it does
not add a new independent orbit or terrain validation.

## Defects found and fixed during acceptance

1. **No retry after an in-session request failure.** The error notice explained the
   failure but offered no retry action. `useApiResource` now exposes `retry`, and the
   planner, comparison, requirements, rescheduler and delay panels show **Try again**.
2. **Misleading custom-coordinate help text.** It said custom points lack terrain “in
   demo mode”; JPL/scientific custom points also lack a LOLA skyline. The text now says
   custom points are labelled **geometric only** whenever no skyline exists.

No scientific calculation was changed to make a test pass. In particular, a
window-limited blackout remains **UNDECIDED**, not PASS.

## Known limitations

- **No hosted deployment was available**, so Test 1 covers the local application. A
  remote deployment still needs its own CORS/API-base and browser check.
- JPL live mode depends on network access to JPL Horizons (with a monthly cache) and
  NASA Moon Trek imagery. The visibility series used here were cached/committed; a
  fresh live fetch was not required to reproduce this run.
- All three 168 h candidate windows have a longest Earth blackout that begins at or
  touches a window edge, so an “at most” blackout threshold above the observed lower
  bound is correctly reported as **UNDECIDED**. Only a longer analysis window or an
  interior blackout can make that check decidable.
- The automated accessibility checks cover keyboard operation, text alternatives and
  overflow; no axe/WCAG contrast scan or screen-reader session was run.
- Only Chrome was exercised. Firefox and Safari were not tested.
- The experimental 3D terrain panel remains feature-flagged off; the 2D profile is the
  tested terrain view.
- Sun visibility is geometry, not generated power; Earth visibility is geometry, not a
  communication link budget. These limitations are stated in the UI.

## Completion checklist

- [x] Test 1 — Website Loading: PASS (local; no hosted deployment)
- [x] Test 2 — Landing Site Selection: PASS
- [x] Test 3 — Mission Date Selection: PASS
- [x] Test 4 — NASA Data Integration: PASS
- [x] Test 5 — Sun/Earth Visualization: PASS
- [x] Test 6 — Visibility Timeline: PASS
- [x] Test 7 — Mission Metrics: PASS
- [x] Test 8 — Landing Site Comparison: PASS
- [x] Test 9 — Mission Delay Comparison: PASS
- [x] Test 10 — Mission Requirements: PASS
- [x] Test 11 — Error Handling: PASS
- [x] Test 12 — Responsive Design: PASS
- [x] Critical End-to-End Test: PASS
- [x] All critical bugs found by the acceptance run resolved.
- [x] Scientific values match validated backend outputs (within the stated tolerances).
- [x] Known limitations documented.
