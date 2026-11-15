# Phase 6 acceptance — science, PSR map and advanced visualization

Executed on **14 Nov 2026** against the real FastAPI backend and a local Vite dev server, using locally installed Google Chrome controlled with Playwright.

```bash
cd backend && uvicorn app.main:app --port 8000
cd frontend && npm run dev
cd frontend && npm run acceptance:phase6
```

**8/8 passed.** The matrix covers the science API, the PSR map layer, the 390 px science layout, playback, the lazy 3D shadow scene and the transparency/no-overclaim contract.

| ID | Test | Evidence |
|---|---|---|
| P6-1 | PSR catalogue and proximity API | 390 mapped polygons within the map's 80°S default of the 653-polygon catalogue; Shackleton boundary distance 2.479 km, centroid 11.216 km, ±60 m positional uncertainty; water ice explicitly `not_assessed`; missing query returns 422. |
| P6-2 | Site science context and mesh API | De Gerlache context carries 5 m near / 80 m far terrain, both committed windows and PSR geometry; `/api/terrain/mesh` matches `/api/terrain-dem` source checksum; 128 × 128 cells at 125 m. |
| P6-3 | Science page, map layer and education | Science view rendered in 6.03–7.54 s end-to-end (navigation load 3.38–3.50 s) across the final matrix runs; an earlier warm run was 4.42 s / 1.02 s. PSR map, context, model labels, six education topics and NASA/LROC attribution all present. |
| P6-4 | Science page at 390 px | No horizontal overflow: document 390 px / viewport 390 px; PSR map 322 px wide. |
| P6-5 | Planner PSR layer toggle and nearest highlight | Layer starts on, hides on toggle, returns with the gold nearest-PSR highlight, and carries the LROC/LOLA >5 km² legend. This test also caught and verified the cache-hydration fix for PSR shapes. |
| P6-6 | Mission playback speed and transition marker | 4× playback advanced the shared inspected time from 11 Dec to 12 Dec; the next modelled visibility edge and dashed amber rule were shown. |
| P6-7 | 3D terrain shadows, marker and scale | Lazy Three.js scene rendered the committed LOLA mesh, a blue landing marker, a local ray-march shadow percentage, 125 m cells and labelled vertical exaggeration. |
| P6-8 | Transparency, missing-data handling and no overclaim | Sources, coordinate/resolution conventions, model labels, unknowns and the no-overclaim contract are visible; no 5xx or page errors. |

## What was checked

- API contracts, units, source metadata, coordinate frame and uncertainty.
- PSR boundary and centroid distances, including the 0 km-inside polygon rule.
- Water-ice status remains unknown, never “absent” or “confirmed”.
- Both mission windows and the 2D terrain basis are carried into the science context.
- PSR layer pause/resume across route changes (the cache bug).
- Playback does not fabricate samples and stops inside the committed series.
- The 3D display is explicitly separated from the authoritative terrain-horizon calculation.
- Desktop and 390 px layouts.
- No console/page errors or 5xx API responses during the science checks.

## Remaining limitations

- PSRs below 5 km² are absent from the product; “no mapped PSR nearby” is not a statement that no small shadow exists.
- The nearest-boundary distance is geometry, not a rover traverse, slope, thermal or trafficability assessment.
- The 3D mesh is a 125 m pooled preview; it cannot resolve the landing ellipse, boulders or a route.
- The 3D shadow ray-march is illustrative and local (~12 km), not the 360-point horizon mask used for visibility.
- Water-ice concentration, depth, temperature and resource value are not in the committed datasets.
- The performance numbers are one local run, not a device/network benchmark.

## Supporting documents

- [PHASE6_SCIENCE.md](PHASE6_SCIENCE.md) — data sources, geometry, water-ice contract, 3D/shadow limits.
- [PHASE6_PERFORMANCE.md](PHASE6_PERFORMANCE.md) — measured build split and browser timings.
- [DECISION_SUPPORT.md](DECISION_SUPPORT.md) — the existing science-priority ranking mode.
- [SITES.md](SITES.md) — site provenance and the Phase 1 PSR context.
