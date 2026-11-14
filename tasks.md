
# Phase 4 — Interactive Website & Data Visualization

## Objective

Develop the interactive Lunar Landing Site Navigator
website for our NASA Space Apps Challenge 2026 project.

Use the verified scientific calculations from Phase 3
to create an intuitive application that helps users
evaluate lunar south-pole landing locations.

The website should allow users to:

1. Explore and select lunar landing sites.
2. Choose landing dates and mission durations.
3. Visualize Sun and Earth positions.
4. Analyze sunlight and communication windows.
5. Compare multiple landing locations.
6. Evaluate mission constraints.
7. Understand how mission delays affect feasibility.

By the end of Phase 4, users should be able to
interact with a functional lunar mission-planning
dashboard without needing to understand raw
astronomical datasets.

---

## Task 1: Set Up the Frontend Application

- [ ] Initialize the frontend using React and TypeScript.
- [ ] Configure Vite or the team's chosen framework.
- [ ] Install Tailwind CSS for styling.
- [ ] Set up routing if multiple pages are required.
- [ ] Create reusable components.
- [ ] Configure environment variables for the backend URL.
- [ ] Set up API request utilities.
- [ ] Configure loading and error states.
- [ ] Confirm the application runs locally.
- [ ] Test communication with the backend.

### Suggested Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend | React + TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS |
| Charts | Recharts or Plotly |
| 3D Visualization | Three.js (optional) |
| Backend | Python + FastAPI |
| Data Format | JSON |
| Deployment | Vercel + Python backend host |

### Suggested Frontend Structure

```text
frontend/
├── src/
│   ├── components/
│   │   ├── LunarMap.tsx
│   │   ├── SiteSelector.tsx
│   │   ├── DateSelector.tsx
│   │   ├── MissionControls.tsx
│   │   ├── SunEarthSkyView.tsx
│   │   ├── VisibilityTimeline.tsx
│   │   ├── MetricsDashboard.tsx
│   │   ├── SiteComparison.tsx
│   │   ├── MissionStatus.tsx
│   │   └── LoadingState.tsx
│   │
│   ├── pages/
│   │   └── Dashboard.tsx
│   │
│   ├── services/
│   │   └── api.ts
│   │
│   ├── types/
│   │   └── mission.ts
│   │
│   ├── App.tsx
│   └── main.tsx
│
├── package.json
└── README.md
```

### Deliverable

A working React frontend that connects to
the scientific backend and loads mission data.

---

## Task 2: Build the Lunar Landing-Site Map

- [ ] Display an interactive map of the lunar south pole.
- [ ] Use lunar imagery or map tiles from a permitted source.
- [ ] Display the three landing sites from Phase 1.
- [ ] Add markers for each candidate landing site.
- [ ] Allow users to select a site by clicking a marker.
- [ ] Display each site's name and coordinates.
- [ ] Highlight the currently selected location.
- [ ] Support zooming and panning.
- [ ] Display elevation data when available.
- [ ] Provide a curated site list if map interaction fails.
- [ ] Verify that coordinates align with the map projection.

### Initial Landing Sites

- Site A — Shackleton Rim
- Site B — Connecting Ridge
- Site C — de Gerlache Rim

Use the exact coordinates verified in Phase 1.

Do not substitute approximate coordinates
without clearly identifying them.

### Site Information Panel

Display:

- Site name
- Latitude
- Longitude
- Elevation
- Data source
- Terrain analysis availability
- Nearby scientific areas, if verified

### Important

LROC QuickMap and NASA Moon Trek are reference tools.

Do not assume their interactive viewers can be
embedded directly into our website.

Use accessible imagery, supported APIs, or
downloadable datasets according to their terms.

### Deliverable

An interactive lunar south-pole map with
three selectable landing sites.

### Resources

NASA LROC QuickMap:
https://quickmap.lroc.asu.edu/

NASA Moon Trek:
https://trek.nasa.gov/moon/

