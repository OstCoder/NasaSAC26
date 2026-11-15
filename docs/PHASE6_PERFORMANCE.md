# Phase 6 performance — measured and bounded

This is a local measurement, not a benchmark across devices or networks. The point is to record what changed, what was measured and what remains large.

## Build split after Phase 6

`cd frontend && npm run build` produced:

| Asset | Size | Gzip |
|---|---:|---:|
| `index-*.js` | 1,051.67 kB | 312.56 kB |
| `OrbitControls-*.js` (Three.js) | 561.42 kB | 139.51 kB |
| `SciencePage-*.js` | 16.40 kB | 5.08 kB |
| `TerrainScene-*.js` | 2.78 kB | 1.59 kB |
| `LunarGlobe-*.js` | 9.53 kB | 4.06 kB |

Before the Phase 6 split the entry chunk was 1,614.90 kB. The Three.js renderer now loads only when the user enables the 3D panel; the Science page is route-split and loads when opened. The entry chunk is still above Vite's 500 kB warning threshold, so the warning is retained rather than hidden.

## Browser measurement

The Phase 6 acceptance run measured the Science page in local Chrome with both servers running:

- Runs with a warm route cache: navigation load **1.02 s**; end-to-end science context/PSR wait **4.42 s**.
- Final full-matrix runs: navigation load **3.38–3.50 s**; end-to-end **6.03–7.54 s**.
- Earlier run with a colder browser cache: **3.39 s** navigation load and **7.35 s** end-to-end.
- 390 px Science layout: **390 px document width / 390 px viewport**, PSR map **322 px** wide.

These numbers depend on the machine, the ~2 MB PSR payload, the first-time 1024 px Moon Trek imagery request and whether the browser cache is warm. They are useful for regression comparison, not a service-level guarantee.

## Deliberate optimizations

1. **Route split** — `SciencePage` is `React.lazy`, so the education/map/context code does not enter the planner's initial route.
2. **3D split** — `TerrainScene` and Three.js's `OrbitControls` are lazy-loaded after the user presses **Enable 3D view**. The panel's enable gate also avoids DEM/horizon/series requests while it is off.
3. **PSR cache** — the PSR catalogue is fetched once per page session and shared across map instances. The cache now hydrates the shapes on the next mount instead of returning an empty layer; this was found by the Phase 6 acceptance matrix.
4. **Pooled mesh** — 128 × 128 cells (125 m) rather than the full 5 m site DEM; the 2D profile remains the calculation source.
5. **Pixel ratio cap** — the WebGL renderer caps device pixel ratio at 2 to avoid 3× render targets on high-density laptops.
6. **No animation redraw of the DOM chart** — chart series use `isAnimationActive={false}`; the Three.js loop only updates orbit controls and renders the current scene.
7. **Request failure paths** — the science page uses the shared `ErrorNotice`/retry path; missing PSR, terrain or visibility values are reported, never filled.

## Remaining performance limits

- The PSR catalogue is still a large JSON response; gzip helps, but the client still parses and simplifies 390 polygons.
- The 3D ray-march is recomputed when the Sun direction or DEM changes. It is intentionally capped at 96 steps and 16,384 cells.
- The Science page requests a context per candidate for its comparison rows, plus the selected context. This is a small fixed fan-out for three candidates, not a poll.
- No formal low-end phone benchmark or Lighthouse score is claimed.
