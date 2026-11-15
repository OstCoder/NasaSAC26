
# Phase 6 — Scientific Exploration & Advanced Visualization

## Objective

Enhance our NASA Space Apps Challenge 2026 Lunar
Landing Site Navigator with scientific exploration
features, advanced lunar visualizations, and
improved educational experiences.

Build upon the astronomical calculations from
Phase 3, the interactive website from Phase 4,
and the mission decision-support system from Phase 5.

Focus on helping users understand the relationship
between:

1. Lunar south-pole geography.
2. Sunlight and shadow conditions.
3. Direct-to-Earth communication opportunities.
4. Permanently shadowed regions (PSRs).
5. Potential water-ice exploration.
6. Landing-site engineering constraints.

By the end of Phase 6, our website should provide
a more complete understanding of why some lunar
locations are scientifically interesting but
operationally challenging.

---

## Task 1: Research Permanently Shadowed Regions (PSRs)

- [ ] Research what permanently shadowed regions are.
- [ ] Understand why PSRs exist near the lunar poles.
- [ ] Research how low solar elevation and crater
      geometry create long-term shadowing.
- [ ] Investigate why PSRs may preserve water ice.
- [ ] Identify PSRs near our three candidate sites.
- [ ] Find verified NASA datasets showing PSR boundaries.
- [ ] Review dataset resolution and coordinate systems.
- [ ] Record sources and scientific limitations.
- [ ] Distinguish permanent shadowing from temporary
      darkness during the selected mission period.
- [ ] Document why PSRs are scientifically valuable.

### Key Scientific Concepts

Permanently Shadowed Region (PSR):
A location where direct sunlight does not reach
the surface over the relevant long-term solar
illumination cycle because of local geometry.

Water Ice:
Some permanently shadowed regions may contain
water ice or other volatile materials.

Scientific Importance:
Studying these regions could help scientists
understand lunar water, volatile preservation,
and resources for future exploration.

### Important

Not every PSR contains confirmed water ice.

Our application must not claim that a location
contains accessible ice solely because it
is permanently shadowed.

### Deliverable

A documented collection of verified PSR datasets,
scientific references, and candidate exploration
regions near our selected landing sites.

### Resources

NASA LROC QuickMap:
https://quickmap.lroc.asu.edu/

NASA Moon Trek:
https://trek.nasa.gov/moon/

NASA Science:
https://science.nasa.gov/

---

## Task 2: Integrate PSR Data Into the Lunar Map

- [ ] Obtain a usable PSR boundary dataset.
- [ ] Check the dataset's geographic coverage.
- [ ] Confirm its lunar coordinate reference system.
- [ ] Convert PSR data into a frontend-compatible format.
- [ ] Align PSR boundaries with the lunar map projection.
- [ ] Display PSRs as a separate map layer.
- [ ] Add a toggle to enable or disable the layer.
- [ ] Highlight PSRs near the selected landing sites.
- [ ] Display PSR boundaries with appropriate labels.
- [ ] Add a legend explaining the layer.
- [ ] Verify map alignment against source data.
- [ ] Display attribution for the scientific dataset.

### Suggested Map Layers

Layer 1:
Lunar Surface Imagery

Layer 2:
Candidate Landing Sites

Layer 3:
Terrain Elevation

Layer 4:
Permanently Shadowed Regions

Layer 5:
Sunlight and Earth Visibility Information

### Important

PSR boundaries must come from verified scientific
data rather than manually drawn approximations
presented as factual boundaries.

Ensure overlays align correctly with the
lunar map's coordinate system and projection.

### Deliverable

An interactive lunar map with verified PSR
boundaries displayed alongside candidate
landing sites.

---

## Task 3: Calculate Proximity to PSRs

- [ ] Load the selected landing site coordinates.
- [ ] Load verified PSR boundaries.
- [ ] Identify nearby permanently shadowed regions.
- [ ] Calculate the minimum surface distance from
      each landing site to nearby PSR boundaries.
