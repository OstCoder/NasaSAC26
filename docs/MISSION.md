# Mission definition

What LunaNav is scoped to for the 2026 build: one hypothetical robotic mission and
three candidate landing sites near the lunar south pole. The scenario is a
decision, not a claim about a real mission.

The machine-readable version lives in `config/lunanav.config.json` → `mission`, and
the site catalogue in `data/demo/sites.json`. This page explains the choices.

## Scenario

**7-day solar-powered robotic mission investigating lunar polar terrain.**

| | |
| --- | --- |
| Surface duration | 7 days (168 h) |
| Power | Solar, no radioisotope source |
| Vehicle | Robotic lander/rover, uncrewed |
| Objective | Characterise Sun and direct-to-Earth visibility over the polar terrain from each candidate site |
| Landing | Default 2027-01-15 12:00 UTC (within the supported 2026–2030 window) |

Why 7 days: it is a plausible small-lander surface lifetime, and it spans the
roughly 27.3-day lunar day enough to expose both the long polar illumination
stretches and the terrain-shadowed gaps that matter for a solar-powered vehicle.
A 14-day default was rejected because it hides the trade-off a solar mission
actually faces.

What this scenario is **not**: LunaNav reports when the Sun is above the terrain
horizon. That is not available power, and Earth visibility is not a comms link.
There is no power model, thermal model or link budget in this build (those are
flagged extension points). See [METHODOLOGY.md](METHODOLOGY.md).

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
