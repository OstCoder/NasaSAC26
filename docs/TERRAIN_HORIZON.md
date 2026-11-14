# Terrain horizon obstructions (Phase 3 Task 3)

How the project answers "is the Sun (or Earth) actually above the hills?" for a
candidate site, what the numbers mean, and what they deliberately do not claim.

- Code: `backend/app/services/terrain_horizon.py`
- Endpoint: `GET /api/terrain-horizon`
- Tests: `backend/tests/test_terrain_horizon.py`
- Data: `data/scientific/horizon_masks/<site>.json` (see
  [TERRAIN.md](TERRAIN.md) and [DATA_ACCESS.md](DATA_ACCESS.md))

## The rule

For each sample, at the body's own azimuth:

```text
skyline_deg  = max terrain elevation angle in that azimuth direction
clearance_deg = body.elevation_deg - skyline_deg
visible      = clearance_deg > 0        (body centre above the terrain)
```

This module does not invent a second visibility rule. It builds the explicit
horizon profile, compares both bodies against it, and **delegates** the
adjusted visibility, intervals and metrics to
`services/phase3.py::visibility_response`, so a number in this document and a
number in `/api/phase3` can never disagree — the tests assert the delegation.

## Inputs

| Input | Where it comes from | Notes |
| --- | --- | --- |
| Terrain profile | committed LOLA masks, 360 azimuths at 1° | near tier 5 m/pixel to the site DEM edge, far tier 80 m/pixel to 150 km |
| Surface elevation | mask document / series site block | LOLA DEM datum, metres |
| Observer height | mask document (`observer_height_m`) | 2.0 m eye height; change it by rebuilding the mask, not by shifting the profile |
| Curvature | applied when the mask was built | `drop = s² / (2R)`, `R = 1 737 400 m` |
| Sun/Earth elevation | Phase 2 Task 2 hourly series | same values the geometric tasks use |
| Visibility rule | `config.visibility` (`center_above_terrain`) | a rule other than this raises instead of silently changing meaning |

## What the response contains

| Block | Meaning |
| --- | --- |
| `terrain.profile` | `azimuth_deg` (0…359) and `elevation_deg` — the full skyline, not a summary |
| `terrain.summary` | max/min/mean obstruction and the azimuth of the maximum |
| `terrain.coverage` | both tiers (pixel size, range), longest sampled range, curvature model |
| `terrain.uncertainty` | pixel sizes, observer height and its uncertainty, azimuth sampling, what is unmodelled |
| `terrain.limits` | plain-language statements of what the skyline cannot see |
| `terrain.basis` / `geometric_only` | `"terrain"`/`false` when a LOLA skyline exists, `"geometric"`/`true` otherwise |
| `comparison.sun`, `comparison.earth` | samples, above/below skyline, clearances, skyline range, how many flat-horizon answers terrain blocked |
| `visibility` | the `/api/phase3` summary, intervals, rule and a pointer to the series |
| `checks` | profile length, profile-vs-mask agreement, observer height agreement, whether terrain changed any answer, finiteness |
| `provenance` | ephemeris, mask source, sampling, expected terrain provenance |

## Committed skylines (2 m observer)

| Site | Max obstruction | Azimuth of max | Far-tier commentary |
| --- | --- | --- | --- |
| `shackleton-rim` | 9.4281° | 236° | ridge terrain dominates; far tier adds little |
| `connecting-ridge` | 2.849° | from mask | far tier 1.06° |
| `de-gerlache-rim` | 1.284° | from mask | far tier −0.85° (below the tangent plane) |

The Sun never rises above ~1.7° at these latitudes, so a skyline of 9.4° blocks
it for the entire window: the terrain-adjusted answer is far stricter than
`elevation > 0`. That is the point of Task 3, and the `comparison` block
quantifies it per site instead of asserting it.

## Geometric-only points

A point with no committed mask — any custom `latitude_deg`/`longitude_deg`, or a
site whose mask was never built — is returned with:

- `terrain.available: false`, `basis: "geometric"`, `geometric_only: true`
- a flat 0° horizon (360 samples), never a fabricated profile
- `visibility.available: false` with the reason, and `comparison` nulls

