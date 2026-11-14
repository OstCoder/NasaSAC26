
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

- [x] Load the Sun visibility timeline.
- [x] Identify continuous periods of sunlight.
- [x] Identify continuous periods without sunlight.
- [x] Calculate total sunlight duration.
- [x] Calculate total darkness duration.
- [x] Calculate sunlight availability percentage.
- [x] Find the longest continuous darkness period.
- [x] Estimate the next sunrise or sunset transition.
- [x] Refine observation intervals near transitions.
- [x] Save calculated sunlight statistics.

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

### Implemented

`backend/app/services/intervals.py` + `backend/app/services/metrics.py`, served
by `GET /api/phase3` on the terrain-adjusted basis and by the Phase 1 planner on
the geometric one. Sunlight and darkness come from
`intervals_from_clearance` (visibility edges are interpolated between samples,
so interval timing is finer than the stored step); totals and percentages are
span seconds, i.e. time-weighted rather than sample counts, which stays honest
if observation intervals are ever unequal. `sun_visible_hours`,
`sun_visible_pct`, `sun_blocked` and `longest_sun_blackout_hours` all appear in
`GET /api/phase3`; a longest interval that touches the window edge is flagged
`censored` and shown as "≥", which is the window-limited labelling the task
asks for. Next transitions come from `VisibilityCalculator.snapshot`
(`services/visibility.py`): a 30-minute forward scan within the lookahead,
then bisection refinement of the flip to sub-minute precision, with
`transition_beyond_lookahead` set when the window contains no cycle
(a seven-day polar mission may not). Statistics are served from the committed
series and also captured by the Task 11 mission-report envelope; there is no
second copy of the math to keep in sync. Verified against the committed data:
connecting-ridge/initial is sunlit 100% of the window (blackout 0 h),
shackleton-rim/alternative is dark 100% with the blackout censored at 168 h.
Tests: `backend/tests/test_horizon_intervals.py`,
`backend/tests/test_phase3.py`, `backend/tests/test_api_and_modes.py`.

---

## Task 5: Calculate Earth Communication Windows

- [x] Load the Earth visibility timeline.
- [x] Identify continuous periods of Earth visibility.
- [x] Identify periods when Earth is obstructed.
- [x] Calculate total Earth visibility duration.
- [x] Calculate Earth visibility percentage.
- [x] Identify the longest Earth visibility window.
- [x] Identify the longest communication blackout.
- [x] Estimate the next Earthrise or Earthset.
- [x] Refine observation intervals near transitions.
- [x] Save communication window statistics.

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

### Implemented

The same interval and metric machinery as Task 4, run on the Earth track:
`earth_visible`, `earth_blocked` intervals with interpolated edges,
`earth_visible_hours`, `earth_visible_pct` and `longest_earth_blackout_hours`
(with the `censored` flag for window-limited blackouts), all in `GET /api/phase3`
on the terrain-adjusted basis. Earthrise/Earthset come from
`VisibilityCalculator.snapshot` with the same 30-minute scan + bisection
refinement. Every Earth response and note in the project says these are
direct-to-Earth line-of-sight opportunities and not guarantees of a working
radio link — antenna pattern, link budget and ground-station scheduling are out
of scope by design. Earth's apparent disk is carried as a `disk_fraction`
context field near the horizon; it never changes the boolean. Verified against
the committed data: shackleton-rim/alternative is 0% (terrain blocks all 75
flat-horizon-visible samples), connecting-ridge/alternative 20.7%, and
de-gerlache-rim/alternative 59.8% — higher than its 52.1% geometric count
because lunar curvature drops the skyline below 0° on convex ground, which
`test_curvature_lowers_flat_horizon` pins down. Tests: `test_phase3.py`,
`test_horizon_intervals.py`, `test_api_and_modes.py`.

---

## Task 6: Calculate Simultaneous Sun and Earth Visibility

- [x] Combine Sun and Earth visibility results.
- [x] Ensure timestamps and site identifiers match.
- [x] Identify periods when both objects are visible.
- [x] Identify periods when only the Sun is visible.
- [x] Identify periods when only Earth is visible.
- [x] Identify periods when neither is visible.
- [x] Calculate total simultaneous visibility time.
- [x] Calculate simultaneous visibility percentage.
- [x] Store the resulting operational windows.

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

### Implemented

