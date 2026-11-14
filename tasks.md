
# Phase 3 — Lunar Visibility & Mission Calculations

## Objective

Develop the scientific calculation engine for our NASA
Space Apps Challenge 2026 Lunar Landing Site Navigator.

Using the astronomical and terrain data collected in
Phase 2, calculate when the Sun and Earth are visible
from each selected lunar landing site.

Analyze sunlight availability, Earth communication
windows, terrain obstructions, and mission feasibility.

By the end of Phase 3, our backend should be able to
evaluate and compare lunar landing sites using actual
astronomical data and clearly documented assumptions.

---

## Task 1: Calculate Geometric Sun Visibility

- [x] Load Sun position data generated in Phase 2.
- [x] Read the Sun's elevation at each timestamp.
- [x] Determine whether the Sun is above or below
      the local geometric horizon.
- [x] Calculate geometric Sun visibility for every
      observation in the mission timeline.
- [x] Store visibility results as Boolean values.
- [x] Preserve Sun azimuth and elevation measurements.
- [x] Handle observations near the horizon carefully.
- [x] Test calculations with positive, negative,
      and zero elevation angles.

### Calculation

For a point-source geometric approximation:

Sun visible = Sun elevation > 0°

Sun not visible = Sun elevation <= 0°

This initially ignores terrain and the Sun's
apparent angular diameter.

### Example

| Time (UTC) | Sun Elevation | Visible |
|------------|---------------|---------|
| 00:00 | +3.2° | Yes |
| 01:00 | +1.5° | Yes |
| 02:00 | -0.8° | No |
| 03:00 | -2.1° | No |

Example values are illustrative, not NASA measurements.

### Deliverable

A Python function that determines geometric Sun
visibility at each timestamp.

Implemented in `backend/app/services/geometric.py`
(`geometric_visibility`, `sun_visibility_response`) and served at
`GET /api/geometric-sun?site_id=..&window=initial|alternative`. It reads the
committed Phase 2 series, keeps each azimuth and elevation, stores a boolean per
timestamp, and flags samples within the Sun's 0.2666 deg radius as grazing
without changing the `> 0` rule. Terrain is separate (`GET /api/phase3`); the
two results are labelled differently on purpose.

---

## Task 2: Calculate Geometric Earth Visibility

- [x] Load Earth position data generated in Phase 2.
- [x] Read Earth's elevation at each timestamp.
- [x] Determine whether Earth is above or below
      the local geometric horizon.
- [x] Calculate geometric Earth visibility throughout
      the mission timeline.
- [x] Store Earth visibility as Boolean values.
- [x] Preserve Earth azimuth and elevation measurements.
- [x] Account for changing Earth positions over time
      using the Horizons ephemeris.
- [x] Test calculations with different locations
      and observation times.

### Calculation

For a point-source geometric approximation:

Earth visible = Earth elevation > 0°

Earth not visible = Earth elevation <= 0°

This initially ignores terrain and Earth's
apparent angular diameter.

### Important

Geometric Earth visibility does not guarantee
a successful communication link.

Actual communication also depends on antenna
orientation, signal strength, spacecraft hardware,
ground-station availability, and other constraints.

### Deliverable

A Python function that calculates geometric
Earth visibility at each timestamp.

Implemented in `backend/app/services/geometric_earth.py`
(`geometric_earth_visibility`, `earth_visibility_response`) and served at
`GET /api/geometric-earth?site_id=..&window=initial|alternative`. It reuses
Task 1's rule implementation unchanged (one `> 0` rule for both bodies), reads
the committed Phase 2 series, keeps each azimuth and elevation, stores a
boolean per timestamp, and flags samples within Earth's 0.95 deg apparent
radius as grazing without changing the rule. The response carries the task's
warning that geometric visibility is not a working communication link. Tested
at all three sites in both mission windows (11 tests in
`backend/tests/test_geometric_earth.py`).

---

## Task 3: Calculate Terrain Horizon Obstructions

- [x] Load lunar elevation data obtained in Phase 2.
- [x] Identify each landing site's surface elevation.
- [x] Define an observer height above the lunar surface.
- [x] Extract surrounding terrain elevations.
- [x] Account for lunar surface curvature.
- [x] Calculate terrain obstruction angles at
      different azimuth directions.
- [x] Generate a terrain horizon profile for
      at least one landing site.
- [x] Compare Sun elevation against the terrain horizon.
- [x] Compare Earth elevation against the terrain horizon.
- [x] Store terrain-adjusted visibility results.
- [x] Document terrain resolution and uncertainties.
- [x] Mark sites without terrain profiles as
      geometric-only rather than terrain-verified.

