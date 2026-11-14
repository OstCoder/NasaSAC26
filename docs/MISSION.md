# Mission definition

What LunaNav is scoped to for the 2026 build: one hypothetical robotic mission and
three candidate landing sites near the lunar south pole. The scenario is a
decision, not a claim about a real mission.

The machine-readable version lives in `config/lunanav.config.json` → `mission`,
served to the frontend at `GET /api/config`; the site catalogue is
`data/demo/sites.json`. This page explains the choices.

## Mission: Polar Ice Scout

**7-day solar-powered robotic mission investigating lunar polar terrain.**

| | |
| --- | --- |
| Objective | Investigate the lunar south-pole environment and support scientific exploration of potential water ice near permanently shadowed regions |
| Surface duration | 7 Earth days (168 h) |
| Initial landing | 2026-12-01 12:00 UTC |
| Alternative landing | 2026-12-11 12:00 UTC |
| Power | Solar panels with battery storage |
| Communication | Direct-to-Earth |
| Vehicle | Robotic lander/rover, uncrewed |

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

## Candidate sites

Task 2 owns *which* three sites the mission is flown at and their A → B → C order;
Task 1 owns the numbers in those rows. `mission.candidate_sites` is that ordered
list of ids, and every id must exist in `data/demo/sites.json` with a recorded
coordinate `source` — otherwise `SiteRepository` refuses to serve the catalogue.
That check is the seam between the two tasks: when Task 1 replaces the approximate
coordinates with LROC-derived ones, only `data/demo/sites.json` changes.

| # | Site | `site_id` | Region | Latitude | Longitude (east+) | Elevation | Coordinate source | Nearby PSRs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | Peak Near Shackleton | `peak-near-shackleton` | Shackleton Crater Rim | −88.81° | 123.64° | not yet recorded | Approximate literature value | not yet recorded |
| B | Shackleton–de Gerlache Connecting Ridge | `connecting-ridge` | Connecting Ridge | −89.45° | 222.69° (−137.31°) | not yet recorded | Approximate literature value | not yet recorded |
| C | de Gerlache Rim | `de-gerlache-rim` | de Gerlache Crater Rim | −88.71° | −68.80° | not yet recorded | Approximate | not yet recorded |

Rows follow Task 1's table order, and that order is what the planner and
`GET /api/sites` use: candidates first, in mission order, then the rest of the
catalogue. "not yet recorded" is literal — `elevation_m` is `null` and
`nearby_psrs` is empty in the catalogue until Task 1 fills them, and the planner
prints the gap instead of substituting a plausible number.

The three are deliberately different in elevation and Earth-facing geometry, so
comparing them separates illumination from Earth visibility instead of sampling
one terrain type three times.

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
| Elevation | `elevation_m` (metres above the 1737.4 km reference sphere; `null` until recorded) |
| Source | `source` (required for candidates; the loader rejects a candidate without one) |
| Nearby PSRs | `nearby_psrs` (feature names; empty until recorded) |
| How the point was chosen | `coordinate_note` |

If Task 1 settles on a different feature than one of these three, change the id in
`mission.candidate_sites` and the matching record together — the loader rejects a
candidate the catalogue cannot supply, so the two files cannot drift apart
silently.

## Provenance and limits

- Each site is an approximate point on or near a named feature, not an official
  Artemis landing-region definition and not derived from a lander DEM. The
  `source` field in `data/demo/sites.json` says so per site.
- Coordinates should be checked against LOLA products and the IAU Gazetteer
  before any scientific use; the served terrain skylines in Demo Mode are
  synthetic by design.
- Adding, removing or reordering candidates means editing
  `mission.candidate_sites` in the config and the matching entries in
  `data/demo/sites.json` (then regenerating demo skylines if coordinates change —
  see [ADAPTATION_GUIDE.md](ADAPTATION_GUIDE.md)).