---

## Task 3: Build Date and Mission Controls

- [ ] Create a landing date and time selector.
- [ ] Display timestamps in UTC.
- [ ] Add mission duration controls.
- [ ] Load the initial mission scenario.
- [ ] Load the delayed mission scenario.
- [ ] Allow users to switch between scenarios.
- [ ] Provide a button to run the analysis.
- [ ] Validate date ranges before sending requests.
- [ ] Display an error for unsupported date ranges.
- [ ] Prevent duplicate API requests while loading.
- [ ] Reset outdated results when parameters change.

### Default Mission Configuration

Mission: Polar Ice Scout

Initial landing date:
December 1, 2026, 00:00 UTC

Alternative landing date:
December 11, 2026, 00:00 UTC

Mission duration:
168 hours (7 Earth days)

### Mission Controls

Users should be able to change:

- Landing site
- Landing date
- Mission duration
- Comparison date
- Mission requirements

### Important

If the backend only supports precomputed dates,
the interface must clearly show those supported
ranges instead of offering unrestricted dates.

### Deliverable

Functional date and mission controls
connected to backend calculations.

---

## Task 4: Create Sun and Earth Position Visualizations

- [ ] Display the Sun's azimuth and elevation.
- [ ] Display Earth's azimuth and elevation.
- [ ] Create a 2D sky-view visualization.
- [ ] Show the geometric horizon.
- [ ] Show the terrain horizon when available.
- [ ] Represent the Sun with a recognizable marker.
- [ ] Represent Earth with a recognizable marker.
- [ ] Update positions based on selected timestamps.
- [ ] Clearly indicate when an object is obstructed.
- [ ] Add tooltips for position measurements.
- [ ] Label the difference between geometric and
      terrain-adjusted visibility.

### Suggested Visualization

A sky-position chart containing:

- Azimuth along the horizontal axis
- Elevation along the vertical axis
- Sun position marker
- Earth position marker
- Geometric horizon reference
- Terrain horizon profile, if available

### Example Data

| Object | Azimuth | Elevation | Status |
|--------|---------|-----------|--------|
| Sun | 120° | +4° | Visible |
| Earth | 245° | -2° | Below Horizon |

These are illustrative values.

### Important

Use actual results from Phase 3.

Do not animate fabricated Sun or Earth trajectories.

If the terrain model is unavailable, clearly label
the visualization as geometric-only.

### Deliverable

An interactive sky visualization showing
Sun and Earth positions relative to the horizon.

---

## Task 5: Build the Visibility Timeline

- [ ] Create a timeline covering the mission duration.
- [ ] Display sunlight availability intervals.
- [ ] Display periods without direct sunlight.
- [ ] Display Earth visibility intervals.
- [ ] Display Earth obstruction intervals.
- [ ] Highlight simultaneous Sun/Earth visibility.
- [ ] Display accurate UTC timestamps.
- [ ] Add hover details for visibility transitions.
- [ ] Add zoom controls for longer mission intervals.
- [ ] Allow users to select a timestamp.
- [ ] Synchronize timeline selection with the sky view.
- [ ] Handle incomplete or missing data clearly.

### Timeline Layout

Display three separate rows:

1. Sunlight availability
2. Earth visibility
3. Simultaneous visibility

Suggested visual categories:

- Yellow — Sun visible
- Dark gray — Sun obstructed
- Blue — Earth visible
- Red/orange — Communication line of sight unavailable
- Green — Both Sun and Earth visible

Include text labels so results are not
communicated through color alone.

### Interaction

When a user selects a timestamp:

- Update the Sun's sky position.
- Update Earth's sky position.
- Display their elevation and azimuth.
- Update the visibility status.
- Highlight the corresponding mission interval.

### Deliverable

An interactive timeline synchronized with
the Sun and Earth position visualization.

---

## Task 6: Build the Mission Metrics Dashboard

