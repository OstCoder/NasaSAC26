
# Phase 5 — Mission Planning Intelligence & Decision Support

## Objective

Develop the decision-support features for our NASA
Space Apps Challenge 2026 Lunar Landing Site Navigator.

Build upon the scientific calculations from Phase 3
and the interactive website developed in Phase 4.

Enable users to define spacecraft requirements,
evaluate landing-site suitability, compare mission
scenarios, and understand the trade-offs between
sunlight availability, Earth communication, and
scientific exploration opportunities.

By the end of Phase 5, our website should help
users understand not only what conditions exist
at a lunar site, but what those conditions mean
for a hypothetical mission.

---

## Task 1: Develop Adjustable Mission Requirements

- [ ] Create a mission requirements configuration.
- [ ] Allow users to define minimum sunlight availability.
- [ ] Allow users to define minimum Earth visibility.
- [ ] Allow users to define maximum communication blackout.
- [ ] Allow users to define maximum darkness duration.
- [ ] Allow users to choose mission duration.
- [ ] Allow users to set spacecraft power requirements.
- [ ] Validate all user-provided values.
- [ ] Store requirements in a consistent format.
- [ ] Connect the requirements to the backend.
- [ ] Update mission evaluations when requirements change.

### Default Mission Requirements

| Requirement | Example Value |
|-------------|---------------|
| Mission Duration | 168 hours |
| Minimum Sunlight | 60% |
| Minimum Earth Visibility | 50% |
| Maximum Communication Blackout | 12 hours |
| Maximum Darkness | 16 hours |
| Average Spacecraft Power Demand | 40 W |

These are hypothetical demonstration requirements,
not official NASA mission specifications.

### Example Configuration

```json
{
  "mission_name": "Polar Ice Scout",
  "duration_hours": 168,
  "requirements": {
    "min_sunlight_percent": 60,
    "min_earth_visibility_percent": 50,
    "max_communication_blackout_hours": 12,
    "max_darkness_hours": 16,
    "average_power_demand_watts": 40
  }
}
```

### Deliverable

A configurable mission requirements system that
allows users to evaluate lunar landing sites
against different operational constraints.

---

## Task 2: Build the Mission Feasibility Evaluator

- [ ] Load calculated mission metrics from Phase 3.
- [ ] Load the user's selected mission requirements.
- [ ] Compare each metric against its requirement.
- [ ] Evaluate sunlight availability.
- [ ] Evaluate Earth visibility.
- [ ] Evaluate maximum darkness duration.
- [ ] Evaluate maximum communication blackout.
- [ ] Evaluate energy requirements when modeled.
- [ ] Identify failed requirements.
- [ ] Identify unavailable or incomplete measurements.
- [ ] Generate a feasibility explanation.
- [ ] Return structured results to the frontend.

### Evaluation Logic

Each requirement should have one of three statuses:

- PASS — The modeled condition meets the requirement.
- FAIL — The modeled condition violates the requirement.
- UNKNOWN — Data is insufficient to evaluate the requirement.

Overall mission constraint status:

PASS:
All required constraints pass.

FAIL:
At least one required constraint fails.

UNKNOWN:
No constraint fails, but one or more required
constraints cannot be evaluated.

### Example Evaluation

Site A:

| Requirement | Result |
|-------------|--------|
| Minimum Sunlight | PASS |
| Minimum Earth Visibility | PASS |
| Maximum Darkness | PASS |
| Maximum Communication Blackout | FAIL |

Overall Result:
FAIL

Reason:
Site A exceeds the maximum allowed direct-to-Earth
visibility blackout duration.

### Important

Passing the selected constraints does not mean a
landing site is safe, approved, or flight-ready.

The evaluator does not automatically account for
landing hazards, radiation, all thermal constraints,
communications link budgets, or other mission risks.

### Deliverable

A constraint-based feasibility engine that
evaluates landing sites and clearly explains
which requirements pass, fail, or remain unknown.

---

## Task 3: Develop Solar Power Estimation