`GET /api/phase3` builds every combination from one pair of interval lists:
`both_visible` = `intersect(sun_visible, earth_visible)` from
`services/intervals.py`, then `not_both`, `sun_blocked`, `earth_blocked` and
`neither_visible` by interval algebra over the same window span — so sun-only
and earth-only periods are the complements of the intersections, not a second
calculation. Sun and Earth share one committed series per site/window
(`services/site_data.load_series`), so timestamps and site identifiers match
by construction. The summary reports `both_visible_hours`,
`both_visible_pct` and `longest_no_simultaneous_hours`; the operational
windows themselves are served in the `intervals` block of the same response
and carried into the Task 11 mission-report envelope. Verified against the
committed data: both_visible_pct is 0% wherever either body is 0%
(shackleton-rim in both windows; every site's initial window for Earth), and
follows the intersection where both bodies have light. Tests:
`test_phase3.py` (`test_summary_matches_the_intervals_it_claims`),
`test_horizon_intervals.py` (`test_algebra`).

---

## Task 7: Compare Landing Sites

- [x] Load calculated results for all three sites.
- [x] Compare sites over the same mission date range.
- [x] Compare sunlight availability percentages.
- [x] Compare Earth visibility percentages.
- [x] Compare longest darkness periods.
- [x] Compare longest communication blackouts.
- [x] Compare simultaneous visibility percentages.
- [x] Identify advantages and disadvantages
      of each landing site.
- [x] Generate structured comparison results.

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

### Implemented

`GET /api/phase3/windows` (`services/phase3.py::all_windows_summary`) loads the
committed results for all three candidates over the same date range and reports,
per site and per window: Sun/Earth/both visible percentages, the interval
summaries, and the skyline's max range — one structured table, same timestamps,
offline. Pairwise trade-offs come from `POST /api/compare`
(`services/comparison.py::ScenarioComparisonService.compare`), which diffs every
metric in the shared registry with delta, percent change, per-metric sentences,
an explicit trade-off list and comparability notes (durations or landing times
that differ are flagged there). Advantages and disadvantages are expressed as
these measured deltas — the service deliberately refuses to rank: trade-off text
is asserted free of "recommend/best site/optimal" in
`test_api_and_modes.py::TestCompare::test_compare_two_sites`, and the windows
summary carries the same note. The Phase 4 feasibility matrix composes the same
numbers per site against the requirements. Tests: `test_phase3.py`,
`test_api_and_modes.py`, `backend/tests/test_feasibility.py`.

---

## Task 8: Evaluate Mission Requirements

- [x] Load mission requirements defined in Phase 1.
- [x] Compare calculated results against each requirement.
- [x] Determine whether each site meets the minimum
      sunlight availability threshold.
- [x] Determine whether each site meets the minimum
      Earth visibility threshold.
- [x] Determine whether each site's longest communication
      blackout is within the permitted limit.
- [x] Identify which requirements each site fails.
- [x] Generate explanations for the results.
- [x] Avoid declaring a site fully mission-safe
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

### Implemented

`services/requirements.py::RequirementService` + `POST /api/requirements`
(`RequirementEvaluation`): thresholds are loaded from
`config/lunanav.config.json -> requirements` (60% Sun, 50% Earth, 12 h blackout
— the Phase 1 demo thresholds), measured with the same metric registry the
planner and comparison use, so a verdict and the on-screen number cannot
disagree. Each check reports value, threshold, comparison, a status of
`met/not_met/unknown` and a plain-language explanation of why; which
requirements a site fails is exactly the list of `not_met` checks. The
simplified-conditions caution is structural, not cosmetic: the verdict is a
three-state `satisfied` field, a censored longest-blackout can only be
`unknown` (the window caps it, so "at most" cannot be confirmed), and the
docstring plus response notes state it is a constraint check, not a
recommendation. `GET /api/feasibility` reuses the same `CHECKS` table and
status rules for every candidate x window in one matrix. Tests:
`test_spec_requirements.py`, `test_api_and_modes.py`,
`test_feasibility.py`.

---

## Task 9: Compare Original and Delayed Landing Dates

- [x] Load the initial mission period.
- [x] Load the delayed mission period.
- [x] Calculate visibility metrics for both periods.
- [x] Compare sunlight availability changes.
- [x] Compare Earth visibility changes.
- [x] Compare maximum darkness duration changes.
- [x] Compare communication blackout changes.
- [x] Identify sites that become less favorable.
- [x] Identify sites that become more favorable.
- [x] Generate a before-and-after comparison.

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

### Implemented

`POST /api/reschedule` (`ScenarioComparisonService.reschedule`) loads both
periods, runs the same visibility computation for the original and proposed
landing UTC at the same duration, and returns the shift in hours, the full
metric delta list, and `headline_changes` ordered by operational impact (Sun
hours, Earth hours, simultaneous hours, then the two longest blackouts) —
which sites or dates become more or less favourable is expressed per metric via
the registry's `availability_direction` and the generated statements, never as
a site ranking. A censored delta on either side is carried as
`either_censored`. The mission's own before/after pair (1-8 Dec vs 11-18 Dec
2026, exactly 168 h each, explicit UTC) is precomputed offline by
`GET /api/phase3/windows` and the feasibility matrix, both reporting both
windows per site. Tests: `test_api_and_modes.py::TestReschedule` (shift hours,
headline order, Original label), `test_identical_scenarios_have_zero_delta`,
`test_different_durations_noted`, `test_spec_requirements.py` (the two
presets), plus `test_phase3.py` for the offline window pairs.

---