- [ ] Use lunar surface geometry for distance estimates.
- [ ] Identify the nearest mapped PSR.
- [ ] Display proximity measurements in kilometers.
- [ ] Compare PSR proximity across landing sites.
- [ ] Handle sites with no nearby mapped PSRs.
- [ ] Record uncertainty caused by dataset resolution.
- [ ] Clearly distinguish distance from accessibility.

### Simplified Lunar Surface Distance

For two positions on an ideal spherical Moon:

d = R × c

Where:

d = Surface distance
R = Approximate lunar radius
c = Central angular separation between positions

Using the haversine relationship:

a =
sin²(Δlatitude / 2) +
cos(latitude1) × cos(latitude2) ×
sin²(Δlongitude / 2)

c = 2 × atan2(sqrt(a), sqrt(1 - a))

All angular inputs must be in radians.

A commonly used mean lunar radius is
approximately 1737.4 kilometers.

For proximity to a PSR polygon, calculate
the minimum distance to its boundary or
interior rather than only to its center.

### Important

Surface distance does not indicate whether
a rover can safely travel between locations.

Actual accessibility depends on:

- Terrain slope
- Crater walls
- Obstacles
- Surface conditions
- Rover capabilities
- Thermal and power constraints

### Deliverable

A PSR proximity analysis function that
reports distances from candidate landing
sites to nearby mapped PSRs.

---

## Task 4: Create a Water-Ice Exploration Mode

- [ ] Add an optional science exploration mode.
- [ ] Allow users to prioritize proximity to PSRs.
- [ ] Display nearby scientifically interesting regions.
- [ ] Combine PSR proximity with sunlight metrics.
- [ ] Combine PSR proximity with Earth visibility metrics.
- [ ] Compare candidate sites based on these factors.
- [ ] Display conflicts between engineering and
      scientific exploration priorities.
- [ ] Identify sites that satisfy selected constraints.
- [ ] Explain why a nearby PSR may be interesting.
- [ ] Clearly identify unsupported scientific claims.
- [ ] Avoid claiming confirmed water ice without evidence.

### Example User Scenario

A mission planner wants to investigate potential
water ice near the Moon's south pole.

The spacecraft requires:

- Adequate solar illumination.
- Acceptable direct-to-Earth visibility.
- Suitable battery reserves.
- Proximity to a scientifically interesting PSR.

Our application compares potential landing sites
and explains the trade-offs.

### Example Output

Site A:
Strong sunlight availability but relatively
far from the nearest mapped PSR.

Site B:
Moderate sunlight availability with a
closer mapped PSR.

Site C:
Potentially interesting science location,
but extended Earth visibility blackouts.

These are illustrative descriptions,
not calculated results.

### Important

The best site is not necessarily the closest
site to a permanently shadowed region.

Engineering constraints must still be evaluated.

### Deliverable

A science-focused mission planning mode that
combines PSR proximity with operational metrics.

---

## Task 5: Develop Advanced 3D Lunar Terrain Visualization

- [ ] Review available elevation data for selected sites.
- [ ] Choose Three.js or React Three Fiber.
- [ ] Create a 3D terrain mesh from elevation data.
- [ ] Apply appropriate lunar surface textures.
- [ ] Place landing-site markers on the terrain.
- [ ] Add camera rotation and zoom controls.
- [ ] Display realistic relative terrain elevations.
- [ ] Add a terrain scale or elevation legend.
- [ ] Indicate when vertical exaggeration is applied.
- [ ] Optimize terrain resolution for browser performance.
- [ ] Ensure markers align with their real coordinates.
- [ ] Provide a 2D fallback when 3D rendering is unavailable.

### Suggested 3D Features

- Rotatable terrain view
- Zoomable lunar surface
- Landing-site markers
- Crater and ridge geometry
- Terrain elevation visualization
- Optional PSR overlay
- Sun and Earth direction indicators

### Important

Scientific accuracy is more important than
creating a visually dramatic but incorrect
representation of lunar terrain.

Do not claim that a decorative 3D Moon
is a scientifically accurate elevation model.

### Deliverable

An interactive 3D visualization of at least
one selected lunar landing region using
verified elevation data.

### Resources

NASA Moon Trek:
https://trek.nasa.gov/moon/

NASA LROC QuickMap:
https://quickmap.lroc.asu.edu/