- [ ] Read Sun elevation and azimuth data.
- [ ] Read terrain-adjusted Sun visibility when available.
- [ ] Define the solar panel area.
- [ ] Define the solar panel efficiency.
- [ ] Define the solar panel orientation.
- [ ] Set a documented solar irradiance assumption.
- [ ] Calculate the angle of sunlight incidence.
- [ ] Estimate instantaneous solar power generation.
- [ ] Set direct solar generation to zero when
      the Sun is fully obstructed.
- [ ] Calculate estimated energy generation over time.
- [ ] Account for varying observation time intervals.
- [ ] Document model assumptions and limitations.

### Solar Power Model

A simplified solar power equation is:

P = S × A × efficiency × max(0, cos(theta))

Where:

P = Estimated solar power output (W)
S = Solar irradiance (W/m²)
A = Solar panel area (m²)
theta = Angle between sunlight direction
        and the panel's surface normal

For a horizontal panel:

P = S × A × efficiency × max(0, sin(elevation))

For other panel orientations, calculate the
angle of incidence using both solar elevation
and azimuth.

### Example Spacecraft Assumptions

| Parameter | Example |
|-----------|---------|
| Solar Panel Area | 2 m² |
| Panel Efficiency | 25% |
| Solar Irradiance | 1361 W/m² |
| Panel Orientation | Horizontal |
| Power Demand | 40 W |

These are hypothetical demonstration values.

### Important

Actual spacecraft power depends on solar
array orientation, temperature, degradation,
electrical losses, and hardware design.

Near the lunar poles, fixed vertical or
Sun-tracking solar panels may perform
differently from horizontal panels.

Do not use Sun visibility percentage alone
as a substitute for energy calculations.

### Deliverable

A simplified, documented solar power estimation
module that calculates estimated electrical
generation over the mission timeline.

---

## Task 4: Implement Battery Survival Simulation

- [ ] Define battery capacity in watt-hours.
- [ ] Define initial battery charge.
- [ ] Define spacecraft power consumption.
- [ ] Use estimated solar power from Task 3.
- [ ] Simulate battery charge over time.
- [ ] Prevent battery charge from exceeding capacity.
- [ ] Identify periods when generation is below demand.
- [ ] Identify periods when battery reserves decrease.
- [ ] Identify minimum battery charge.
- [ ] Calculate energy shortfall when applicable.
- [ ] Identify potential power-loss events.
- [ ] Display battery status throughout the mission.

### Simplified Battery Model

Battery energy at the next time step:

E_next = E_current + (P_solar - P_load) × delta_t

Where:

E_current = Current battery energy (Wh)
P_solar = Generated electrical power (W)
P_load = Spacecraft power demand (W)
delta_t = Time interval in hours

For the simulation:

- Limit stored energy to battery capacity.
- Account for charge and discharge efficiencies
  if supported.
- Stop treating the spacecraft as operational
  once its usable energy has been exhausted.
- Document whether battery reserve limits
  and depth-of-discharge are included.

### Example Scenario

Battery capacity: 2000 Wh

Initial charge: 2000 Wh

Spacecraft power demand: 40 W

No solar generation for 20 hours.

Energy consumed:

40 W × 20 h = 800 Wh

Remaining energy, ignoring losses:

2000 Wh - 800 Wh = 1200 Wh

### Important

The model is an educational engineering
approximation, not a flight-qualified
spacecraft power simulation.

### Deliverable

A battery simulation that estimates whether
the hypothetical spacecraft can sustain
its power demand throughout a selected mission.

---

## Task 5: Create a Mission Energy Timeline

- [ ] Display estimated solar power generation.
- [ ] Display spacecraft power consumption.
- [ ] Display estimated battery energy over time.
- [ ] Highlight periods without direct sunlight.
- [ ] Highlight periods of battery discharge.
- [ ] Highlight periods of battery charging.
- [ ] Show minimum estimated battery energy.
- [ ] Identify potential power shortages.
- [ ] Synchronize the timeline with mission timestamps.
- [ ] Add tooltips explaining energy calculations.
- [ ] Display the assumed panel and battery parameters.

### Suggested Charts

Chart 1:
Solar Power Generation vs. Spacecraft Demand

Chart 2:
Battery Energy Remaining Over Time

Chart 3:
Sun Visibility vs. Battery Status

### Important

The energy timeline should use the same UTC
timestamps as the astronomical calculations.