### Calculation

For each azimuth:

Terrain horizon angle =
Maximum angular elevation of obstructing terrain
in that direction.

For simplified center-point visibility:

Sun visible if:
Sun elevation > terrain horizon angle

Earth visible if:
Earth elevation > terrain horizon angle

### Example

| Object | Elevation | Terrain Horizon | Visible |
|--------|-----------|-----------------|---------|
| Sun | +3° | +5° | No |
| Sun | +7° | +5° | Yes |
| Earth | +4° | +2° | Yes |
| Earth | +1° | +6° | No |

Example values are illustrative.

### Implemented

`backend/app/services/terrain_horizon.py` exposes `GET /api/terrain-horizon`:
the committed 360-point two-tier LOLA skyline per site (5 m/pixel near,
80 m/pixel to 150 km, 1 degree step, 2 m observer, curvature applied at build
time), the site's surface elevation and observer height, per-body samples above
and below the skyline with clearances, and how many flat-horizon "visible"
samples the terrain blocks. The adjusted visibility, intervals and metrics are
delegated unchanged to `services/phase3.py::visibility_response`, so there is
one visibility rule in the project. Points without a committed mask (custom
coordinates, or a site with no mask) return a flat 0 degree horizon marked
`basis: "geometric"` / `geometric_only: true` — never a fabricated profile.
Resolution, curvature, the 150 km range and the 1 degree sampling are documented
in [docs/TERRAIN_HORIZON.md](docs/TERRAIN_HORIZON.md); tests are in
`backend/tests/test_terrain_horizon.py`.

### Important Considerations

- Use consistent lunar coordinate and height systems.
- Account for the Moon's curvature.
- Use the observer's actual position and height.
- Avoid treating the terrain as a flat plane.
- Specify the distance covered by the terrain dataset.
- A limited terrain dataset can miss distant obstructions.

For more advanced accuracy, account for the apparent
angular sizes of the Sun and Earth when calculating
partial and complete obstruction.

### Deliverable

A terrain horizon calculation module that produces
terrain-aware Sun and Earth visibility for at least
one verified landing site.

### Resources

NASA LROC QuickMap:
https://quickmap.lroc.asu.edu/

NASA Moon Trek:
https://trek.nasa.gov/moon/

NASA LOLA South-Pole Topography:
https://pgda.gsfc.nasa.gov/products/78

---

## Task 4: Calculate Sunlight Availability

- [ ] Load the Sun visibility timeline.
- [ ] Identify continuous periods of sunlight.
- [ ] Identify continuous periods without sunlight.
- [ ] Calculate total sunlight duration.
- [ ] Calculate total darkness duration.
- [ ] Calculate sunlight availability percentage.
- [ ] Find the longest continuous darkness period.
- [ ] Estimate the next sunrise or sunset transition.
- [ ] Refine observation intervals near transitions.
- [ ] Save calculated sunlight statistics.

### Calculations

Sunlight availability percentage:

Sunlight Availability (%) =
(Total Sunlit Duration / Total Mission Duration) * 100

Darkness duration:

Darkness Duration =
Total Mission Duration - Total Sunlit Duration

### Example

Mission duration: 168 hours

Sunlight duration: 120 hours

Darkness duration: 48 hours

Sunlight availability:

120 / 168 * 100 = 71.43%

These are hypothetical values.

### Important

Use time-weighted intervals rather than counting
samples if observation intervals are unequal.

A full seven-day mission may not contain a complete
sunrise/sunset cycle.

If a visibility interval extends beyond the selected
analysis period, label the result as window-limited.

### Deliverable

A function that calculates sunlight availability,
sunlight windows, darkness windows, and the longest
continuous period without direct sunlight.

---

## Task 5: Calculate Earth Communication Windows

- [ ] Load the Earth visibility timeline.
- [ ] Identify continuous periods of Earth visibility.
- [ ] Identify periods when Earth is obstructed.
- [ ] Calculate total Earth visibility duration.
- [ ] Calculate Earth visibility percentage.
- [ ] Identify the longest Earth visibility window.
- [ ] Identify the longest communication blackout.
- [ ] Estimate the next Earthrise or Earthset.
- [ ] Refine observation intervals near transitions.
- [ ] Save communication window statistics.

### Calculations

Earth visibility percentage:

Earth Visibility (%) =
(Total Earth-Visible Duration / Mission Duration) * 100

Maximum geometric communication blackout:

Longest continuous interval when Earth
is not visible from the landing site.

