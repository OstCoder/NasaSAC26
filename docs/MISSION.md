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

In the order the planner treats them, all near the south pole:

| # | Site | `site_id` | Latitude | Longitude (east+) | Why it is a candidate |
| --- | --- | --- | --- | --- | --- |
| 1 | Peak Near Shackleton | `peak-near-shackleton` | −88.81° | 123.64° | High-standing massif on the far side of Shackleton crater as seen from Earth: low local horizon and long illumination, at the cost of Earth sitting low. |
| 2 | Shackleton–de Gerlache Connecting Ridge | `connecting-ridge` | −89.45° | 222.69° (−137.31°) | Ridge crest between the two craters, discussed in the literature for extended illumination. |
| 3 | de Gerlache Rim | `de-gerlache-rim` | −88.71° | −68.80° | Rim on the Earth-facing side of the pole: the counterpart case where direct-to-Earth geometry is favoured over illumination. |

The three are deliberately different in elevation and Earth-facing geometry, so
comparing them separates illumination from Earth visibility instead of sampling
one terrain type three times.

Reference crater centres from the IAU Gazetteer (`data/reference/moon_craters.json`):
Shackleton −89.67°, 129.78°, 20.9 km; de Gerlache −88.48°, −88.34°, 32.7 km.

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
