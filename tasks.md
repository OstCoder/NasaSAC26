
# Phase 2 — NASA Data Integration

## Objective

Integrate official NASA scientific resources to retrieve
accurate Sun and Earth positions for our selected lunar
south-pole landing sites.

Prepare lunar terrain data for the visibility calculations
and mission-planning features in later phases.

By the end of Phase 2, our backend should be able to accept
a landing site's coordinates and a date range, retrieve
astronomical position data, and save the results in a
structured format.

---

## Task 1: Integrate JPL Horizons

- [ ] Read the JPL Horizons documentation.
- [ ] Set up Python access using the Horizons API or Astroquery.
- [ ] Configure an observer at a specific lunar surface location.
- [ ] Use one verified landing site from Phase 1.
- [ ] Request the Sun's apparent position at the site.
- [ ] Request Earth's apparent position at the same site.
- [ ] Extract azimuth and elevation angles for both objects.
- [ ] Confirm the coordinate conventions and measurement units.
- [ ] Test requests with multiple dates and times.
- [ ] Handle API errors and invalid inputs.

### Required Inputs

- Lunar latitude
- Lunar longitude
- Observer height/elevation
- Start date and time (UTC)
- End date and time (UTC)
- Time interval between observations

### Required Outputs

- Timestamp (UTC)
- Sun azimuth (degrees)
- Sun elevation (degrees)
- Earth azimuth (degrees)
- Earth elevation (degrees)

### Deliverable

A working Python module that retrieves Sun and Earth
positions from JPL Horizons for a selected lunar site
and time interval.

### Resources

JPL Horizons:
https://ssd.jpl.nasa.gov/horizons/

Horizons API Documentation:
https://ssd-api.jpl.nasa.gov/doc/horizons.html

---

## Task 2: Generate Astronomical Time-Series Data

- [ ] Use the three verified lunar sites from Phase 1.
- [ ] Generate Sun position data for each site.
- [ ] Generate Earth position data for each site.
- [ ] Use December 1–8, 2026, as the initial analysis period.
- [ ] Use December 11–18, 2026, as the delayed mission period.
- [ ] Start with 1-hour observation intervals.
- [ ] Ensure all timestamps use UTC.
- [ ] Store the observations in chronological order.
- [ ] Ensure Sun and Earth positions share matching timestamps.
- [ ] Confirm that missing data is not silently treated as zero.

### Example Data Structure

```json
{
  "site_id": "A",
  "timestamp_utc": "2026-12-01T00:00:00Z",
  "sun": {
    "azimuth_deg": null,
    "elevation_deg": null
  },
  "earth": {
    "azimuth_deg": null,
    "elevation_deg": null
  }
}
```

Replace null values with actual Horizons results.

### Deliverable

Astronomical time-series data for all three landing sites
across both proposed mission periods.

### Note

Hourly sampling is suitable for initial analysis.

Phase 3 should refine observations near visibility
transitions to improve the accuracy of sunset,
sunrise, Earthset, and Earthrise estimates.

---

## Task 3: Obtain Lunar Terrain Data

- [ ] Open NASA LROC QuickMap.
- [ ] Locate the three selected landing coordinates.
- [ ] Inspect the terrain surrounding each location.
- [ ] Identify relevant elevation and topography datasets.
- [ ] Explore the same regions using NASA Moon Trek.
- [ ] Record the available terrain data resolution.
- [ ] Obtain downloadable elevation data where available.
- [ ] Document the coordinate reference system and height datum.
- [ ] Record the source and coverage of each terrain dataset.
- [ ] Identify any missing terrain coverage or limitations.

### Important Terrain Information

For each landing site, collect:

- Latitude and longitude
- Surface elevation
- Terrain elevation data
- Dataset resolution
- Coordinate reference system
- Data source
- Data coverage

Terrain information will later help determine whether
nearby hills, crater walls, or ridges obstruct the Sun
or Earth.

### Deliverable

A documented collection of lunar terrain data for
the three landing sites, including at least one
usable digital elevation model for Phase 3.

### Resources

NASA LROC QuickMap:
https://quickmap.lroc.asu.edu/

NASA Moon Trek:
https://trek.nasa.gov/moon/

NASA LOLA South-Pole Topography:
https://pgda.gsfc.nasa.gov/products/78

---

## Task 4: Organize and Store the Data

- [ ] Define a consistent data structure for each landing site.
- [ ] Store the verified site coordinates.
- [ ] Store Sun and Earth time-series results.
- [ ] Save dataset source information.
- [ ] Store terrain files or references separately.
- [ ] Use consistent units across all datasets.
- [ ] Use a consistent lunar longitude convention.
- [ ] Add basic validation for missing or invalid values.
- [ ] Cache astronomical results to avoid unnecessary requests.
- [ ] Ensure the data can be accessed by the backend.

