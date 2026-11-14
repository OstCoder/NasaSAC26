# Methodology

This document describes exactly what LunaNav computes, what it includes, and what it leaves out.

## 1. Coordinates and time

- **Body frame:** Moon Mean Earth / Polar Axis (ME). Selenographic latitude/longitude, planetocentric, longitude east-positive in [−180°, 180°).
- **Reference sphere:** 1737.4 km. Observer height (default 2 m) is above this sphere. Catalogue landing sites additionally add their recorded LOLA elevation (see §9); custom coordinates default to the sphere unless the caller supplies `elevation_m`.
- **Local frame:** East-North-Up. **Azimuth** is clockwise from local north. Near the south pole, north points along the meridian toward the equator. Exact poles are rejected because azimuth is undefined there.
- **Time:** All inputs must be timezone-aware; naive timestamps are rejected. UTC → TT uses a fixed 69.184 s, valid for the configured 2026–2030 window.

## 2. Ephemeris

### Demo Mode: analytic (Meeus)
- Moon geocentric longitude, latitude, distance: *Astronomical Algorithms* (2nd ed.) Ch. 47, the leading 32 longitude/distance and 20 latitude terms plus additive terms A1–A3.
- Sun: Ch. 25 low-accuracy solution.
- Sub-Earth and sub-solar points: Ch. 53 **optical** libration with I = 1.54242°. The Sun uses the heliocentric direction of the Moon.
- **Verification** (`tests/test_ephemeris.py`): Example 47.a Moon position matches to 0.005° (lat) and 18 km; Example 53.a optical libration to 0.005°; Example 25.a Sun longitude to 0.0001°.
- **Omitted:** physical libration (~0.02–0.04°), nutation (cancels in libration to first order), light-time, aberration.
- **Expected accuracy** of Sun/Earth elevation at the surface: ~0.05–0.1°. Because the Sun moves only ~0.5°/day in elevation near the pole, a 0.05° error can shift a grazing sunrise/sunset by **hours**. This is why it is labelled approximate.

### Scientific Mode: JPL Horizons tables
- Query: target 301 (Moon), centre 500@399 (geocentre), quantities 14 (sub-observer point), 15 (sub-solar point), 19 (heliocentric range), 20 (observer range). Built by `providers/horizons_format.py`.
- Tables are interpolated linearly on unit vectors; use a step of 30 min or less.
- Run `scripts/validate_ephemeris.py` after fetching to confirm agreement with the analytic model (expect hundredths of a degree; degrees means a frame or sign issue).
- **Caveat to resolve with real data:** confirm Horizons' lunar body-fixed frame (ME vs PA, ~0.5 km at the surface) and longitude sign for your query. The parser accepts `--lon-sign -1`.

### SPICE (integration point)
`providers/ephemeris_spice.py` calls `spkpos(target, et, "MOON_ME", "LT+S", "MOON")` with DE440 and the lunar PA/ME kernels. Implemented, **not validated** here.

## 3. Topocentric geometry

Body vector **b** (Moon centre → body, km, ME frame) and observer **o** = (R + h)·**up**. Relative vector **r** = **b** − **o** is projected onto E, N, U:

- elevation = atan2(r·U, √((r·E)² + (r·N)²))
- azimuth = atan2(r·E, r·N) mod 360°

This includes **parallax** (≈0.26° for Earth, negligible for the Sun).

## 4. Terrain horizon and visibility

A **horizon mask** is the skyline elevation as a function of azimuth. It is interpolated circularly.

- **clearance** = geometric elevation − skyline(azimuth of the body)
- **visible** ⇔ clearance > 0 (body centre above the skyline)
- **Solar disk fraction**: area of a disk of radius 0.2666° above a locally straight skyline, from the circular-segment formula. Reported alongside, not used for the visible flag.

A body can therefore be:
1. Above terrain horizon (visible)
2. **Blocked by terrain**: geometric elevation > 0 but below the skyline
3. Below the geometric horizon

The UI keeps these distinct everywhere.