---

## Task 6: Add Sunlight and Shadow Visualization

- [ ] Use verified Sun position data from Phase 2.
- [ ] Use terrain data for supported landing sites.
- [ ] Determine the Sun direction at selected timestamps.
- [ ] Display the direction of incoming sunlight.
- [ ] Implement terrain-based shadow rendering.
- [ ] Update shadows when the timestamp changes.
- [ ] Clearly distinguish modeled shadows from
      actual observed lunar imagery.
- [ ] Synchronize shadow rendering with the timeline.
- [ ] Test low-elevation Sun conditions.
- [ ] Validate representative shadows against
      available NASA reference observations.
- [ ] Document limitations of the rendering model.

### Suggested Visualization

Display a 3D lunar terrain model where:

- The Sun's position changes over time.
- Crater walls cast shadows.
- Sunlit surfaces are visually distinguishable.
- Landing markers remain visible.
- Users can inspect how illumination changes.

### Important

Accurate shadow rendering requires correct
solar geometry and terrain data.

A simplified lighting effect should be labeled
as illustrative rather than scientifically exact.

Do not automatically classify temporarily
shadowed terrain as a permanent PSR.

### Deliverable

A time-controlled terrain illumination
visualization for a supported lunar site.

---

## Task 7: Create a Mission Time Animation

- [ ] Add an interactive mission time slider.
- [ ] Allow users to select a specific UTC timestamp.
- [ ] Add play and pause functionality.
- [ ] Add adjustable animation playback speed.
- [ ] Update Sun and Earth position markers over time.
- [ ] Update visibility status during playback.
- [ ] Synchronize the sky view with the timeline.
- [ ] Synchronize terrain illumination when available.
- [ ] Update mission metrics or selected-time details.
- [ ] Highlight visibility transitions.
- [ ] Prevent animation outside available data ranges.
- [ ] Handle gaps in astronomical data.
- [ ] Test playback across different mission periods.

### Expected User Experience

1. Select a landing site.
2. Choose a seven-day mission period.
3. Open the mission timeline.
4. Press Play.
5. Watch the Sun and Earth positions change.
6. Observe changes in visibility.
7. Pause at an interesting timestamp.
8. Inspect the exact scientific measurements.

### Important

Interpolate positions carefully.

Do not invent visibility transitions between
large observation gaps without a documented
interpolation method or refined calculations.

### Deliverable

An interactive mission-time animation
synchronized with astronomical measurements
and available terrain visualizations.

---

## Task 8: Build Educational Information Panels

- [ ] Create an explanation of lunar south-pole geography.
- [ ] Explain why the Sun stays near the polar horizon.
- [ ] Explain why some lunar craters remain shadowed.
- [ ] Explain the scientific importance of PSRs.
- [ ] Explain how lunar water ice may be preserved.
- [ ] Explain Earth visibility and lunar libration.
- [ ] Explain why sunlight affects spacecraft power.
- [ ] Explain why Earth visibility affects communication.
- [ ] Explain the purpose of landing-site comparisons.
- [ ] Include relevant scientific references.
- [ ] Make terminology understandable to non-specialists.
- [ ] Provide tooltips for technical measurements.

### Suggested Educational Topics

Topic 1:
Why Is the Lunar South Pole Important?

Topic 2:
What Are Permanently Shadowed Regions?

Topic 3:
Why Does Sunlight Matter for Spacecraft?

Topic 4:
How Do Lunar Spacecraft Communicate With Earth?

Topic 5:
Why Can Mission Delays Change Landing Conditions?

Topic 6:
Why Are Water-Ice Deposits Scientifically Important?

### Deliverable

A collection of educational panels that
explain the scientific principles behind
the application's calculations.

---

## Task 9: Improve Scientific Transparency

- [ ] Identify which data comes from JPL Horizons.
- [ ] Identify which data comes from lunar terrain datasets.
- [ ] Display the observation time range.
- [ ] Display dataset resolution when relevant.
- [ ] Identify geometric-only visibility calculations.
- [ ] Identify terrain-adjusted visibility calculations.
- [ ] Identify simplified power and battery models.
- [ ] Identify hypothetical mission parameters.
- [ ] Document coordinate systems and conventions.
- [ ] Document uncertainty and data limitations.
- [ ] Add source attribution to the website.
- [ ] Avoid unsupported scientific conclusions.