Avoid displaying an energy curve based on
fabricated sunlight observations.

### Deliverable

Interactive power and battery visualizations
that explain how changing solar conditions
affect hypothetical spacecraft operations.

---

## Task 6: Develop Mission Delay Analysis

- [ ] Load the original landing-date scenario.
- [ ] Load the delayed landing-date scenario.
- [ ] Run the same mission requirements for both.
- [ ] Compare sunlight availability.
- [ ] Compare Earth visibility.
- [ ] Compare maximum darkness duration.
- [ ] Compare maximum communication blackout.
- [ ] Compare estimated energy generation.
- [ ] Compare minimum battery reserves.
- [ ] Identify new failed requirements.
- [ ] Identify requirements that improve.
- [ ] Display changes in the frontend.
- [ ] Generate a clear explanation of the differences.

### Example Scenario

Original Landing:
December 1, 2026

Delayed Landing:
December 11, 2026

Mission Duration:
7 Earth days

### Example Questions

- Does the delayed landing receive less sunlight?
- Does the delay increase communication blackouts?
- Can the battery support the new darkness intervals?
- Does the original site still meet the mission criteria?
- Would an alternative site be more suitable?

### Deliverable

A mission-delay evaluator that compares
the original and delayed mission scenarios
using consistent scientific calculations.

---

## Task 7: Build Landing-Site Ranking and Recommendations

- [ ] Load mission results for all selected sites.
- [ ] Evaluate each site's mission constraints.
- [ ] Separate sites that pass, fail, or are unknown.
- [ ] Allow users to prioritize sunlight or communication.
- [ ] Define a transparent ranking method.
- [ ] Normalize metrics before combining them.
- [ ] Apply penalties for undesirable conditions.
- [ ] Avoid ranking missing data as favorable.
- [ ] Show the measurements behind each ranking.
- [ ] Explain why sites are ranked differently.
- [ ] Update rankings when requirements change.

### Suggested Ranking Approach

First:
Filter sites using required mission constraints.

Second:
Rank sites that pass the constraints using
the selected mission priorities.

Possible ranking factors:

- Sunlight availability
- Earth visibility
- Longest darkness duration
- Longest communication blackout
- Estimated battery energy margin
- Simultaneous visibility

### Example Weighted Score

Score =
0.30 × Sunlight Score +
0.30 × Earth Visibility Score +
0.20 × Battery Margin Score +
0.20 × Communication Reliability Score

Each component must be normalized to the
same scale before applying weights.

These weights are hypothetical and should
be adjustable or clearly documented.

### Important

Do not invent a universal NASA-approved
landing-site suitability score.

Different missions have different priorities.

Sites that fail critical requirements should
not be recommended simply because their
weighted score is high.

### Deliverable

A transparent landing-site ranking engine
that recommends alternatives based on
user-defined mission requirements.

---

## Task 8: Generate Explainable Mission Recommendations

- [ ] Identify the strongest advantages of each site.
- [ ] Identify the most significant operational risks.
- [ ] Explain which constraints caused a failure.
- [ ] Explain changes caused by landing-date delays.
- [ ] Generate a short summary for each site.
- [ ] Generate an overall comparison summary.
- [ ] Connect explanations to calculated measurements.
- [ ] Include uncertainty and model limitations.
- [ ] Avoid unsupported scientific conclusions.
- [ ] Display explanations in understandable language.

### Example Recommendation

Site B is preferable under the selected
demonstration requirements because:

- It satisfies the minimum sunlight threshold.
- It offers more Earth visibility than Site A.
- Its longest communication blackout is shorter.
- Its modeled battery reserves remain above
  the required minimum.

Site A may still be useful for missions that
prioritize sunlight over frequent communication.

### Important

Use deterministic, measurement-based
explanations as the default.

AI-generated natural-language explanations
are optional and should only summarize
verified calculations.

Never allow an AI model to invent site
measurements or mission results.

### Deliverable

An explanation system that helps non-specialists
understand the trade-offs behind each result.

---

## Task 9: Add Scientific Exploration Preferences

