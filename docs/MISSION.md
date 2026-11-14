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

In the order the planner treats them, all near the south pole. These are the
Task 1 site selections — exact published coordinates with recorded elevation
and PSR context; the full provenance chain, verification steps and dataset
links are in [SITES.md](SITES.md).

| # | Site | `site_id` | Latitude | Longitude (east+) | Elevation (LOLA) | Why it is a candidate |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Shackleton Rim | `shackleton-rim` | −89.78° | 204.27°E (−155.73°) | 1,734 m | Rim crest of the classic Shackleton PSR site (Mazarico 2011 pt 4 = NASA 2020 site 004). Looks directly into the ~4 km² Shackleton floor PSR (nearest mapped PSR 2.5 km), balanced Sun/Earth geometry. |
| 2 | Shackleton–de Gerlache Connecting Ridge | `connecting-ridge` | −89.45° | 222.69°E (−137.31°) | 1,955 m | Ridge crest (Mazarico 2011 pt 1 = NASA 2020 site 001), the highest of the three. Nearest mapped (>5 km²) PSR 11.5 km; published kilometre-scale PSRs (e.g. C1-0/C1-1, 70–100 m) sit below the product threshold. |
| 3 | de Gerlache Rim | `de-gerlache-rim` | −88.67° | 291.90°E (−68.10°) | 1,808 m | Rim on the Earth-facing side of the pole (Mazarico 2011 pt 11 = NASA 2020 site 011), the counterpart case where direct-to-Earth geometry is favoured over illumination. Nearest mapped PSR 12.1 km. |

The three are deliberately different in elevation and Earth-facing geometry, so
comparing them separates illumination from Earth visibility instead of sampling
one terrain type three times. `peak-near-shackleton` (Mazarico 2011 pt 7 =
NASA 2020 site 007) is kept in the catalogue as a reference site.

Reference crater centres from the IAU Gazetteer (`data/reference/moon_craters.json`):
Shackleton −89.67°, 129.78°, 20.9 km; de Gerlache −88.48°, −88.34°, 32.7 km.

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
  `mission.candidate_sites` in the config and the matching entries in
  `data/demo/sites.json` (then regenerating demo skylines if coordinates change —
  see [ADAPTATION_GUIDE.md](ADAPTATION_GUIDE.md)).
