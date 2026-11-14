# Phase 1 — Final mission specification

**Version 1.0.0 · approved 2026-11-14 · NASA Space Apps Challenge 2026 (Lunar Landing Site Navigator)**

This is the Task 4 deliverable: the single description of the mission, the three
candidate landing sites, the measurable requirements, the datasets Phase 2 needs,
and the sign-off. Everything scientific here is also machine-readable in
[`config/lunanav.config.json`](../config/lunanav.config.json), so the document and
the running application cannot drift apart without a test failing
(`backend/tests/test_spec_requirements.py`).

The mission is hypothetical. It is a demonstration scenario for the challenge, not
a flown or approved NASA mission.

## 1. Mission

| Field | Value |
| --- | --- |
| Name | Polar Ice Scout |
| Profile | `solar_powered_robotic` — uncrewed solar-powered lander |
| Objective | Investigate the lunar south-pole environment and support scientific exploration of potential water ice near permanently shadowed regions (PSRs) |
| Surface duration | 7 Earth days (168 h) |
| Primary landing | 2026-12-01 00:00 UTC |
| Alternate landing | 2026-12-11 00:00 UTC |
| Power | Solar panels with battery storage (no radioisotope source) |
| Communication | Direct-to-Earth, no relay |
| Default mode in the app | JPL live; Demo for offline work; Scientific when sourced data is present |

Both landing dates are presets in the app, so comparing 1 December with
11 December is one click. The 7-day duration spans enough of the 27.3-day lunar
day to expose both the long polar illumination stretches and the terrain-shadowed
gaps that decide a solar mission; a 14-day default would hide them.

## 2. Landing sites

Exact published coordinates, with LOLA surface elevation and nearest mapped PSR.
Full provenance and verification steps: [SITES.md](SITES.md).

| Site | `site_id` | Latitude | Longitude (east+) | Elevation | Slope | Nearest mapped PSR | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Shackleton Crater Rim | `shackleton-rim` | −89.78° | 204.27° (−155.73°) | 1,734 m | 8.8° | 2.48 km (Shackleton floor, 233.7 km²) | Mazarico et al. 2011 point 4 = NASA 2020 site 004 |
| Connecting Ridge | `connecting-ridge` | −89.45° | 222.69° (−137.31°) | 1,955 m | 3.8° | 11.5 km (Spudis, 53.3 km²) | Mazarico et al. 2011 point 1 = NASA 2020 site 001 |
| de Gerlache Crater Rim | `de-gerlache-rim` | −88.67° | 291.90° (−68.10°) | 1,808 m | 3.8° | 12.1 km (de Gerlache, 243.4 km²) | Mazarico et al. 2011 point 11 = NASA 2020 site 011 |

`peak-near-shackleton` (Mazarico point 7 = NASA 2020 site 007) stays in the
catalogue as a reference site; it is not a mission candidate. The three
candidates deliberately differ in elevation and Earth-facing geometry, so a
comparison separates illumination from Earth visibility instead of sampling one
terrain type three times.

Coordinates are selenographic planetocentric, Mean Earth / Polar Axis,
east-positive in [−180°, 180°). Elevations are metres above the 1737.4 km
reference sphere, sampled from the PGDA 5 m/pix LOLA site DEMs.

## 3. Requirements and how each one is measured

All three thresholds are stored in `config/lunanav.config.json → requirements`
and evaluated over the whole mission window from the landing time.

| # | Requirement | Target | Metric | Rule |
| --- | --- | --- | --- | --- |
| R1 | Minimum sunlight availability | ≥ 60 % of the window | `sun_visible_pct` | Sun centre above the terrain skyline |
| R2 | Minimum Earth visibility | ≥ 50 % of the window | `earth_visible_pct` | Earth centre above the terrain skyline |
| R3 | Maximum communication blackout | ≤ 12 h | `longest_earth_blackout_hours` | Longest continuous interval with Earth below the skyline |
| R4 | Proximity to PSRs | Optional preference | `nearest_psr.distance_km` | Reported, never pass/fail |

Notes that matter for reading a result:

- R1 and R2 are shares of the **mission window**, not of a lunar day, so a longer
  mission does not automatically improve them. Compare percentages only between
  equal durations.
- A value that touches the window edge is a **lower bound** (the API flags it
  `censored`). For R1/R2 a censored value that already clears the threshold still
  passes; below the threshold the check reports `unknown`, never `not_met`. For R3
  a censored value under 12 h is `unknown`, because the true blackout can only be
  longer.
- The overall verdict is three-state: **met** (all three pass), **not met** (at
  least one fails), **undecided** (nothing fails but something cannot be decided).
  It is a constraint check, not a ranking, and it never picks a site.
- R4 is context, not compliance. Only PSRs larger than ~5 km² are in the mapped
  LROC catalogue, so a site can sit metres from a sub-kilometre PSR and still show
  a kilometre-scale nearest distance (see [SITES.md](SITES.md) for the published
  sub-kilometre values).

These are hypothetical demonstration targets, **not** official NASA mission
specifications. Changing one is a one-line edit in the config: no code, no UI
change.

## 4. One shared configuration for backend and frontend

`config/lunanav.config.json` is the only place these values exist. The backend
loads it at startup (`backend/app/core/settings.py`), the frontend fetches the
public subset from `GET /api/config`, and `frontend/src/types/api.ts` mirrors the
contract.