### Suggested Model Labels

GEOMETRIC MODEL

Visibility determined from astronomical
positions without terrain obstruction.

TERRAIN-AWARE MODEL

Visibility calculated using a local terrain
horizon derived from elevation data.

SIMPLIFIED ENERGY MODEL

Power and battery estimates based on
documented hypothetical spacecraft parameters.

UNAVAILABLE DATA

Insufficient verified data to calculate
the requested measurement.

### Important

The website should make it clear which
results are verified measurements,
model-derived estimates, or hypothetical
mission assumptions.

### Deliverable

A transparent scientific methodology
and data-source information section.

---

## Task 10: Optimize Website Performance

- [ ] Measure initial page loading time.
- [ ] Optimize large lunar terrain datasets.
- [ ] Reduce unnecessary API requests.
- [ ] Cache previously calculated results.
- [ ] Optimize chart rendering.
- [ ] Reduce unnecessary React re-renders.
- [ ] Test animation performance.
- [ ] Optimize 3D terrain meshes.
- [ ] Implement loading indicators.
- [ ] Handle network failures gracefully.
- [ ] Provide fallbacks for unsupported 3D rendering.
- [ ] Verify the application remains usable
      on slower devices.

### Performance Priorities

1. Fast initial dashboard loading.
2. Responsive site selection.
3. Smooth timestamp changes.
4. Reliable comparison charts.
5. Stable 3D rendering when enabled.

### Important

Do not compromise scientific accuracy
to improve visual performance.

If detailed terrain processing is expensive,
precompute terrain meshes and horizon profiles
where practical.

### Deliverable

A responsive website that handles scientific
datasets and visualizations efficiently.

---

## Task 11: Validate Scientific Features

- [ ] Verify PSR boundaries against source data.
- [ ] Verify landing-site map alignment.
- [ ] Test PSR distance calculations.
- [ ] Validate lunar surface distance formulas.
- [ ] Verify 3D terrain elevation consistency.
- [ ] Verify solar direction calculations.
- [ ] Verify Earth direction calculations.
- [ ] Test shadow geometry at known timestamps.
- [ ] Validate mission animation synchronization.
- [ ] Test missing terrain data behavior.
- [ ] Confirm all scientific units are correct.
- [ ] Confirm explanations match calculated results.
- [ ] Document unresolved scientific limitations.

### Example Test Cases

Test 1:
A landing site is inside a mapped PSR.

Expected:
Distance to that PSR = 0 km.

Test 2:
A landing site is outside all mapped PSRs.

Expected:
Calculate the distance to the nearest
mapped PSR boundary.

Test 3:
Sun elevation is lower than the terrain horizon
in the Sun's azimuth direction.

Expected:
The Sun is obstructed.

Test 4:
Terrain data is unavailable.

Expected:
Do not show terrain-adjusted visibility
as a verified result.

Test 5:
A mission animation timestamp changes.

Expected:
Sky positions, visibility indicators, and
available terrain visuals remain synchronized.

### Deliverable

Validated scientific exploration features
with tests and documented limitations.

---

## Task 12: Integrate and Test Advanced Features

- [ ] Connect the PSR map layer to site selection.
- [ ] Connect PSR proximity results to site comparison.
- [ ] Connect science preferences to mission evaluation.
- [ ] Connect 3D terrain to the selected landing site.
- [ ] Connect mission time controls to position data.
- [ ] Synchronize animations and visibility timelines.
- [ ] Connect educational panels to relevant features.
- [ ] Verify source attribution across the website.
- [ ] Test combined frontend and backend workflows.
- [ ] Test unsupported sites and missing datasets.
- [ ] Verify advanced features do not break core analysis.
- [ ] Confirm all advanced features can be disabled
      independently when necessary.

### Suggested API Endpoints

GET /api/science/psrs

Returns mapped PSR information.

GET /api/science/nearest-psr?site_id=A

Returns the nearest mapped PSR and
its estimated surface distance.

