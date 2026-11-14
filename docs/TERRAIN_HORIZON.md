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

## HTTP

```bash
curl 'http://localhost:8000/api/terrain-horizon?site_id=shackleton-rim'
curl 'http://localhost:8000/api/terrain-horizon?site_id=shackleton-rim&window=alternative'
curl 'http://localhost:8000/api/terrain-horizon?latitude_deg=-89.9&longitude_deg=0.0'
```

Errors use the shared shape `{code, message, details}`: unknown site is 404, a
half-given coordinate pair or an unknown window is 422, a missing mask
directory is 503.