- [ ] Define optional scientific priorities.
- [ ] Allow users to prioritize proximity to PSRs.
- [ ] Identify potential scientific exploration regions.
- [ ] Obtain verified PSR location or boundary data.
- [ ] Calculate distance to nearby PSRs when supported.
- [ ] Display PSRs on the lunar map when data is available.
- [ ] Compare scientific proximity with operational conditions.
- [ ] Explain conflicts between solar power,
      Earth communication, and scientific objectives.
- [ ] Clearly distinguish PSRs from confirmed water-ice deposits.
- [ ] Avoid treating straight-line distance as
      proof of rover accessibility.

### Scientific Mission Example

Mission Objective:
Investigate potential water ice near the
Moon's south pole.

Operational Preferences:

- Sufficient sunlight for solar power
- Acceptable Earth communication windows
- Reasonable proximity to a PSR

### Important

Permanently shadowed regions may preserve
water ice, but not every PSR contains
confirmed accessible water ice.

A solar-powered lander may operate on
better-illuminated terrain while a
specially equipped rover or instrument
investigates nearby shadowed areas.

Distance to a PSR alone does not guarantee
a safe or practical route.

### Deliverable

An optional science-focused comparison mode
that helps users examine operational feasibility
alongside proximity to scientifically
interesting lunar regions.

---

## Task 10: Build the Mission Decision Dashboard

- [ ] Create a dedicated mission evaluation panel.
- [ ] Display selected mission requirements.
- [ ] Show PASS, FAIL, and UNKNOWN statuses.
- [ ] Display sunlight and communication metrics.
- [ ] Display estimated power and battery status.
- [ ] Display recommended landing sites.
- [ ] Show alternative dates when supported.
- [ ] Provide explanations for recommendations.
- [ ] Highlight critical mission risks.
- [ ] Link each result to the relevant data.
- [ ] Allow users to adjust requirements.
- [ ] Refresh recommendations when inputs change.

### Suggested Dashboard Layout

Section 1:
Mission Requirements

Section 2:
Landing-Site Feasibility

Section 3:
Solar Power and Battery Analysis

Section 4:
Communication Availability

Section 5:
Site Rankings and Recommendations

Section 6:
Mission Delay Comparison

Section 7:
Scientific Exploration Preferences

### Deliverable

An interactive mission decision dashboard
that combines the scientific analysis
with practical mission requirements.

---

## Task 11: Integrate Decision Support With the Backend

- [ ] Connect mission requirement controls to the backend.
- [ ] Integrate the feasibility evaluation engine.
- [ ] Integrate solar energy calculations.
- [ ] Integrate battery simulations.
- [ ] Integrate mission-delay comparisons.
- [ ] Integrate site ranking calculations.
- [ ] Integrate explanation generation.
- [ ] Integrate scientific preferences when supported.
- [ ] Return consistent structured JSON results.
- [ ] Handle invalid mission configurations.
- [ ] Handle unavailable astronomical data.
- [ ] Prevent stale analysis results from being displayed.

### Suggested API Endpoints

POST /api/mission/evaluate

Evaluates a selected site against
the user's mission requirements.

POST /api/mission/power

Calculates estimated power generation
and battery behavior.

POST /api/mission/compare

Compares sites and mission dates.

POST /api/mission/recommend

Returns ranked sites and explanations.

These are proposed application endpoints,
not official NASA endpoints.

### Example Response

```json
{
  "site_id": "A",
  "mission": "Polar Ice Scout",
  "status": "not_calculated",
  "constraints": [],
  "power": {
    "min_battery_wh": null,
    "energy_shortfall_wh": null
  },
  "recommendation": {
    "rank": null,
    "reasons": []
  }
}
```

Replace placeholder values with real
calculations from the backend.

### Deliverable

A connected decision-support system
that returns structured mission evaluations
and recommendations to the frontend.

---

## Task 12: Test and Validate Mission Recommendations

- [ ] Test sunlight requirement evaluation.
- [ ] Test Earth visibility requirement evaluation.
- [ ] Test communication blackout limits.
- [ ] Test maximum darkness limits.
- [ ] Test solar power calculations.
- [ ] Test battery charging calculations.
- [ ] Test battery discharging calculations.
- [ ] Test battery capacity limits.
- [ ] Test scenarios with insufficient energy.
- [ ] Test mission-delay comparisons.
- [ ] Test site ranking logic.
- [ ] Test recommendations with missing data.
- [ ] Test conflicting mission priorities.
- [ ] Verify explanations match numerical results.
- [ ] Confirm scientific limitations are displayed.
- [ ] Verify no unsupported NASA endorsement claims.