### Example

Mission duration: 168 hours

Earth visible: 105 hours

Earth obstructed: 63 hours

Earth visibility:

105 / 168 * 100 = 62.5%

### Important

The application should describe these as
direct-to-Earth line-of-sight opportunities.

They are not guarantees of a working radio link.

Earth's partial visibility near the horizon and
antenna clearance requirements may change actual
communication availability.

### Deliverable

A function that calculates Earth visibility windows,
visibility percentage, and maximum line-of-sight
blackout duration.

---

## Task 6: Calculate Simultaneous Sun and Earth Visibility

- [ ] Combine Sun and Earth visibility results.
- [ ] Ensure timestamps and site identifiers match.
- [ ] Identify periods when both objects are visible.
- [ ] Identify periods when only the Sun is visible.
- [ ] Identify periods when only Earth is visible.
- [ ] Identify periods when neither is visible.
- [ ] Calculate total simultaneous visibility time.
- [ ] Calculate simultaneous visibility percentage.
- [ ] Store the resulting operational windows.

### Calculation

Simultaneous Visibility =
Sun Visible AND Earth Visible

### Example

| Time | Sun Visible | Earth Visible | Both |
|------|-------------|---------------|------|
| 00:00 | Yes | Yes | Yes |
| 01:00 | Yes | No | No |
| 02:00 | No | Yes | No |
| 03:00 | No | No | No |

### Why This Matters

Some mission operations may benefit from having
sunlight and direct communication simultaneously.

However, spacecraft with batteries and onboard data
storage may operate without both being available
at the same time.

### Deliverable

A function that identifies simultaneous sunlight
and Earth communication opportunities.

---

## Task 7: Compare Landing Sites

- [ ] Load calculated results for all three sites.
- [ ] Compare sites over the same mission date range.
- [ ] Compare sunlight availability percentages.
- [ ] Compare Earth visibility percentages.
- [ ] Compare longest darkness periods.
- [ ] Compare longest communication blackouts.
- [ ] Compare simultaneous visibility percentages.
- [ ] Identify advantages and disadvantages
      of each landing site.
- [ ] Generate structured comparison results.

### Example Comparison

| Metric | Site A | Site B | Site C |
|--------|--------|--------|--------|
| Sunlight | 75% | 62% | 84% |
| Earth Visibility | 55% | 88% | 70% |
| Max Darkness | 10 h | 16 h | 7 h |
| Max Earth Blackout | 18 h | 5 h | 11 h |

All numbers are hypothetical.

### Deliverable

A function that compares multiple lunar sites
and returns measurable mission-planning trade-offs.

---

## Task 8: Evaluate Mission Requirements

- [ ] Load mission requirements defined in Phase 1.
- [ ] Compare calculated results against each requirement.
- [ ] Determine whether each site meets the minimum
      sunlight availability threshold.
- [ ] Determine whether each site meets the minimum
      Earth visibility threshold.
- [ ] Determine whether each site's longest communication
      blackout is within the permitted limit.
- [ ] Identify which requirements each site fails.
- [ ] Generate explanations for the results.
- [ ] Avoid declaring a site fully mission-safe
      based only on these simplified conditions.

### Proposed Requirements

| Requirement | Target |
|-------------|--------|
| Minimum Sunlight | 60% |
| Minimum Earth Visibility | 50% |
| Maximum Earth Blackout | 12 hours |

These are hypothetical demo thresholds.

### Example Output

Site A:
- Sunlight requirement: PASS
- Earth visibility requirement: PASS
- Maximum blackout requirement: FAIL

Overall:
Does not meet all selected demonstration constraints.

### Deliverable

A mission constraint evaluator that checks each
landing site against the defined requirements
and explains why it passes or fails.

---

## Task 9: Compare Original and Delayed Landing Dates

- [ ] Load the initial mission period.
- [ ] Load the delayed mission period.
- [ ] Calculate visibility metrics for both periods.
- [ ] Compare sunlight availability changes.
- [ ] Compare Earth visibility changes.
- [ ] Compare maximum darkness duration changes.
- [ ] Compare communication blackout changes.
- [ ] Identify sites that become less favorable.
- [ ] Identify sites that become more favorable.
- [ ] Generate a before-and-after comparison.

### Mission Scenarios

Original mission:
December 1–8, 2026

Delayed mission:
December 11–18, 2026

Each interval should represent exactly 168 hours,
using explicit UTC start and end timestamps.

### Example Question

If the mission is delayed by ten days, which
landing site best satisfies the same sunlight
and communication requirements?