- [ ] Display total sunlight duration.
- [ ] Display sunlight availability percentage.
- [ ] Display longest darkness interval.
- [ ] Display total Earth visibility duration.
- [ ] Display Earth visibility percentage.
- [ ] Display longest Earth visibility blackout.
- [ ] Display simultaneous visibility percentage.
- [ ] Display the next Sun visibility transition.
- [ ] Display the next Earth visibility transition.
- [ ] Show measurement units clearly.
- [ ] Add explanations for technical terminology.
- [ ] Display data quality and calculation assumptions.

### Suggested Metrics

| Metric | Unit |
|--------|------|
| Sunlight Availability | % |
| Total Sunlight | Hours |
| Longest Darkness | Hours |
| Earth Visibility | % |
| Total Earth Visibility | Hours |
| Longest Earth Blackout | Hours |
| Simultaneous Visibility | % |
| Sun Elevation | Degrees |
| Earth Elevation | Degrees |

### Important

Distinguish between:

- Sun visibility and actual solar power generation.
- Earth visibility and successful radio communication.
- Geometric visibility and terrain-adjusted visibility.

Do not display calculated numbers without
identifying their meaning and assumptions.

### Deliverable

A mission metrics dashboard displaying
scientifically grounded results.

---

## Task 7: Build Side-by-Side Landing-Site Comparison

- [ ] Allow users to select at least two landing sites.
- [ ] Support comparing all three curated sites.
- [ ] Use the same date range for site comparisons.
- [ ] Display sunlight percentages side by side.
- [ ] Display Earth visibility percentages side by side.
- [ ] Compare longest darkness periods.
- [ ] Compare longest Earth blackouts.
- [ ] Compare simultaneous visibility.
- [ ] Highlight meaningful differences.
- [ ] Show each site's mission constraint results.
- [ ] Explain why one site may be preferable.
- [ ] Clearly identify differences in model fidelity.

### Example Comparison

| Metric | Site A | Site B | Site C |
|--------|--------|--------|--------|
| Sunlight | 75% | 62% | 84% |
| Earth Visibility | 55% | 88% | 70% |
| Max Darkness | 10 h | 16 h | 7 h |
| Max Blackout | 18 h | 5 h | 11 h |

These numbers are hypothetical.

### Important

When comparing sites, avoid presenting a
terrain-adjusted result as directly equivalent
to a geometric-only result without a warning.

A site with stronger sunlight is not
automatically the best landing site.

### Deliverable

An interactive comparison dashboard
showing the trade-offs between landing sites.

---

## Task 8: Display Mission Feasibility Results

- [ ] Load mission requirements from Phase 1.
- [ ] Allow users to adjust supported constraints.
- [ ] Display PASS or FAIL for each requirement.
- [ ] Highlight failed mission constraints.
- [ ] Provide a short explanation for each result.
- [ ] Display an overall constraints-met status.
- [ ] Identify missing data that prevents evaluation.
- [ ] Allow comparisons using the same constraints.
- [ ] Distinguish hypothetical requirements
      from real NASA flight requirements.

### Default Demonstration Constraints

| Requirement | Target |
|-------------|--------|
| Minimum Sunlight | 60% |
| Minimum Earth Visibility | 50% |
| Maximum Blackout | 12 hours |

### Example Output

Site A:

- Sunlight requirement: PASS
- Earth visibility requirement: PASS
- Maximum blackout requirement: FAIL

Result:

Site A does not satisfy all selected
demonstration constraints.

### Important

Do not label a site as fully "NASA-approved"
or definitively safe for landing.

The website evaluates selected environmental
and operational constraints, not every aspect
of mission feasibility.

### Deliverable

An interactive mission constraint panel
that explains site suitability.

---

## Task 9: Build Mission Delay Comparison

