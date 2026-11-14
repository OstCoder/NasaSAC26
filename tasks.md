
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
| A | Shackleton Rim | −89.78° | 204.27°E | 1,734 m (LOLA) | Mazarico et al. 2011, point 4 = NASA 2020 site 004 |
| B | Connecting Ridge | −89.45° | 222.69°E | 1,955 m (LOLA) | Mazarico et al. 2011, point 1 = NASA 2020 site 001 |
| C | de Gerlache Rim | −88.67° | 291.90°E | 1,808 m (LOLA) | Mazarico et al. 2011, point 11 = NASA 2020 site 011 |

Resource: https://quickmap.lroc.asu.edu/

---

## Task 2: Define the Hypothetical Lunar Mission

- [ ] Define the mission objective.
- [ ] Set the mission duration to 7 Earth days.
- [ ] Set the initial landing date to December 1, 2026.
- [ ] Set an alternative landing date to December 11, 2026.
- [ ] Assume a solar-powered robotic lander.
- [ ] Assume the lander has battery storage.
- [ ] Assume direct-to-Earth communication capability.

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

- [x] Three exact lunar coordinates selected and verified.
- [x] Coordinate sources documented.
- [ ] Mission objective defined.
- [ ] Mission duration and landing dates finalized.
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