### Deliverable

A scenario comparison function that highlights
the operational consequences of changing
a mission's landing date.

---

## Task 10: Validate Scientific Calculations

- [ ] Write unit tests for geometric Sun visibility.
- [ ] Write unit tests for geometric Earth visibility.
- [ ] Test terrain obstruction calculations.
- [ ] Test zero-degree and near-horizon conditions.
- [ ] Test visibility interval detection.
- [ ] Test maximum blackout calculations.
- [ ] Test simultaneous visibility calculations.
- [ ] Test site comparison calculations.
- [ ] Test mission requirement evaluation.
- [ ] Compare selected results with Horizons output.
- [ ] Check calculations against NASA illumination
      reference data where comparable.
- [ ] Verify timestamp ordering and units.
- [ ] Check behavior when data is missing.
- [ ] Ensure incomplete observations are not
      incorrectly reported as continuous coverage.

### Example Test Cases

Test 1:
Sun elevation = +5°
Geometric Sun visibility = True

Test 2:
Sun elevation = -3°
Geometric Sun visibility = False

Test 3:
Sun elevation = +4°
Terrain horizon = +8°
Terrain-adjusted Sun visibility = False

Test 4:
Sun visible = True
Earth visible = False
Simultaneous visibility = False

Test 5:
Longest Earth visibility gap = 15 hours
Allowed maximum blackout = 12 hours
Communication requirement = FAIL

### Deliverable

A tested scientific calculation engine with
documented assumptions, known limitations,
and reproducible results.

---

## Task 11: Prepare Results for Phase 4

- [x] Standardize calculated results into JSON.
- [x] Include the site identifier and coordinates.
- [x] Include mission start and end timestamps.
- [x] Include sunlight and Earth visibility metrics.
- [x] Include continuous visibility windows.
- [x] Include simultaneous visibility statistics.
- [x] Include mission requirement results.
- [x] Include data source and model quality labels.
- [x] Provide structured results for frontend charts.
- [x] Test the calculation output for at least one site.
- [x] Confirm that frontend developers understand
      all output fields and units.

### Example Output Structure

```json
{
  "site_id": "A",
  "mission_duration_hours": 168,
  "sunlight": {
    "availability_percent": null,
    "longest_darkness_hours": null,
    "windows": []
  },
  "earth": {
    "visibility_percent": null,
    "longest_blackout_hours": null,
    "windows": []
  },
  "simultaneous_visibility": {
    "availability_percent": null,
    "windows": []
  },
  "model": {
    "visibility_type": "geometric",
    "status": "not_calculated"
  }
}
```

Replace null values with actual calculations.

The example is a schema template, not a
completed scientific result.

### Implemented

`backend/app/services/mission_report.py` assembles the envelope behind
`GET /api/mission-report?site_id=<id>&window=initial|alternative`, schema
`lunanav.mission_report.v1`. It reads, and never recalculates, the terrain basis
and coverage from `terrain_horizon.py`, the adjusted visibility, intervals and
metrics from `phase3.py`, and the Phase 1 checks and thresholds from
`requirements.py`. `mission_report_json()` sorts keys and includes no wall
clock, so a re-run reproduces the document byte for byte (asserted in
`backend/tests/test_mission_report.py`). Every field, its unit and its meaning
are listed in [docs/MISSION_REPORT.md](docs/MISSION_REPORT.md).

### Suggested Backend Structure

```text
backend/
├── data/
│   ├── sites.json
│   ├── ephemeris/
│   └── terrain/
│
├── services/
│   ├── horizons.py
│   ├── solar_visibility.py
│   ├── earth_visibility.py
│   ├── terrain_horizon.py
│   ├── visibility_windows.py
│   ├── site_comparison.py
│   └── mission_constraints.py
│
├── tests/
│   ├── test_solar_visibility.py
│   ├── test_earth_visibility.py
│   ├── test_terrain_horizon.py
│   ├── test_visibility_windows.py
│   └── test_site_comparison.py
│
└── outputs/
    └── comparison_results.json
```

### Deliverable

A validated backend calculation engine that
outputs structured mission analysis results
for the frontend.

---

## Phase 3 Completion Checklist

- [ ] Geometric Sun visibility implemented.
- [ ] Geometric Earth visibility implemented.
- [ ] Sunlight and darkness windows calculated.
- [ ] Earth visibility and blackout windows calculated.
- [ ] Simultaneous visibility calculated.
- [ ] Sunlight availability percentages calculated.
- [ ] Earth visibility percentages calculated.
- [ ] Longest darkness and blackout periods calculated.
- [ ] Three landing sites compared.
- [ ] Mission constraints evaluated.
- [ ] Original and delayed mission dates compared.
- [ ] Scientific calculations tested.
- [ ] Structured JSON output generated.
- [ ] Results prepared for frontend integration.