- [ ] Add a scenario comparison mode.
- [ ] Display the original mission date.
- [ ] Display the delayed mission date.
- [ ] Retrieve metrics for both mission intervals.
- [ ] Compare sunlight availability changes.
- [ ] Compare Earth visibility changes.
- [ ] Compare maximum darkness changes.
- [ ] Compare communication blackout changes.
- [ ] Highlight improvements and disadvantages.
- [ ] Display updated mission feasibility results.
- [ ] Provide an explanation of the changes.

### Example Scenario

Original landing:
December 1, 2026

Delayed landing:
December 11, 2026

Question:

How does a ten-day delay affect the
operational conditions of the lander?

### Expected User Experience

1. Select an original mission.
2. Select the delayed landing date.
3. Run both analyses.
4. Compare the resulting visibility windows.
5. Determine whether the original site still
   meets mission requirements.

### Deliverable

A mission-delay comparison interface
that demonstrates the effects of schedule changes.

---

## Task 10: Add User Experience and Accessibility Features

- [ ] Create a clear dashboard layout.
- [ ] Use consistent typography and spacing.
- [ ] Provide descriptions for technical terms.
- [ ] Add hover tooltips to unfamiliar metrics.
- [ ] Add loading states for scientific calculations.
- [ ] Add helpful error messages.
- [ ] Support keyboard navigation.
- [ ] Add sufficient text/background contrast.
- [ ] Avoid relying exclusively on colors.
- [ ] Make charts readable on smaller screens.
- [ ] Test mobile and desktop layouts.
- [ ] Add links to NASA scientific data sources.
- [ ] Display calculation limitations clearly.

### Suggested Dashboard Layout

Top Section:
- Project name
- Landing-site selector
- Date and mission controls

Main Section:
- Lunar landing-site map
- Sun/Earth position visualization

Analysis Section:
- Visibility timeline
- Mission metrics
- Feasibility results

Comparison Section:
- Site comparison
- Mission-delay comparison

Footer:
- NASA data attribution
- Scientific assumptions
- Project team information

### Deliverable

A polished, accessible interface suitable
for mission planners, educators, and the public.

---

## Task 11: Integrate Frontend and Backend

- [ ] Connect landing-site selection to backend data.
- [ ] Connect date controls to mission analysis requests.
- [ ] Retrieve Sun and Earth positions.
- [ ] Retrieve calculated visibility windows.
- [ ] Retrieve mission metrics.
- [ ] Retrieve mission constraint results.
- [ ] Display real results in frontend components.
- [ ] Handle backend connection failures.
- [ ] Handle missing or unsupported scientific data.
- [ ] Verify that changing sites updates all visualizations.
- [ ] Verify that changing dates updates all calculations.
- [ ] Ensure that outdated requests do not overwrite
      newer results.
- [ ] Confirm consistent UTC timestamps and units.

### Suggested API Endpoints

GET /api/sites

Returns available lunar landing sites.

GET /api/analysis?site_id=A&start=...&end=...

Returns astronomical positions, visibility
windows, and mission metrics.

POST /api/compare

Compares multiple landing sites or
mission date scenarios.

GET /api/terrain?site_id=A

Returns a terrain horizon profile
when supported.

These are proposed application endpoints,
not official NASA API endpoints.

### Example Frontend Response

```json
{
  "site_id": "A",
  "start_utc": "2026-12-01T00:00:00Z",
  "end_utc": "2026-12-08T00:00:00Z",
  "metrics": {
    "sunlight_percent": null,
    "earth_visibility_percent": null,
    "longest_darkness_hours": null,
    "longest_blackout_hours": null
  },
  "model": {
    "visibility_type": "geometric",
    "status": "not_calculated"
  }
}
```

Replace null values with actual Phase 3 results.

### Deliverable

A fully integrated frontend and backend
with functioning scientific visualizations.

---

## Task 12: Test the Website