## Task 10: Validate Scientific Calculations

- [x] Write unit tests for geometric Sun visibility.
- [x] Write unit tests for geometric Earth visibility.
- [x] Test terrain obstruction calculations.
- [x] Test zero-degree and near-horizon conditions.
- [x] Test visibility interval detection.
- [x] Test maximum blackout calculations.
- [x] Test simultaneous visibility calculations.
- [x] Test site comparison calculations.
- [x] Test mission requirement evaluation.
- [x] Compare selected results with Horizons output.
- [x] Check calculations against NASA illumination
      reference data where comparable.
- [x] Verify timestamp ordering and units.
- [x] Check behavior when data is missing.
- [x] Ensure incomplete observations are not
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

### Implemented

The engine is validated by three layers, all green in CI:

1. **Unit tests for every calculation in this phase** — the Task 10 example
   cases map directly onto existing test files:
   - Geometric Sun: `backend/tests/test_geometric_sun.py` (+5 deg true, -3 deg
     false, 0 and -0.0 not visible, +-1e-9 pin the strict rule).
   - Geometric Earth: `backend/tests/test_geometric_earth.py` (same edge
     cases, Earth's 0.95 deg grazing band, disk-fraction 0.5 at the horizon).
   - Terrain obstruction: `test_horizon_intervals.py` (synthetic wall angle,
     curvature lowering a flat horizon, 360 deg interpolation wrap, invalid
     mask rejection, disk fraction) and `backend/tests/test_terrain_horizon.py`
     (Test 3: Sun at +4 deg under an +8 deg skyline is not visible).
   - Intervals, blackouts, simultaneity: `test_horizon_intervals.py`
     (`test_edges_are_interpolated`, `test_longest_censored_flag`,
     `test_algebra`) and `test_phase3.py`
     (`test_summary_matches_the_intervals_it_claims`) — Test 4 and Test 5
     semantics.
   - Site comparison: `test_api_and_modes.py::TestCompare` (delta arithmetic,
     zero-delta identity, differing durations flagged, anti-ranking wording).
   - Requirement evaluation: `test_spec_requirements.py` and
     `backend/tests/test_feasibility.py` (censored blackouts can only be
     unknown).
2. **Cross-validation against NASA sources** — Phase 2's
   `services/nasa_validation.py` plus the committed report
   `data/reference/nasa_validation.json`: 10 checks, all passing, over 1014
   records for all three sites, including `horizons_reference` (site tracks
   compared against the JPL Horizons observer-table evidence in
   `data/reference/horizons_reference.json`), `units`, `utc_time` (timestamp
   ordering and units), `continuity`, `same_site_different_dates`,
   `different_sites_same_time`, and `assumptions_documented`. The validation is
   adversarial: a tampered value fails the check and a missing reference is a
   failure, not a skip (`test_nasa_validation.py`). NASA illumination maps
   (Mazarico-style PSR products) are polygon masks, not point time series, so
   they are not commensurable with per-sample elevation — recorded as a known
   limitation rather than a forced comparison ("where comparable").
3. **Missing-data and coverage honesty** — unavailable live data returns 503
   (`SCIENTIFIC_DATA_UNAVAILABLE` / `JPL_UNAVAILABLE`), sites without masks get
   a flat horizon labelled `geometric_only` instead of a fabricated skyline,
   matrix cells fail individually without blanking the table, and every
   longest-interval that touches the window edge carries the `censored` flag,
   so incomplete observations are never reported as continuous coverage.

Documented assumptions and limitations live in
[docs/METHODOLOGY.md](docs/METHODOLOGY.md) (sections on geometry, masks,
intervals, and section 9 "Known limitations"),
[docs/TERRAIN_HORIZON.md](docs/TERRAIN_HORIZON.md) and
[docs/MISSION_REPORT.md](docs/MISSION_REPORT.md). Reproducibility: the
mission-report envelope sorts keys and includes no wall-clock time (byte-identical
re-runs, asserted in `backend/tests/test_mission_report.py`), and the
validation report records its generator and evidence versions.

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

- [x] Geometric Sun visibility implemented.
- [x] Geometric Earth visibility implemented.
- [x] Sunlight and darkness windows calculated.
- [x] Earth visibility and blackout windows calculated.
- [x] Simultaneous visibility calculated.
- [x] Sunlight availability percentages calculated.
- [x] Earth visibility percentages calculated.
- [x] Longest darkness and blackout periods calculated.
- [x] Three landing sites compared.
- [x] Mission constraints evaluated.
- [x] Original and delayed mission dates compared.
- [x] Scientific calculations tested.
- [x] Structured JSON output generated.
- [x] Results prepared for frontend integration.

### Advanced Completion Criteria

- [x] Terrain horizon profile calculated.
- [x] Terrain-adjusted visibility implemented.
- [x] Terrain calculation validated.
- [x] Uncertainty and coverage limitations documented.
- [x] Geometric and terrain-adjusted results distinguished.

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
