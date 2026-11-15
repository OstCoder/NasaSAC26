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

## Slow-connection check (14 Nov 2026)

The Task 5 item "test the application on slower connections" was run against a throttled
API link. `scripts/slow_connection_proxy.py` is a TCP reverse proxy that paces bytes and
adds latency; it sat between the dev server and FastAPI
(`vite → proxy 8003 → backend 8002`, `LUNANAV_API=http://127.0.0.1:8003`).

**Profile:** 400 kbit/s, +300 ms one-way latency (≈600 ms RTT) — roughly "slow 3G". The
proxy only throttles the client↔API link: page assets still come from the dev server
(production: CDN) and backend→JPL/Moon Trek fetches are server-side. The proxy measured
46–47.5 kB/s effective on large transfers against the 50 kB/s target; the remainder is
chunking overhead.

### Per-endpoint transfer cost (curl, `Accept-Encoding: gzip`)

| Endpoint | Size | Direct | Throttled |
| --- | ---: | ---: | ---: |
| `GET /api/config` | 1,449 B | 2 ms | 0.64 s |
| `GET /api/sites` | 3,031 B | 2 ms | 0.67 s |
| `GET /api/series` (1 site, window) | 7,592 B | 5 ms | 0.77 s |
| `GET /api/terrain-horizon` | 5,331 B | 4 ms | 0.71 s |
| `GET /api/engineering` | 4,405 B | 9 ms | 0.73 s |
| `GET /api/psrs` (390 polygons) | 329,226 B | 257 ms | 7.75 s |
| `GET /api/imagery/south-pole` size=512 | 423,557 B | — | 9.44 s |
| `GET /api/imagery/south-pole` size=1024 | 1,442,015 B | 1.4 ms (cached) | 30.67 s |

### In-browser (same profile, repeat visit so imagery came from the HTTP cache)

- Shell and site data visible ≈ **3.5 s** after navigation start.
- Mission summary and timeline interactive ≈ **8.7 s**; the 329 kB PSR catalogue
  transferred cold in **7.73 s** in-page (matches the curl number).
- Interaction under throttle: switching the power-budget site refetched
  `/api/engineering` in **730 ms** and the panel updated (708 W / 118,487 Wh).
- Decision support view: `POST /api/decision` returned in **702 ms**; verdict rendered.
- **Zero console errors or failed requests** for the whole session.

### Findings

1. The JSON API contract survives a slow link: every analysis endpoint is small, gzipped
   and stays under a second at 400 kbit/s, so site selection, comparisons and the
   decision view remain responsive.
2. The first-visit cost is dominated by Moon Trek imagery: the 512 preview + 1024 full
   image are ≈1.9 MB, ≈40 s serialized at this rate (requests run concurrently, so wall
   clock is ≈30–40 s). Repeat visits reuse the browser cache (2–3 ms). The app shows
   loading states and renders the vector layers meanwhile, so the page stays usable
   while imagery arrives.
3. Loading indicators and failure retries (Phase 4) are what make this profile survivable;
   nothing timed out or dead-ended.

Remaining limit: the imagery payload itself. A future improvement could default to the
512 px layer on slow links or cache it harder; this was measured, not changed, because
the task asked to test, not to redesign.

No low-end phone or real-network field test is claimed. Other profiles can be re-run with
the committed script's `--rate-kbps` / `--latency-ms` flags.

## Remaining performance limits

- The PSR catalogue is still a large JSON response; gzip helps, but the client still parses and simplifies 390 polygons.
- The 3D ray-march is recomputed when the Sun direction or DEM changes. It is intentionally capped at 96 steps and 16,384 cells.
- The Science page requests a context per candidate for its comparison rows, plus the selected context. This is a small fixed fan-out for three candidates, not a poll.
- No formal low-end phone benchmark or Lighthouse score is claimed.