### Advanced Completion Criteria

- [ ] Terrain horizon profile calculated.
- [ ] Terrain-adjusted visibility implemented.
- [ ] Terrain calculation validated.
- [ ] Uncertainty and coverage limitations documented.
- [ ] Geometric and terrain-adjusted results distinguished.

---

## Phase 4 — Next Steps

Build the interactive Lunar Landing Site Navigator
website using the scientific results from Phase 3.

The website should help users understand
why different locations and dates produce
different mission conditions.

Phase 4 is tracked as concrete, independently
claimable tasks. A task is done when it has an
endpoint or component, tests or a build check,
and a doc line; claim it in
[docs/PHASE3_COORDINATION.md](docs/PHASE3_COORDINATION.md)
before you start.

## Task 1: Horizon profile view

- [x] Draw the site's terrain horizon profile
      from `GET /api/terrain-horizon` in the
      Mission Planner.
- [x] Overlay the Sun and Earth elevation
      tracks, with their azimuths.
- [x] Label the profile `terrain` or
      `geometric only` from the payload, never
      inferred from the site name.
- [x] Show the observer height, the 5 m/80 m
      tiers, the 150 km range and the maximum
      obstruction with its azimuth.
- [x] Explain in one sentence why a skyline
      above the Sun's maximum elevation means
      no sunlight in that window.

## Task 2: Feasibility matrix

- [ ] One row per candidate, both mission
      windows against every Phase 1
      requirement.
- [ ] Each cell is met, not met or unknown,
      with the measured value and threshold.
- [ ] Link each cell to the metric that
      produced it; no hand-entered values.
- [ ] State that `unknown` is not a pass.

## Task 3: Phase 3 result envelope

- [x] One JSON document per site and window
      combining the series, adjusted
      visibility, intervals, metrics,
      requirements and provenance.
- [x] Deterministic ordering and rounding,
      one schema string, a version field.
- [x] Documented in `docs/` and covered by a
      test that a re-run reproduces it byte
      for byte.

## Task 4: Landing-delay comparison

- [ ] Surface the reschedule comparison as a
      before/after panel, not only an API.
- [ ] Show both windows, not only the initial
      one.
- [ ] Make the change in the metrics explicit
      when the landing date moves.

## Task 5: States and accessibility

- [ ] Empty, loading, error and
      geometric-only states for every new
      panel.
- [ ] Keyboard reachable controls, labelled
      charts, sufficient contrast.
- [ ] No chart is the only copy of a number.

## Task 6: 3D terrain (optional, feature-flagged)

- [ ] Render the LOLA DEM around a candidate
      with the skyline and Sun/Earth directions.
- [ ] Off by default; the 2D profile stays the
      source of truth.
- [ ] Document the frame, datum and
      exaggeration factor.

---

## Official NASA Space Apps Resources

### NASA JPL Horizons
https://ssd.jpl.nasa.gov/horizons/

Used to obtain Sun and Earth positions for
selected lunar observer locations.

### NASA LROC QuickMap
https://quickmap.lroc.asu.edu/

Used for site coordinates, lunar imagery,
and terrain exploration.

### NASA Moon Trek
https://trek.nasa.gov/moon/

Used to examine 3D lunar terrain and
understand geographic features.

### NASA LOLA South-Pole Topography
https://pgda.gsfc.nasa.gov/products/78

Used for terrain elevation data and
terrain horizon calculations.

### Canadian Space Agency — Moon Exploration
https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/

Used for scientific background and
lunar exploration context.

---

## Expected Final Outcome

By completing Phase 3, our team should have:

1. A functional Sun visibility calculation engine.
2. A functional Earth visibility calculation engine.
3. Calculated sunlight and communication windows.
4. Maximum darkness and blackout measurements.
5. Simultaneous Sun/Earth visibility analysis.
6. Landing-site comparison functionality.
7. Mission requirement evaluation.
8. Mission-delay comparison functionality.
9. Tested and documented scientific calculations.
10. Structured data ready for the website.

Phase 3 is complete when our backend can
take verified lunar coordinates, a date range,
and mission requirements, then return
scientifically grounded visibility metrics
and explain the trade-offs between sites.

Terrain-aware analysis is an advanced milestone.
If it is incomplete, the application must clearly
label its results as geometric-only estimates.