GET /api/terrain/mesh?site_id=A

Returns or references a terrain mesh
when supported.

GET /api/science/site-context?site_id=A

Returns scientific context and
available exploration information.

These are proposed application endpoints,
not official NASA APIs.

### Example Science Response

```json
{
  "site_id": "A",
  "nearest_psr": {
    "id": null,
    "distance_km": null,
    "source": null
  },
  "terrain": {
    "available": false,
    "resolution_m": null
  },
  "science": {
    "water_ice_confirmed": null,
    "notes": []
  },
  "status": "not_calculated"
}
```

Null values indicate that verified results
have not yet been populated.

Unknown water-ice status must not be
interpreted as confirmed absence.

### Deliverable

Advanced scientific exploration and visualization
features integrated into the website.

---

## Phase 6 Completion Checklist

### Core Scientific Features

- [ ] Permanently shadowed regions researched.
- [ ] Reliable PSR data sources identified.
- [ ] PSR data integrated into the application.
- [ ] PSR map layer implemented.
- [ ] PSR proximity calculations implemented.
- [ ] Scientific exploration preferences supported.
- [ ] Scientific information panels created.
- [ ] Scientific data sources documented.
- [ ] Scientific limitations clearly displayed.

### Application Improvements

- [ ] Mission-time visualization improved.
- [ ] Map interaction tested.
- [ ] Existing visibility charts verified.
- [ ] Mission comparison remains functional.
- [ ] Application performance optimized.
- [ ] Missing-data behavior tested.
- [ ] Advanced features integrated successfully.

### Advanced Completion Criteria

- [ ] Interactive 3D lunar terrain implemented.
- [ ] Terrain-based shadow rendering implemented.
- [ ] Animated sunlight conditions supported.
- [ ] Animated Earth positions supported.
- [ ] Science-focused mission recommendations added.
- [ ] Scientific model cross-validation completed.
- [ ] Advanced visualization performance optimized.

---

## Phase 7 — Next Steps

Prepare the Lunar Landing Site Navigator
for final demonstration and submission.

Planned activities:

1. Complete end-to-end application testing.
2. Review scientific data and calculations.
3. Fix critical bugs.
4. Deploy the website.
5. Prepare the final project demonstration.
6. Record a walkthrough video if required.
7. Complete project documentation.
8. Add scientific credits and data sources.
9. Explain the project's real-world impact.
10. Submit the project through NASA Space Apps.

Phase 7 will focus on final validation,
deployment, demonstration, and submission.

---

## Official NASA Space Apps Resources

### NASA LROC QuickMap
https://quickmap.lroc.asu.edu/

Used for lunar imagery, surface mapping,
terrain exploration, and PSR investigation.

### NASA Moon Trek
https://trek.nasa.gov/moon/

Used for 3D lunar terrain exploration
and geographic visualization references.

### NASA JPL Horizons
https://ssd.jpl.nasa.gov/horizons/

Used to obtain astronomical positions
of the Sun and Earth from lunar sites.

### NASA LOLA South-Pole Topography
https://pgda.gsfc.nasa.gov/products/78

Used for terrain elevations and
terrain horizon calculations.

### Canadian Space Agency — Moon Exploration
https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/

Used for lunar exploration background
and scientific education.

### NASA Science
https://science.nasa.gov/

Used for additional scientific information
about the Moon and lunar exploration.

---

## Expected Final Outcome

By completing Phase 6, our team should have:

1. Verified PSR information integrated into the map.
2. PSR proximity analysis for supported landing sites.
3. A science-focused exploration mode.
4. Improved lunar terrain and geographic visualization.
5. Enhanced Sun and Earth time-based visualizations.
6. Educational explanations of lunar polar conditions.
7. Clear scientific data attribution.
8. Documented modeling assumptions and limitations.
9. Optimized application performance.
10. Tested and integrated scientific features.

Phase 6 is complete when the application can
help users understand how lunar geography,
Sunlight, Earth connectivity, and scientific
exploration opportunities interact.

Advanced 3D terrain and shadow animations
are optional enhancements.

The application must remain useful and
scientifically transparent even if advanced
visualizations are not completed.