- [ ] Test selecting each landing site.
- [ ] Test changing the landing date.
- [ ] Test changing the mission duration.
- [ ] Test visibility chart interactions.
- [ ] Test sky-view timestamp synchronization.
- [ ] Test side-by-side site comparison.
- [ ] Test mission-delay comparison.
- [ ] Test mission requirement adjustments.
- [ ] Test invalid dates and coordinates.
- [ ] Test missing backend data.
- [ ] Test API connection failures.
- [ ] Test desktop and mobile layouts.
- [ ] Verify scientific values match backend outputs.
- [ ] Verify labels and units are correct.
- [ ] Check that no fabricated data is shown
      as real NASA calculations.

### Critical Test Scenario

1. Open the website.
2. Select Site A.
3. Choose December 1, 2026.
4. Run the seven-day analysis.
5. Inspect Sun and Earth visibility timelines.
6. Switch to Site B.
7. Compare the sites.
8. Change the date to December 11, 2026.
9. Compare the original and delayed missions.
10. Review mission constraint results.

All steps should function without crashes
or inconsistent scientific measurements.

### Deliverable

A tested website ready for deployment
and final hackathon presentation.

---

## Phase 4 Completion Checklist

- [ ] React frontend initialized.
- [ ] Frontend connected to backend.
- [ ] Interactive lunar map implemented.
- [ ] Three landing sites selectable.
- [ ] Date and mission controls functional.
- [ ] Sun and Earth positions visualized.
- [ ] Geometric horizon displayed.
- [ ] Visibility timeline implemented.
- [ ] Mission metrics displayed.
- [ ] Side-by-side site comparison functional.
- [ ] Mission constraints displayed.
- [ ] Mission-delay comparison functional.
- [ ] Scientific assumptions documented.
- [ ] Loading and error states implemented.
- [ ] Responsive layout tested.
- [ ] End-to-end workflow tested.

### Advanced Completion Criteria

- [ ] Terrain horizon displayed in sky visualization.
- [ ] Terrain-adjusted visibility supported.
- [ ] Three-dimensional lunar terrain visualization.
- [ ] Smooth time-based animation.
- [ ] Interactive custom lunar coordinates.
- [ ] Educational explanations of lunar polar conditions.

---

## Phase 5 — Next Steps

Improve the application's mission decision-making
capabilities.

Planned features:

1. Adjustable spacecraft requirements.
2. Mission feasibility and constraint evaluation.
3. Solar energy and battery survival modeling.
4. Mission-delay recommendations.
5. Landing-site ranking based on selected priorities.
6. Explainable site recommendations.
7. Optional scientific exploration preferences,
   including proximity to permanently shadowed regions.

Phase 5 will focus on helping users make better
mission-planning decisions using the data
and visualizations developed in Phase 4.

---

## Official NASA Space Apps Resources

### NASA LROC QuickMap
https://quickmap.lroc.asu.edu/

Used for lunar imagery, terrain exploration,
and landing-site mapping references.

### NASA Moon Trek
https://trek.nasa.gov/moon/

Used for 3D lunar terrain exploration
and spatial understanding.

### NASA JPL Horizons
https://ssd.jpl.nasa.gov/horizons/

Used for the astronomical data displayed
in the website.

### NASA LOLA South-Pole Topography
https://pgda.gsfc.nasa.gov/products/78

Used for lunar elevation data and terrain
horizon analysis.

### Canadian Space Agency — Moon Exploration
https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/

Used for lunar exploration background
and educational information.

---

## Expected Final Outcome

By completing Phase 4, our team should have:

1. An interactive lunar south-pole map.
2. Three selectable landing sites.
3. Functional date and mission controls.
4. Sun and Earth position visualizations.
5. Sunlight and communication timelines.
6. A mission metrics dashboard.
7. Side-by-side landing-site comparisons.
8. Mission feasibility indicators.
9. Mission-delay comparison functionality.
10. A fully integrated and tested web application.

Phase 4 is complete when users can open the
website, select lunar landing sites and dates,
and understand the resulting sunlight and
Earth communication conditions using
real scientific data.

The application should clearly distinguish
between verified calculations, estimates,
and hypothetical mission assumptions.
