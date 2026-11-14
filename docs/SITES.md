# Task 1 — Selected Landing Sites (deliverable)

Three lunar south-pole landing sites, selected with exact published coordinates,
recorded LOLA elevations, and identified nearby permanently shadowed regions
(PSRs). This is the deliverable for Phase 1 Task 1; everything here is served
live by the API (`GET /api/sites`, `GET /api/psrs`) and rendered in the planner.

## Deliverable table

| Site | Region | Latitude | Longitude | Elevation | Source |
|------|--------|----------|-----------|-----------|--------|
| A | Shackleton Crater Rim | −89.78° | 204.27°E | 1,734 m | Mazarico et al. 2011, Icarus 211, 1066 — LOLA south-pole point 4 (= NASA 2020 crewed candidate site 004); elevation: LOLA 5 m/pix PGDA Site04 DEM |
| B | Shackleton–de Gerlache Connecting Ridge | −89.45° | 222.69°E | 1,955 m | Mazarico et al. 2011 — LOLA point 1 (= NASA 2020 site 001); elevation: LOLA 5 m/pix PGDA Site01 DEM |
| C | de Gerlache Crater Rim | −88.67° | 291.90°E | 1,808 m | Mazarico et al. 2011 — LOLA point 11 (= NASA 2020 site 011); elevation: LOLA 5 m/pix PGDA Site11 DEM |

Longitudes are selenographic, east-positive, on the Moon Mean Earth/polar axis
frame; the [−180°, 180°) equivalents are −155.73°, −137.31° and −68.10°.
Elevations are metres above the 1737.4 km reference sphere.

## Where the coordinates come from (provenance chain)

The three regions were investigated with LROC QuickMap, then pinned to **exact,
peer-reviewed points** rather than informal map-click coordinates:

1. **Mazarico et al. 2011** (*"Illumination conditions of the lunar polar
   regions using LOLA topography"*, Icarus 211, 1066–1081,
   [doi:10.1016/j.icarus.2010.10.030](https://doi.org/10.1016/j.icarus.2010.10.030))
   tabulated LOLA south-pole candidate points for extended illumination.
2. **Kumari et al. 2022** (*"Detailed Analysis of the Impact of Solar
   Illumination and Topography on the Lunar South Pole"*, Planetary Science
   Journal 3:224, [doi:10.3847/PSJ/ac88c2](https://doi.org/10.3847/PSJ/ac88c2))
   documents that NASA's 2020 south-pole crewed candidate sites inherit that
   numbering:
   site 001 = Mazarico point 1, site 004 = point 4, site 007 = point 7,
   site 011 = point 11.
3. **PGDA** publishes a dedicated 5 m/pix LOLA DEM centred on each of those
   NASA 2020 site numbers ([products/78](https://pgda.gsfc.nasa.gov/products/78)),
   confirming the coordinate ↔ site-number mapping: each DEM's centre matches
   its Mazarico coordinate in the south polar stereographic projection to
   < 2.5 km (see "Verification").

Independent cross-checks: Gläser et al. 2017
([NTRS 20170007365](https://ntrs.nasa.gov/citations/20170007365)) place an
illumination-optimal rim cluster at −89.78°, 204.70°E (1.4 km from our Site A
point, 82.1% mean illumination) and Site B's ridge crest among their "CR"
cluster, and Kumari et al. 2022 analyse sites 011/007 in detail.

### Site A — Shackleton Crater Rim (`shackleton-rim`)

- **Point:** Mazarico 2011 point 4 — −89.78°, 204.27°E (−155.73°). The south
  pole itself lies on Shackleton's rim (IAU Gazetteer: centre −89.67°, 129.78°E,
  d = 20.9 km), so a rim point balances direct-to-Earth geometry against
  illumination.
- **Elevation:** 1,734 m — median of the 125 m window at the point in the
  LOLA 5 m/pix Site04 surf DEM (window std 3.5 m; centre pixel 1,728 m;
  slope in the same window: 8.8° median). RMS height uncertainty of the
  product is 0.32 m (Barker et al. 2021).
- **Nearby PSRs:** the mapped Shackleton floor PSR
  (`SP_896450_1282030`, 233.7 km², centroid −89.64°, 128.20°E) lies **2.48 km**
  from the point — the lander looks straight down into the ~4 km² PSR.
  Published smaller-scale values for this rim: Gläser et al. 2017 give
  PSRs as close as **30 m** (S1) to **370 m** (S0) from the lit rim clusters,
  and Kumari et al. 2022 list site 004 among rim points with ~90% solar
  visibility. Small PSRs below ~5 km² are excluded from the LROC shapefile
  product used here, which is why the *mapped* distance (2.48 km) is larger
  than the *published* sub-km values.

### Site B — Shackleton–de Gerlache Connecting Ridge (`connecting-ridge`)

- **Point:** Mazarico 2011 point 1 — −89.45°, 222.69°E (−137.31°), the crest of
  the ridge connecting Shackleton to de Gerlache.
- **Elevation:** 1,955 m — LOLA 5 m/pix Site01 surf DEM, 125 m window median
  (std 2.0 m; slope 3.8° median). The highest of the three sites.
- **Nearby PSRs:** nearest mapped (>5 km²) PSR is the one near Spudis
  (`SP_895060_2806850`, 53.3 km²) at **11.5 km**; the Shackleton floor PSR is
  11.9 km. Published sub-threshold values: Gläser et al. 2017 give PSRs
  **70 m** (C1-1) and **100 m** (C1-0) from the ridge crest cluster.

### Site C — de Gerlache Crater Rim (`de-gerlache-rim`)

- **Point:** Mazarico 2011 point 11 — −88.67°, 291.90°E (−68.10°), on the
  Earth-facing side of the pole.
- **Elevation:** 1,808 m — LOLA 5 m/pix Site11 surf DEM, 125 m window median
  (std 2.1 m; slope 3.8° median). Kumari et al. 2022 analyse this rim and report
  up to 82.6 % mean illumination for points on it, at elevations around 1,400 m;
  this point sits higher, so its elevation is quoted from the DEM instead.
- **Nearby PSRs:** the mapped de Gerlache PSR (`SP_883120_2691430`,
  243.4 km², centroid −88.31°, −90.86°E) lies **12.1 km** from the point.

### Reference site retained

`peak-near-shackleton` (−88.81°, 123.64°E, Mazarico 2011 point 7 = NASA 2020
site 007, 1,645 m) stays in the catalogue as a reference site for comparison;
it is no longer a mission candidate.

## Verification (what we checked, not just what we read)

The coordinates and elevations are not transcribed on trust; they are
cross-validated in code (`backend/scripts/sample_site_elevation.py`,
`backend/tests/test_sites_psr.py`):

1. **DEM-centre check.** Each PGDA 5 m/pix site DEM is centred on its NASA
   2020 site point. Converting the published (lat, lon) through our south
   polar stereographic projection gives offsets of 0.04–2.1 km from the DEM
   centres (the small offsets reflect the DEMs' centre-pixel round-off) —
   a wrong projection convention would produce tens of km.
2. **Load-time consistency.** The API refuses to start if an entry in
   `data/demo/sites.json` disagrees with the sampled evidence file
   `data/reference/site_elevations.json` by more than 0.05 m.
3. **Geometry regression tests.** Haversine distances, the stereographic
   round-trip, PSR point-in-ring/point-to-boundary distances, and the
   propagation of site elevation into the observer radius are all unit-tested
   (`backend/tests/test_sites_psr.py`).
4. **Parallax sanity.** Adding the recorded elevation changes Earth elevation
   by ~0.0005°/km of altitude — verified end-to-end through
   `POST /api/scenario`.

## How it is served

- `data/demo/sites.json` — the catalogue: exact coordinates, elevation,
  slope, `nasa_site_id`, per-site `sources[]` citations (label + URL), nearest
  mapped PSR (id, label, distance, area, centroid) and the count of mapped
  PSRs within 10 km. Enriched automatically at load time from the PSR
  catalogue.
- `data/reference/psrs.json` — 653 south-pole PSR polygons (>5 km²) built from
  the LROC product `NAC_POLE_PSR_SOUTH` by `backend/scripts/build_psr_catalogue.py`,
  with rings stored in south polar stereographic kilometres (x = ρ·sin λ,
  y = ρ·cos λ, ρ = 2·1737.4·tan((90°+φ)/2)) — the same convention as the map.
- `data/reference/site_elevations.json` — the sampling evidence behind each
  elevation/slope (per-product medians, window statistics, DEM centre
  offsets).
- `backend/scripts/sample_site_elevation.py` — re-derives the elevations from
  the PGDA DEMs (`data/cache/lola_5mpp/`); `backend/scripts/build_psr_catalogue.py`
  re-derives the PSR catalogue from the LROC shapefile.
- API: `GET /api/sites` (enriched), `GET /api/psrs`
  (`min_area_km2`, `max_latitude_deg`, `near_site_id` + `radius_km` filters),
  `POST /api/scenario` (accepts `location.elevation_m` for custom points).
- Frontend: the planner's site picker shows elevation/slope/nearest PSR; the
  map draws the PSR polygons as a shaded layer.

## Sources

- Mazarico, G., et al. "Illumination conditions of the lunar polar regions
  using LOLA topography." Icarus 211 (2011): 1066–1081.
  https://doi.org/10.1016/j.icarus.2010.10.030
- Kumari, S., et al. "Detailed Analysis of the Impact of Solar Illumination and
  Topography on the Lunar South Pole." Planetary Science Journal 3:224 (2022).
  https://doi.org/10.3847/PSJ/ac88c2
- Gläser, P., et al. "Illumination conditions at the lunar south pole
  (with PSR/slope/illumination statistics near candidate sites)."
  NASA NTRS 20170007365. https://ntrs.nasa.gov/citations/20170007365
- Gläser, P., et al. "Illumination conditions at the lunar south pole using
  high-resolution digital terrain models from LOLA." Icarus 243 (2014): 78–87.
  https://doi.org/10.1016/j.icarus.2014.08.013
- LOLA 5 m/pix south-pole site DEMs (Site01/04/07/11): NASA PGDA.
  https://pgda.gsfc.nasa.gov/products/78 (data under `data/cache/lola_5mpp/`)
- LROC NAC polar PSR shapefile (south), PSRs > 5 km²:
  https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_POLE_PSR_SOUTH
- IAU Gazetteer, Shackleton: https://planetarynames.wr.usgs.gov/Feature/5450
- LROC QuickMap (visual investigation): https://quickmap.lroc.asu.edu/