### Building masks from LOLA
`services/horizon.py::build_horizon_mask_from_dem` ray-marches a gridded DEM along each azimuth (default 1° steps, 150 km range, half-pixel sampling, bilinear interpolation). Terrain angle = atan((h − s²/2R − h_obs)/s), so **lunar curvature** is included. Stereographic scale distortion (<0.2% poleward of 85°S) is ignored. Tested with synthetic walls and flat plains (`tests/test_horizon_intervals.py`).

The three mission candidates have committed two-tier masks in `data/scientific/horizon_masks/`, built by `scripts/build_site_horizon_masks.py` at 2 m observer height: the 5 m/pixel site DEM out to its edge (6.3–7.7 km), then the 80 m/pixel wide polar DEM to 150 km, taking the higher tier per azimuth. `services/site_data.py::load_mask` loads them for Phase 3; a location without a mask gets no skyline rather than a fabricated one.

### Demo skylines
`data/demo/horizon_masks.json` is produced by `scripts/generate_demo_data.py` from seeded random harmonics plus Gaussian "massifs". **They are invented.** Custom coordinates in Demo Mode get a flat (0°) mask and are labelled `geometric_only`, which overestimates visibility near the poles.

## 5. Intervals and metrics

- Samples every `step_minutes` (default 30). The step is coarsened automatically if a window would exceed `max_samples`; the response reports the actual step.
- Visibility edges are placed by **linear interpolation of clearance** between samples, so edge timing is finer than the step.
- Interval algebra produces: sun/earth visible, both visible (intersection), blocked (complement), neither (complement of union), and "not both" (complement of both).
- **Censoring:** any longest-interval metric whose interval touches the window edge is flagged `censored` (shown as "≥"). The true value may be longer.
- **Snapshot events** (time until sunset/Earthset or rise): 30 min forward scan within the lookahead (default 720 h, clipped to the supported range), then bisection to ~30 s.

Metric definitions are in `services/metrics.py`; each has a description shown as a tooltip in the UI.

## 6. Comparison and rescheduling

- Deltas = B − A for every registered metric; percent change for non-percentage metrics.
- Changes below 0.25 h / 0.5 pts / 0.05° are reported as "about the same".
- Trade-off sentences are assembled from the signs of five availability metrics. They state differences, never preferences.
- Comparability notes flag differing modes, data quality, durations, step sizes, and censored values.
- Each `MetricDef.availability_direction` (+1 more availability, −1 longer outage, 0 neutral) only drives wording and the UI's mint/coral tint.

## 7. Provenance levels

| Level | Meaning |
| --- | --- |
| `synthetic` | Invented data (demo skylines) |
| `geometric_only` | Real geometry, no terrain applied |
| `analytic_approximate` | Real physics, truncated model |
| `scientific_sourced` | Sourced dataset (Horizons, SPICE, LOLA) |

A result's overall level is the **weakest** of its ephemeris and terrain-mask levels.

## 8. Not modelled

- Solar power: panel orientation, tracking, lander self-shadowing, dust, temperature, battery.
- Communications: antenna pattern and pointing, link budget, DSN/ground-station visibility from Earth, relay satellites, multipath from terrain.
- Refraction (no atmosphere), terrain-reflected light, thermal environment.
- Earth phase or brightness.

## 9. Known limitations

- Site elevation: catalogue sites now carry a recorded LOLA elevation (sampled from the PGDA 5 m/pix site DEMs, `data/reference/site_elevations.json`) and the scenario geometry adds it to the observer radius. The parallax effect on Sun/Earth elevation is tiny (~0.0005° per km), but the value keeps the geometry consistent with the terrain surface and is validated at load time against the sampled evidence file. Custom coordinates without an explicit `elevation_m` still sit on the reference sphere.
- Demo site coordinates are exact published points (Mazarico et al. 2011), but the served horizon masks in Demo Mode remain synthetic — only the Scientific Mode LOLA builder uses real terrain.
- Map basemaps are Moon Trek imagery (LROC WAC, LOLA shaded relief, LOLA elevation)
  and are **display only**: no visibility number is derived from them. When imagery
  is unavailable the polar map falls back to its vector layers (graticule, LROC PSR
  polygons, IAU Gazetteer crater outlines).
