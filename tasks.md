# Phase 1 — Project Planning & Mission Setup

## Objective

Define the lunar landing sites, mission scenario, and engineering
requirements for our NASA Space Apps Challenge 2026 project.

Our website will help mission planners compare lunar south-pole
landing sites based on sunlight availability, Earth communication
visibility, and proximity to permanently shadowed regions (PSRs).

## Task 1: Select Three Lunar Landing Sites

- [x] Research lunar south-pole landing regions using NASA LROC QuickMap.
- [x] Investigate the following candidate regions:
  - Shackleton Crater Rim
  - Connecting Ridge
  - de Gerlache Crater Rim
- [x] Select one exact coordinate within each region.
- [x] Record the latitude and longitude of each site.
- [x] Record surface elevation, if available.
- [x] Record the source of each site's coordinates.
- [x] Identify nearby permanently shadowed regions (PSRs).

### Deliverable

A table containing three candidate landing sites (full provenance in
[docs/SITES.md](docs/SITES.md)):

| Site | Region | Latitude | Longitude | Elevation | Source |
|------|--------|----------|-----------|-----------|--------|
| A | Shackleton Crater Rim | −89.78° | 204.27°E | 1,734 m (LOLA) | Mazarico et al. 2011, point 4 = NASA 2020 site 004 |
| B | Connecting Ridge | −89.45° | 222.69°E | 1,955 m (LOLA) | Mazarico et al. 2011, point 1 = NASA 2020 site 001 |
| C | de Gerlache Crater Rim | −88.67° | 291.90°E | 1,808 m (LOLA) | Mazarico et al. 2011, point 11 = NASA 2020 site 011 |

Resource: https://quickmap.lroc.asu.edu/

---

## Task 2: Define the Hypothetical Lunar Mission

- [x] Define the mission objective.
- [x] Set the mission duration to 7 Earth days.
- [x] Set the initial landing date to December 1, 2026.
- [x] Set an alternative landing date to December 11, 2026.
- [x] Assume a solar-powered robotic lander.
- [x] Assume the lander has battery storage.
- [x] Assume direct-to-Earth communication capability.

Implemented in `config/lunanav.config.json` → `mission` (served at `GET /api/config`),
with the reasoning in `docs/MISSION.md`. Task 2 names the three candidates and
their A/B/C order; Task 1 fills in their coordinates, elevation, source and nearby
PSRs in `data/demo/sites.json`, and the backend rejects a candidate the catalogue
cannot supply.

### Proposed Mission

**Mission Name:** Polar Ice Scout

**Objective:** Investigate the lunar south-pole environment
and support scientific exploration of potential water ice
near permanently shadowed regions.

**Mission Duration:** 7 Earth days

**Initial Landing Date:** December 1, 2026

**Alternative Landing Date:** December 11, 2026

**Power Source:** Solar panels with battery storage

**Communication:** Direct-to-Earth

### Deliverable

A finalized mission description with objectives, dates,
duration, and spacecraft assumptions.

---

## Task 3: Define Landing Site Requirements

- [x] Define minimum sunlight availability.
- [x] Define minimum Earth visibility.
- [x] Define maximum acceptable communication blackout.
- [x] Include proximity to PSRs as an optional scientific factor.
- [x] Document assumptions and limitations.

Documented in `docs/SITE_REQUIREMENTS.md`. Each threshold is tied to a metric the
app already computes (`sun_visible_pct`, `earth_visible_pct`,
`longest_earth_blackout_hours`), so the criteria are measurable without new code:
a site is judged over both landing dates, censored blackouts are reported as lower
bounds rather than passes, and PSR proximity is a measured distance from the LROC
catalogue but stays a preference, because nothing is ranked without stated
weights. The three candidates are evaluated against the thresholds there, using
Task 1's coordinates.

### Proposed Requirements

| Requirement | Target |
|-------------|--------|
| Minimum sunlight availability | 60% |
| Minimum Earth visibility | 50% |
| Maximum communication blackout | 12 hours |
| Proximity to PSRs | Optional preference |

**Note:** These are hypothetical demonstration requirements,
not official NASA mission specifications.

### Deliverable

A list of measurable criteria used to evaluate and compare
landing sites.

---

## Task 4: Finalize Project Specifications

- [x] Combine site coordinates and mission requirements.
- [x] Create a shared mission configuration file.
- [x] Ensure frontend and backend developers use the same data.
- [x] Identify the NASA datasets needed for Phase 2.
- [x] Review and approve the Phase 1 specifications.

### Deliverable

A finalized mission specification shared with the team:
[docs/SPECIFICATIONS.md](docs/SPECIFICATIONS.md). The machine-readable version is
`config/lunanav.config.json` (`mission`, `simulation.landing_presets`,
`requirements`, `datasets`), served by the backend at `GET /api/config` and
mirrored in `frontend/src/types/api.ts`.

---

## Phase 1 Completion Checklist

- [x] Three exact lunar coordinates selected and verified.
- [x] Coordinate sources documented.
- [x] Mission objective defined.
- [x] Mission duration and landing dates finalized.
- [x] Sunlight and communication requirements finalized.
- [x] Mission specifications shared with the team: [docs/SPECIFICATIONS.md](docs/SPECIFICATIONS.md).

## Phase 2 — Next Steps

Extend the NASA scientific data integration, in this order:

1. JPL Horizons — Sun and Earth positions (already used live in JPL and Scientific
   modes; freeze tables so runs work offline).
2. NASA LOLA — lunar topography and terrain elevations (elevations are sampled;
   real horizon masks are the missing piece).
3. LROC QuickMap — lunar mapping and site references (imagery basemaps and site
   cross-checks).

With real terrain in place, these datasets turn the current synthetic skylines
into measured sunlight availability and Earth communication windows.

The datasets this build needs and the order to tackle them in are listed in
[docs/SPECIFICATIONS.md](docs/SPECIFICATIONS.md) §5: real LOLA horizon masks for
each candidate (which turns Scientific Mode on), frozen Horizons tables for
offline reproducibility, and a re-derived PSR catalogue with the product
versions recorded.

## Resources

- NASA Space Apps Challenge:
  https://www.spaceappschallenge.org/

- NASA LROC QuickMap:
  https://quickmap.lroc.asu.edu/

- JPL Horizons API:
  https://ssd-api.jpl.nasa.gov/doc/horizons.html

- NASA South Pole Topography:
  https://pgda.gsfc.nasa.gov/products/78