### Suggested Project Structure

```text
backend/
├── data/
│   ├── sites.json
│   ├── ephemeris/
│   │   ├── site_a.json
│   │   ├── site_b.json
│   │   └── site_c.json
│   └── terrain/
│
├── services/
│   └── horizons.py
│
└── tests/
    └── test_horizons.py
```

The exact structure can be adjusted to match the team's
existing repository.

Large scientific datasets should not automatically
be committed to GitHub.

### Deliverable

An organized data pipeline that stores lunar landing
sites, astronomical observations, and terrain references.

---

## Task 5: Validate NASA Data

- [ ] Confirm that all three site coordinates are valid.
- [ ] Verify the Horizons observer location is on the Moon.
- [ ] Check Sun and Earth position results.
- [ ] Compare selected results against Horizons reference output.
- [ ] Verify azimuth and elevation units.
- [ ] Confirm UTC date and time handling.
- [ ] Check data continuity across the mission interval.
- [ ] Test the same site on different dates.
- [ ] Test different sites at the same date and time.
- [ ] Document any assumptions or known limitations.

### Important Validation Checks

1. Sun and Earth positions must come from actual
   astronomical calculations.

2. The observer must be configured at the correct
   lunar location, not at Earth's surface or
   the Moon's center.

3. Elevation angles must be interpreted relative
   to the correct local reference plane.

4. Geometric visibility must not be confused with
   terrain-obstructed visibility.

5. Unknown or missing results must not be presented
   as verified measurements.

### Deliverable

Validated astronomical datasets and documented
limitations for all three landing sites.

---

## Task 6: Prepare Data for Phase 3

- [ ] Make the astronomical data accessible to calculation modules.
- [ ] Ensure all time-series records have consistent fields.
- [ ] Make the selected sites available through a shared data file.
- [ ] Prepare terrain data for future horizon calculations.
- [ ] Document how to load and query the datasets.
- [ ] Confirm that frontend and backend developers agree on formats.
- [ ] Test retrieving data for at least one site and date range.

### Deliverable

A verified dataset and functioning data-access layer
ready for Sun visibility, Earth visibility, and
terrain-obstruction calculations.

---

## Phase 2 Completion Checklist

- [ ] JPL Horizons successfully integrated.
- [ ] Sun positions retrieved using real NASA data.
- [ ] Earth positions retrieved using real NASA data.
- [ ] Three lunar landing sites supported.
- [ ] Initial mission date range processed.
- [ ] Alternative mission date range processed.
- [ ] Astronomical time-series data saved.
- [ ] Lunar terrain sources identified.
- [ ] At least one usable terrain dataset obtained.
- [ ] Data formats standardized.
- [ ] Astronomical results validated.
- [ ] Backend data pipeline tested.
- [ ] Data ready for Phase 3.

---

## Phase 3 — Next Steps

Use the data collected in Phase 2 to calculate
actual mission visibility conditions.

Planned calculations:

1. Sun visibility above the geometric horizon.
2. Earth visibility above the geometric horizon.
3. Terrain obstruction of Sun and Earth.
4. Direct sunlight availability over time.
5. Direct-to-Earth communication visibility windows.
6. Longest continuous darkness period.
7. Longest Earth communication blackout.
8. Simultaneous Sun and Earth visibility.

These calculations will form the scientific foundation
of our lunar mission-planning website.

---

## Official NASA Space Apps Resources

### NASA LROC QuickMap
https://quickmap.lroc.asu.edu/

Used for lunar imagery, surface terrain exploration,
and landing site inspection.

### NASA Moon Trek
https://trek.nasa.gov/moon/

Used for 3D lunar exploration and understanding
the geography surrounding potential landing sites.

### NASA JPL Horizons
https://ssd.jpl.nasa.gov/horizons/

Used for calculating the positions of the Sun
and Earth from selected lunar surface locations.

### Canadian Space Agency — Moon Exploration
https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/

Used for lunar exploration background and
scientific mission context.

---

## Expected Final Outcome

By completing Phase 2, our team should have:

1. A working NASA ephemeris data integration.
2. Real Sun and Earth positions for three lunar sites.
3. Astronomical data covering two mission date ranges.
4. Lunar terrain datasets or documented references.
5. Validated and organized scientific data.
6. A backend data pipeline ready for Phase 3.

Phase 2 is complete when our team can reliably
retrieve the astronomical data needed to evaluate
lunar landing sites without inventing measurements.
