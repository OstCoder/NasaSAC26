# Mission definition

What LunaNav is scoped to for the 2026 build: one hypothetical robotic mission and
three candidate landing sites near the lunar south pole. The scenario is a
decision, not a claim about a real mission.

The machine-readable version lives in `config/lunanav.config.json` → `mission` and
`requirements`, and the site catalogue in `data/demo/sites.json`. This page explains
the choices; the finalized Phase 1 specification, including the requirement
thresholds, dataset list and sign-off, is [SPECIFICATIONS.md](SPECIFICATIONS.md).

## Mission: Polar Ice Scout

**Polar Ice Scout — 7-day solar-powered robotic mission investigating lunar polar terrain.**

| | |
| --- | --- |
| Surface duration | 7 days (168 h) |
| Power | Solar panels with battery storage, no radioisotope source |
| Communication | Direct-to-Earth, no relay |
| Vehicle | Robotic lander/rover, uncrewed |
| Objective | Investigate the lunar south-pole environment and support scientific exploration of potential water ice near permanently shadowed regions |
| Primary landing | 2026-12-01 00:00 UTC (first of the two landing presets in the app) |
| Alternate landing | 2026-12-11 00:00 UTC (the second preset, for a one-click date comparison) |
| Requirements | ≥ 60 % sunlight, ≥ 50 % Earth visibility, ≤ 12 h Earth blackout over the 7-day window; PSR proximity is a preference ([SPECIFICATIONS.md](SPECIFICATIONS.md)) |

Both landing dates are one-click presets in the planner; the initial date is the
default landing time in the config, so an unedited run is the mission. The loader
enforces that: `duration_days × 24` must equal `simulation.default_duration_hours`,
the initial date must equal `simulation.default_landing_utc`, and both dates must
sit inside the supported window, or the backend refuses to start.

Why 7 days: it is a plausible small-lander surface lifetime, and it spans enough
of the roughly 27.3-day lunar day to expose both the long polar illumination
stretches and the terrain-shadowed gaps that matter for a solar-powered vehicle.
A 14-day default was rejected because it hides the trade-off a solar mission
actually faces.

Why those dates: December 2026 sits inside the supported 2026–2030 window. The
11 December alternative is ten days later so the same site and duration can be
compared across two landing dates — that isolates how much the date alone moves
the numbers.

What this scenario is **not**: LunaNav reports when the Sun is above the terrain
horizon and when Earth is visible. Neither implies a working power system. Battery
storage is assumed in the scenario but **not** simulated — there is no state of
charge, eclipse or link-budget model in this build
(`features.experimental_power_model` and `experimental_comm_link_budget` are off).
Sun above terrain is not available power, and Earth visibility is not a comms
link. See [METHODOLOGY.md](METHODOLOGY.md).

The measurable criteria a site must meet to qualify for this mission — minimum
sunlight, minimum Earth visibility, maximum communication blackout, and PSR
proximity as a preference — are in [SITE_REQUIREMENTS.md](SITE_REQUIREMENTS.md).

## Candidate sites

Task 2 owns *which* three sites the mission is flown at and their A → B → C order;
Task 1 owns the numbers in those rows. `mission.candidate_sites` is that ordered
list of ids, and `data/demo/sites.json` declares the same ids in
`mission_candidates`. `SiteRepository` refuses to load the catalogue if the two
lists disagree, if an id is unknown, if a candidate repeats, or if a candidate has
no recorded coordinate `source` — so the mission and the coordinates cannot drift
apart silently. Full provenance, verification steps and dataset links for the rows
below are in [SITES.md](SITES.md).

| # | Site | `site_id` | Latitude | Longitude (east+) | Elevation (LOLA) | Why it is a candidate |
| --- | --- | --- | --- | --- | --- | --- |
| A | Shackleton Rim | `shackleton-rim` | −89.78° | 204.27°E (−155.73°) | 1,734 m | Rim crest of the classic Shackleton PSR site (Mazarico 2011 pt 4 = NASA 2020 site 004). Looks directly into the ~4 km² Shackleton floor PSR (nearest mapped PSR 2.5 km), balanced Sun/Earth geometry. |
| B | Shackleton–de Gerlache Connecting Ridge | `connecting-ridge` | −89.45° | 222.69°E (−137.31°) | 1,955 m | Ridge crest (Mazarico 2011 pt 1 = NASA 2020 site 001), the highest of the three. Nearest mapped (>5 km²) PSR 11.5 km; published kilometre-scale PSRs (e.g. C1-0/C1-1, 70–100 m) sit below the product threshold. |
| C | de Gerlache Rim | `de-gerlache-rim` | −88.67° | 291.90°E (−68.10°) | 1,808 m | Rim on the Earth-facing side of the pole (Mazarico 2011 pt 11 = NASA 2020 site 011), the counterpart case where direct-to-Earth geometry is favoured over illumination. Nearest mapped PSR 12.1 km. |

The three are deliberately different in elevation and Earth-facing geometry, so
comparing them separates illumination from Earth visibility instead of sampling
one terrain type three times. `peak-near-shackleton` (Mazarico 2011 pt 7 =
NASA 2020 site 007) is kept in the catalogue as a reference site.

Reference crater centres from the IAU Gazetteer (`data/reference/moon_craters.json`):
Shackleton −89.67°, 129.78°, 20.9 km; de Gerlache −88.48°, −88.34°, 32.7 km.

## Contract with Task 1

Task 1's deliverable is a table of three sites: one exact coordinate per region,
latitude and longitude, surface elevation, coordinate source, and nearby PSRs.
Those columns are exactly the fields of a site record, so Task 1 can be finished
without editing Task 2:

| Task 1 column | `data/demo/sites.json` field |
| --- | --- |
| Site / Region | `name`, `region` (the region names in `tasks.md`) |
| Latitude / Longitude | `latitude_deg`, `longitude_deg` (east-positive) |
| Elevation | `elevation_m` (metres above the 1737.4 km reference sphere) |
| Source | `source` (required for candidates; the loader rejects a candidate without one) |
| Nearby PSRs | `nearest_psr`, `psrs_within_10_km` (filled at load time from the LROC PSR catalogue) |
| How the point was chosen | `coordinate_note` |

Changing a candidate means editing the id in `mission.candidate_sites`, the
matching record in `data/demo/sites.json`, and the `mission_candidates` list — the
loader rejects any drift between them.

## Provenance and limits

- Coordinates are exact published points: the LOLA south-pole candidate points
  of Mazarico et al. 2011, which the NASA 2020 south-pole site numbering
  inherits; elevations are LOLA samples from the matching PGDA 5 m/pix site
  DEMs. Per-site citations live in the `sources` field of
  `data/demo/sites.json` and in [SITES.md](SITES.md).
- PSR distances come from the LROC south-pole PSR shapefile (PSRs > 5 km²),
  computed with the same south polar stereographic projection as the map.
  Sub-kilometre PSRs are below that product's threshold; published values for
  them are quoted per site in SITES.md.
- Coordinates are recorded to the precision published in the sources; they
  should still be checked against the raw products before any real mission
  use. The served terrain skylines in Demo Mode remain synthetic by design.
- Adding, removing or reordering candidates means editing
  `mission.candidate_sites` in the config, `mission_candidates` and the matching
  entries in `data/demo/sites.json` (then regenerating demo skylines if
  coordinates change — see [ADAPTATION_GUIDE.md](ADAPTATION_GUIDE.md)).
