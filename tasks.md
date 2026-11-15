
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

- [x] Initialize the frontend using React and TypeScript.
- [x] Configure Vite or the team's chosen framework.
- [x] Install Tailwind CSS for styling.
- [x] Set up routing if multiple pages are required.
- [x] Create reusable components.
- [x] Configure environment variables for the backend URL.
- [x] Set up API request utilities.
- [x] Configure loading and error states.
- [x] Confirm the application runs locally.
- [x] Test communication with the backend.

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

- [x] Display an interactive map of the lunar south pole.
- [x] Use lunar imagery or map tiles from a permitted source.
- [x] Display the three landing sites from Phase 1.
- [x] Add markers for each candidate landing site.
- [x] Allow users to select a site by clicking a marker.
- [x] Display each site's name and coordinates.
- [x] Highlight the currently selected location.
- [x] Support zooming and panning.
- [x] Display elevation data when available.
- [x] Provide a curated site list if map interaction fails.
- [x] Verify that coordinates align with the map projection.

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

- [x] Create a landing date and time selector.
- [x] Display timestamps in UTC.
- [x] Add mission duration controls.
- [x] Load the initial mission scenario.
- [x] Load the delayed mission scenario.
- [x] Allow users to switch between scenarios.
- [x] Provide a button to run the analysis.
- [x] Validate date ranges before sending requests.
- [x] Display an error for unsupported date ranges.
- [x] Prevent duplicate API requests while loading.
- [x] Reset outdated results when parameters change.

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

- [x] Display the Sun's azimuth and elevation.
- [x] Display Earth's azimuth and elevation.
- [x] Create a 2D sky-view visualization.
- [x] Show the geometric horizon.
- [x] Show the terrain horizon when available.
- [x] Represent the Sun with a recognizable marker.
- [x] Represent Earth with a recognizable marker.
- [x] Update positions based on selected timestamps.
- [x] Clearly indicate when an object is obstructed.
- [x] Add tooltips for position measurements.
- [x] Label the difference between geometric and
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

- [x] Create a timeline covering the mission duration.
- [x] Display sunlight availability intervals.
- [x] Display periods without direct sunlight.
- [x] Display Earth visibility intervals.
- [x] Display Earth obstruction intervals.
- [x] Highlight simultaneous Sun/Earth visibility.
- [x] Display accurate UTC timestamps.
- [x] Add hover details for visibility transitions.
- [x] Add zoom controls for longer mission intervals.
- [x] Allow users to select a timestamp.
- [x] Synchronize timeline selection with the sky view.
- [x] Handle incomplete or missing data clearly.

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

- [x] Display total sunlight duration.
- [x] Display sunlight availability percentage.
- [x] Display longest darkness interval.
- [x] Display total Earth visibility duration.
- [x] Display Earth visibility percentage.
- [x] Display longest Earth visibility blackout.
- [x] Display simultaneous visibility percentage.
- [x] Display the next Sun visibility transition.
- [x] Display the next Earth visibility transition.
- [x] Show measurement units clearly.
- [x] Add explanations for technical terminology.
- [x] Display data quality and calculation assumptions.

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

- [x] Allow users to select at least two landing sites.
- [x] Support comparing all three curated sites.
- [x] Use the same date range for site comparisons.
- [x] Display sunlight percentages side by side.
- [x] Display Earth visibility percentages side by side.
- [x] Compare longest darkness periods.
- [x] Compare longest Earth blackouts.
- [x] Compare simultaneous visibility.
- [x] Highlight meaningful differences.
- [x] Show each site's mission constraint results.
- [x] Explain why one site may be preferable.
- [x] Clearly identify differences in model fidelity.

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

- [x] Load mission requirements from Phase 1.
- [x] Allow users to adjust supported constraints.
- [x] Display PASS or FAIL for each requirement.
- [x] Highlight failed mission constraints.
- [x] Provide a short explanation for each result.
- [x] Display an overall constraints-met status.
- [x] Identify missing data that prevents evaluation.
- [x] Allow comparisons using the same constraints.
- [x] Distinguish hypothetical requirements
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

- [x] Add a scenario comparison mode.
- [x] Display the original mission date.
- [x] Display the delayed mission date.
- [x] Retrieve metrics for both mission intervals.
- [x] Compare sunlight availability changes.
- [x] Compare Earth visibility changes.
- [x] Compare maximum darkness changes.
- [x] Compare communication blackout changes.
- [x] Highlight improvements and disadvantages.
- [x] Display updated mission feasibility results.
- [x] Provide an explanation of the changes.

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

- [x] Create a clear dashboard layout.
- [x] Use consistent typography and spacing.
- [x] Provide descriptions for technical terms.
- [x] Add hover tooltips to unfamiliar metrics.
- [x] Add loading states for scientific calculations.
- [x] Add helpful error messages.
- [x] Support keyboard navigation.
- [x] Add sufficient text/background contrast.
- [x] Avoid relying exclusively on colors.
- [x] Make charts readable on smaller screens.
- [x] Test mobile and desktop layouts.
- [x] Add links to NASA scientific data sources.
- [x] Display calculation limitations clearly.

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

- [x] Connect landing-site selection to backend data.
- [x] Connect date controls to mission analysis requests.
- [x] Retrieve Sun and Earth positions.
- [x] Retrieve calculated visibility windows.
- [x] Retrieve mission metrics.
- [x] Retrieve mission constraint results.
- [x] Display real results in frontend components.
- [x] Handle backend connection failures.
- [x] Handle missing or unsupported scientific data.
- [x] Verify that changing sites updates all visualizations.
- [x] Verify that changing dates updates all calculations.
- [x] Ensure that outdated requests do not overwrite
      newer results.
- [x] Confirm consistent UTC timestamps and units.

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

- [x] Test selecting each landing site.
- [x] Test changing the landing date.
- [x] Test changing the mission duration.
- [x] Test visibility chart interactions.
- [x] Test sky-view timestamp synchronization.
- [x] Test side-by-side site comparison.
- [x] Test mission-delay comparison.
- [x] Test mission requirement adjustments.
- [x] Test invalid dates and coordinates.
- [x] Test missing backend data.
- [x] Test API connection failures.
- [x] Test desktop and mobile layouts.
- [x] Verify scientific values match backend outputs.
- [x] Verify labels and units are correct.
- [x] Check that no fabricated data is shown
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

- [x] React frontend initialized.
- [x] Frontend connected to backend.
- [x] Interactive lunar map implemented.
- [x] Three landing sites selectable.
- [x] Date and mission controls functional.
- [x] Sun and Earth positions visualized.
- [x] Geometric horizon displayed.
- [x] Visibility timeline implemented.
- [x] Mission metrics displayed.
- [x] Side-by-side site comparison functional.
- [x] Mission constraints displayed.
- [x] Mission-delay comparison functional.
- [x] Scientific assumptions documented.
- [x] Loading and error states implemented.
- [x] Responsive layout tested.
- [x] End-to-end workflow tested.

### Advanced Completion Criteria

- [x] Terrain horizon displayed in sky visualization.
- [x] Terrain-adjusted visibility supported.
- [x] Three-dimensional lunar terrain visualization.
- [x] Smooth time-based animation.
- [x] Interactive custom lunar coordinates.
- [x] Educational explanations of lunar polar conditions.

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