### Example Test Cases

Test 1:
Sunlight availability = 70%
Minimum requirement = 60%
Expected = PASS

Test 2:
Longest communication blackout = 15 hours
Maximum allowed = 12 hours
Expected = FAIL

Test 3:
Battery capacity = 2000 Wh
Initial energy = 2000 Wh
Power load = 40 W
No solar generation for 20 hours
Expected remaining energy = 1200 Wh
(ignoring losses)

Test 4:
Required metric is unavailable.
Expected status = UNKNOWN

Test 5:
Site A meets all constraints.
Site B fails one critical constraint.
Expected result:
Site A is preferred over Site B
regardless of Site B's weighted score.

### Deliverable

A tested mission evaluation engine
with reproducible calculations,
transparent recommendations,
and documented assumptions.

---

## Phase 5 Completion Checklist

- [ ] Adjustable mission requirements implemented.
- [ ] Mission feasibility evaluator functional.
- [ ] PASS, FAIL, and UNKNOWN results supported.
- [ ] Mission-delay analysis functional.
- [ ] Multiple landing sites evaluated.
- [ ] Transparent site comparison implemented.
- [ ] Site ranking implemented.
- [ ] Recommendation explanations generated.
- [ ] Scientific assumptions documented.
- [ ] Mission decision dashboard connected.
- [ ] Backend integrations tested.
- [ ] End-to-end mission evaluation validated.

### Advanced Completion Criteria

- [ ] Solar power estimation implemented.
- [ ] Battery survival simulation implemented.
- [ ] Interactive battery energy timeline created.
- [ ] Adjustable solar panel orientation supported.
- [ ] Power model assumptions documented.
- [ ] PSR proximity analysis implemented.
- [ ] Scientific exploration mode functional.
- [ ] Terrain-aware results incorporated into rankings.
- [ ] Uncertainty or sensitivity analysis included.

---

## Phase 6 — Next Steps

Improve the application's scientific exploration
capabilities and presentation quality.

Planned features:

1. Detailed permanently shadowed region mapping.
2. Water-ice exploration context and scientific layers.
3. Advanced 3D lunar terrain visualization.
4. Improved temporal animations.
5. Educational explanations.
6. Scientific model validation.
7. Final website optimization.
8. Hackathon demonstration and documentation.

Phase 6 will focus on making the project more
scientifically informative, visually compelling,
and ready for public demonstration.

---

## Official NASA Space Apps Resources

### NASA JPL Horizons
https://ssd.jpl.nasa.gov/horizons/

Provides astronomical position data used
for Sun and Earth visibility calculations.

### NASA LROC QuickMap
https://quickmap.lroc.asu.edu/

Provides lunar imagery and geographic
information for landing-site investigation.

### NASA Moon Trek
https://trek.nasa.gov/moon/

Provides interactive lunar terrain visualization
and supports understanding of lunar geography.

### NASA LOLA South-Pole Topography
https://pgda.gsfc.nasa.gov/products/78

Provides lunar elevation information used
for terrain and horizon calculations.

### Canadian Space Agency — Moon Exploration
https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/

Provides background information about lunar
missions and exploration technologies.

---

## Expected Final Outcome

By completing Phase 5, our team should have:

1. Configurable mission requirements.
2. A mission feasibility evaluation system.
3. Sunlight and communication constraint checks.
4. Mission-delay comparisons.
5. Landing-site ranking and recommendations.
6. Explainable mission-planning results.
7. Optional solar power and battery simulations.
8. Optional PSR proximity and science analysis.
9. A fully integrated mission decision dashboard.
10. Tested and documented scientific assumptions.

Phase 5 is complete when users can select
lunar landing sites, specify mission requirements,
and receive transparent evaluations explaining
which locations and dates best satisfy
their selected operational constraints.

The website must distinguish between
verified NASA-derived measurements,
simplified engineering estimates,
and hypothetical mission assumptions.