The flag is surfaced, not hidden: a client must not display these as
terrain-verified. `provenance.expected_terrain_provenance` stays
`scientific_sourced` so the gap is visible in the payload.

## Uncertainty and limits

- **5 m / 80 m pixels.** The near tier resolves ridges within a few metres; the
  far tier smooths terrain finer than 80 m, so a distant ridge narrower than a
  pixel can be under-represented. The far tier is a lower bound on distant
  obstructions.
- **2 m observer.** A mast or a lander deck changes the skyline; rebuild the
  mask with a different eye height rather than adding an offset here.
- **1° azimuth sampling.** Obstructions narrower than ~1° are sampled, not
  resolved; the skyline is linearly interpolated between samples.
- **150 km range.** Past that distance lunar curvature puts even the highest
  terrain below the tangent plane for these sites (~194 km for a 10.8 km peak).
- **Geometry, not hardware.** Sun above terrain is a power precondition; Earth
  above terrain is line of sight, not a link budget. Neither is a landing
  recommendation.
- **No atmosphere, no scattering, no libration beyond the stored ephemeris.**
  The numbers are airless geometry at the stored UTC samples.

## In the website

The Mission Planner's *Phase 4 · Terrain horizon profile* panel
(`frontend/src/features/phase3/TerrainHorizonPanel.tsx`) draws this profile with
the Sun and Earth tracks from `/api/series` on top, shows the `terrain` or
`geometric only` badge from the payload itself, and prints the observer height,
both pixel tiers, the 150 km range, the maximum obstruction and its azimuth. It
reports how many samples sit above the skyline and how many the terrain blocks,
so the chart is never the only copy of a number.

## HTTP

```bash
curl 'http://localhost:8000/api/terrain-horizon?site_id=shackleton-rim'
curl 'http://localhost:8000/api/terrain-horizon?site_id=shackleton-rim&window=alternative'
curl 'http://localhost:8000/api/terrain-horizon?latitude_deg=-89.9&longitude_deg=0.0'
```

Errors use the shared shape `{code, message, details}`: unknown site is 404, a
half-given coordinate pair or an unknown window is 422, a missing mask
directory is 503.

## Experimental site 3D view (Phase 4 Task 6, feature-flagged)

`GET /api/terrain-dem?site_id=..` serves a committed 128x128 average-pooled
height grid of the PGDA 5 m/pix site model (one JSON per candidate in
`data/scientific/site_dems/`, generated by
`backend/scripts/export_site_dem_previews.py`, which records the source file
and its SHA-256). The panel `SiteTerrain3DPanel` renders it with three.js,
behind the `experimental_3d_terrain` feature flag (false in
`config/lunanav.config.json`) and an explicit in-panel enable button —
double off by default.

Frame, datum and exaggeration, all also shown in the panel text:

- **Frame:** local ENU at the site. Scene x = east, z = south, y = up;
  azimuth is clockwise from local north (azimuth 90 deg points along +x).
- **Datum:** heights are LOLA metres above the 1737.4 km reference sphere.
  The mesh displays them *relative to the pooled site-cell height* (absolute
  differences are what matter at site scale; the absolute value is printed).
- **Exaggeration:** vertical scale is exaggerated by a labelled slider factor
  (default 3x, 1-5x). Horizontal scale is true kilometres; no vertical Datum
  distortion beyond the slider.
- **Resolution:** 125 m average-pooled cells over the 16 km x 16 km site DEM,
  so it resolves hills and rims, not boulders or the landing ellipse.
- **Projection:** the source rasters are polar stereographic; scale distortion
  at these latitudes is under 0.2% and is ignored (as in the mask builder).

The skyline is drawn on a sky dome as *directions* (the committed 360-point
profile from `GET /api/terrain-horizon`), and the Sun/Earth arrows are the
window-mean azimuth/elevation from the committed series. This view is display
only: **the 2D terrain horizon profile and its numbers remain the source of
truth for every visibility answer.** The DEM payload is copied from the
committed evidence and validated (schema, grid shape, finite heights, plausible
cell size) in `backend/tests/test_terrain_dem.py`; a missing or malformed
preview is a 503 `DEM_UNAVAILABLE`, never a fabricated mesh.