| Config section | What it fixes | Consumed by |
| --- | --- | --- |
| `mission` | name, profile, objective, `spacecraft` (power and communication), duration, landing dates, candidate site ids | `/api/config`, planner header, docs |
| `simulation` | supported window, `default_landing_utc`, `landing_presets`, duration/step limits | planner, comparison, rescheduler, date presets |
| `requirements` | R1–R3 thresholds, PSR preference, basis text | `/api/config`, `POST /api/requirements`, methodology page |
| `coordinates` | frame, longitude convention, reference radius, map latitude bounds | every coordinate calculation, map projection |
| `datasets` | paths to the site catalogue, PSR catalogue, elevation evidence, masks, cache | site and terrain services |
| `providers` | ephemeris and terrain provider per mode | mode switching and provenance labels |
| `visibility` | angular radii and visibility rules | visibility calculation |

API surface used by the team:

| Endpoint | Purpose |
| --- | --- |
| `GET /api/config` | mission, requirements, landing presets, supported window, feature flags |
| `GET /api/sites` | candidate + reference sites with elevation, slope, nearest PSR, citations |
| `GET /api/psrs` | mapped PSR polygons (filterable by area, latitude, distance to a site) |
| `POST /api/scenario` | Sun/Earth visibility, intervals and metrics for one site/date |
| `POST /api/requirements` | the same scenario checked against R1–R3 |
| `POST /api/compare`, `POST /api/reschedule` | two scenarios, descriptive deltas only |

Rule for the team: if a number appears in the UI, in a slide or in a doc, it comes
from this config or from an API response — never from a literal in a component.

## 5. NASA datasets for Phase 2

| Dataset | Provider | What it gives us | Used for | Where it is |
| --- | --- | --- | --- | --- |
| JPL Horizons (SSD API) | NASA/JPL Solar System Dynamics | Moon geocentric state, sub-solar and sub-Earth points, Sun/Earth distances | Sun and Earth geometry for every scenario | Live, `providers/ephemeris_horizons_live.py`; optional frozen tables in `data/scientific/ephemeris/{sun,earth}.json` |
| LOLA 5 m/pix south-pole site DEMs | NASA GSFC PGDA (products/78) | Elevation, slope and terrain per NASA 2020 site | Site elevations, buildable horizon masks | `data/cache/lola_5mpp/` → sampled evidence `data/reference/site_elevations.json` |
| LROC NAC polar PSR shapefile (south) | LROC / ASU | Permanently shadowed region polygons > 5 km² | PSR proximity metric and map layer | `data/reference/psrs.json` (built by `backend/scripts/build_psr_catalogue.py`) |
| LROC WAC global mosaic | LROC / ASU via Moon Trek | Optical basemap | Polar map, whole-Moon map, 3D globe texture | Served through the imagery provider from Moon Trek tiles |
| LOLA shaded relief / elevation tiles | NASA/GSFC LOLA via Moon Trek | Display elevation and relief | Basemap layers, 3D globe shape | `imagery.layers` in the config |
| IAU Gazetteer of Planetary Nomenclature | USGS | Named crater centres and diameters | Map labels and orientation | `data/reference/moon_craters.json` |
| SPICE kernels (DE440 + lunar PA/ME) | NAIF | High-accuracy frames and light time | Alternative to Horizons tables (integration point) | `data/scientific/spice/`, `providers/ephemeris_spice.py` |

Phase 2 work that these datasets enable, in order:

1. Build real LOLA horizon masks for each candidate (`backend/scripts/build_horizon_mask.py`),
   which turns Scientific Mode on and replaces the synthetic demo skylines.
2. Fetch and freeze Horizons tables so the demo runs offline and reproducibly.
3. Re-derive the PSR catalogue and elevations from the raw products for the
   submitted build, and record the product versions in `data/reference/`.

## 6. Assumptions and limitations

- Visibility is **body centre above the terrain skyline**. It is not available
  power and not a working radio link: no power model, thermal model, antenna
  pattern or link budget is included.
- Demo Mode skylines are synthetic; only the Scientific Mode builder applies real
  LOLA terrain. Results carry a provenance label, and the overall quality is the
  weakest input.
- Missing scientific data is never substituted: the API returns
  `503 SCIENTIFIC_DATA_UNAVAILABLE` instead.
- Coordinates are exact published points, checked against the matching DEMs, but
  they are not landing-certified sites. Verify against the raw products and
  LROC QuickMap before operational use.
- Comparisons and requirement checks describe differences and compliance. They do
  not rank or recommend sites.

## 7. Review and approval

| Section | Owner | Status |
| --- | --- | --- |
| Task 1 — landing sites, elevations, PSR proximity | sites | Approved 2026-11-14 |
| Task 2 — mission objective, duration, landing dates | mission | Approved 2026-11-14 |
| Task 3 — sunlight, Earth-visibility and blackout requirements | requirements | Approved 2026-11-14 |
| Task 4 — combined specification, shared config, dataset list | integration | Approved 2026-11-14 |

Approved by the LunaNav team on 2026-11-14 (commits by `OstCoder` and Aarush Gutha); the role owners above are accountable for their sections. Record any later change here.

Change control: edit the config first, run `cd backend && pytest` and
`cd frontend && npm run build`, then update this page and `docs/MISSION.md`.
Bumping `specification.version` in the config is how the team signals that the
mission definition changed.

## 8. Task 4 checklist → where it is satisfied

| Task 4 item | Where |
| --- | --- |
| Combine site coordinates and mission requirements | §2 + §3 here; `requirements` and `mission.candidate_sites` in one config; `POST /api/requirements` evaluates a site against R1–R3 |
| Create a shared mission configuration file | `config/lunanav.config.json` (single source for mission, dates, requirements, datasets, providers) |
| Ensure frontend and backend developers use the same data | `GET /api/config` serves the same file; `frontend/src/types/api.ts` mirrors it; date presets and the requirements page read it; parity covered by `backend/tests/test_spec_requirements.py` |
| Identify the NASA datasets needed for Phase 2 | §5 |
| Review and approve the Phase 1 specifications | §7 |
