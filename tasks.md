
# Phase 1 — Project Planning & Mission Setup

## Objective

Define the lunar landing sites, mission scenario, and engineering
requirements for our NASA Space Apps Challenge 2026 project.

Our website will help mission planners compare lunar south-pole
landing sites based on sunlight availability, Earth communication
visibility, and proximity to permanently shadowed regions (PSRs).

## Task 1: Select Three Lunar Landing Sites

- [ ] Research lunar south-pole landing regions using NASA LROC QuickMap.
- [ ] Investigate the following candidate regions:
  - Shackleton Crater Rim
  - Connecting Ridge
  - de Gerlache Crater Rim
- [ ] Select one exact coordinate within each region.
- [ ] Record the latitude and longitude of each site.
- [ ] Record surface elevation, if available.
- [ ] Record the source of each site's coordinates.
- [ ] Identify nearby permanently shadowed regions (PSRs).

### Deliverable

A table containing three candidate landing sites:

| Site | Region | Latitude | Longitude | Elevation | Source |
|------|--------|----------|-----------|-----------|--------|
| A | Shackleton Rim | TBD | TBD | TBD | TBD |
| B | Connecting Ridge | TBD | TBD | TBD | TBD |
| C | de Gerlache Rim | TBD | TBD | TBD | TBD |

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

- [ ] Define minimum sunlight availability.
- [ ] Define minimum Earth visibility.
- [ ] Define maximum acceptable communication blackout.
- [ ] Include proximity to PSRs as an optional scientific factor.
- [ ] Document assumptions and limitations.

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

- [ ] Combine site coordinates and mission requirements.
- [ ] Create a shared mission configuration file.
- [ ] Ensure frontend and backend developers use the same data.
- [ ] Identify the NASA datasets needed for Phase 2.
- [ ] Review and approve the Phase 1 specifications.

### Deliverable

A finalized mission specification shared with the team.

---

## Phase 1 Completion Checklist

- [ ] Three exact lunar coordinates selected and verified.
- [ ] Coordinate sources documented.
- [x] Mission objective defined.
- [x] Mission duration and landing dates finalized.
- [ ] Sunlight and communication requirements finalized.
- [ ] Mission specifications shared with the team.

## Phase 2 — Next Steps

Integrate NASA scientific data sources:

1. JPL Horizons — Sun and Earth positions.
2. NASA LOLA — Lunar topography and terrain elevations.
3. LROC QuickMap — Lunar mapping and site references.

Use these datasets to calculate and visualize sunlight
availability and Earth communication windows.

## Resources

- NASA Space Apps Challenge:
  https://www.spaceappschallenge.org/

- NASA LROC QuickMap:
  https://quickmap.lroc.asu.edu/

- JPL Horizons API:
  https://ssd-api.jpl.nasa.gov/doc/horizons.html

- NASA South Pole Topography:
  https://pgda.gsfc.nasa.gov/products/78
