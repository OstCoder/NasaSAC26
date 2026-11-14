# Task 5 — Data validation (deliverable)

The Task 2 series is only useful if its numbers mean what the schema says. This
document records what was validated, how, and what the validation cannot prove.

Everything below is produced by one command, from the committed files:

```bash
cd backend
python scripts/validate_nasa_data.py            # offline, no network
python scripts/validate_nasa_data.py --json     # the full report
python scripts/validate_nasa_data.py --live     # re-query Horizons, rewrite the evidence
```

The latest report is committed at `data/reference/nasa_validation.json` and
served at **`GET /api/validation`**. The independent Horizons sample it compares
against is `data/reference/horizons_reference.json`. The script exits 1 on any
failed check, so it can gate a release.

## Three sources, never merged

| Source | What it is | Where |
| --- | --- | --- |
| The dataset | 1,014 hourly Sun/Earth records, 3 sites × 2 windows | `data/scientific/site_series/` |
| The reference | A separate Horizons fetch at a 12 h step over the same spans | `data/reference/horizons_reference.json` |
| The model | LunaNav's own Meeus ephemeris, recomputed topocentrically | `app/providers/ephemeris_analytic.py` |

The reference and the model share nothing: one is JPL's geometry with light-time
and physical libration, the other is a truncated closed-form series. Agreement
between them and the committed values is what makes a frame, sign, column or copy
error visible.

## What each Task 5 item checks

| Task 5 item | Check | Result |
| --- | --- | --- |
| All three site coordinates are valid | `site_coordinates` | 3/3 finite, sourced, inside their PGDA DEM footprint and identical in the series and terrain files |
| The Horizons observer is on the Moon | `observer_on_moon` | 12 queries use `CENTER='coord@301'` (body 301), altitude 1.736–1.957 km above the mean sphere, and the recorded site coordinate; Horizons echoes that observer back |
| Sun and Earth results are correct | `sun_earth_positions` | 1,014 records × 2 bodies agree with the independent model to ≤ 0.032° in elevation, ≤ 0.020° in azimuth |
| Compare against Horizons reference output | `horizons_reference` | 180 rows at 12 h marks over both windows reproduced at the exact hourly timestamps |
| Azimuth and elevation units | `units` | Azimuth ∈ [0, 360), elevation ∈ [−90, 90]; the radian hypothesis is rejected; Sun range median 1.472e8 km, Earth 3.958e5 km |
| UTC date and time handling | `utc_time` | Every timestamp is ISO-8601 `Z`, round-trips, is exactly 3,600 s from its neighbour, and starts on the configured landing date |
| Data continuity across the interval | `continuity` | 169 samples per file, no duplicate or missing hour, hour-to-hour change within the model's own step + 0.05° |
| The same site on different dates | `same_site_different_dates` | Observer unchanged, windows 10 days apart, Sun/Earth geometry differs in each (a copied file would not) |
| Different sites at the same time | `different_sites_same_time` | Pairwise differences equal the model's prediction; Sun elevation spread up to 1.1° proves independent observers |
| Assumptions and limitations documented | `assumptions_documented` | This file plus the `assumptions` and `limitations` blocks in the report |

Numbers quoted above are from the committed run; the live report carries the
exact values and their timestamps.

## Coordinates and observer

A coordinate is only "on the Moon" if it is a point on the surface, not the
Moon's centre and not an Earth station. Three independent facts pin it down:

1. each site's latitude/longitude projects inside its 16 km PGDA DEM footprint
   (`polar_stereographic_xy` against the raster bounds) and matches the terrain
   reference to 1e-6°;
2. the observer altitude recorded in every series file is 1.7–2.0 km above the
   1737.4 km mean sphere, so the observer radius is 1739.1–1739.4 km — an Earth
   surface observer would need ~4,640 km, the Moon's centre −1,737 km;
3. every query names `CENTER='coord@301'`, and the live fetch returns
   `Center geodetic` equal to the requested longitude, latitude and altitude.

## Units and time

- Azimuth is degrees clockwise from local lunar north, `0 ≤ az < 360`.
- Elevation is degrees above the local horizontal, airless, terrain-free.
- Ranges are kilometres: the median Sun range is 1.472e8 km and the median
  Earth range 3.958e5 km. A value stored in AU (≈1.0 and ≈0.0026) fails the
  physical-span check by five orders of magnitude.
- The analytic comparison also rejects radians: interpreting the stored angles
  as radians moves them away from the model by far more than the tolerance.
- All timestamps are UTC. The parser rejects naive input, and the series
  timestamps round-trip through it unchanged. Horizons is sent
  `START_TIME='YYYY-MM-DD HH:MM'` with no zone suffix, which Horizons treats as
  UTC; the live reproduction of the same instants confirms that reading.

## Same site, different dates / different sites, same time

The two mission windows start ten days apart, so the same site must produce
*different* Sun and Earth geometry. The check compares the two windows sample by
sample and fails if they are identical (a copy error) while also confirming the
observer block is unchanged.

The three sites are 10–40 km apart, so at a shared timestamp the Sun's elevation
differs by up to 1.1° (mostly the latitude difference tilting the local horizon)
and Earth by a few tenths of a degree (parallax plus the same tilt). The check
requires the observed pairwise differences to match the model's prediction to
0.15° — a shared or Moon-centred observer would give zero difference and fail.

## Assumptions

1. Longitude is selenographic east-positive in [−180, 180); Horizons receives the
   same meridian as 0–360°.
2. Heights are metres above the 1737.4 km IAU mean sphere; the Moon has no geoid.
3. The observer is the site point plus a 2 m antenna/eye height above the LOLA
   surface sample.
4. Elevation is apparent, airless and terrain-free: the geometric horizon with no
   atmospheric refraction.
5. UTC is used everywhere; UTC → TT for the analytic model uses the fixed
   69.184 s offset valid for 2026–2030.
6. Hourly sampling is adequate to validate the data, not to time sunrise or
   Earthrise; Phase 3 refines the edges.
7. Horizons applies light-time and aberration to the apparent position; the
   analytic model omits both.

## Known limitations

- **The authority is still Horizons.** The validation proves reproduction and
  physical consistency, not that JPL's ephemeris is correct.
- **Model accuracy.** Meeus' truncated series omits physical libration, light-time
  and aberration; agreement of a few hundredths of a degree is expected and
  observed. Sub-arcsecond agreement is not claimed.
- **Geometric, not terrain-obstructed.** Every elevation here is above the flat
  local horizon. The committed LOLA masks (`data/scientific/horizon_masks/`) reach
  9.43°, 2.85° and 1.28° at the 2 m observer, so a body at +0.5° can still be
  hidden; applying terrain is Phase 3's calculation, not this validation's.
- **Sampling.** The series is hourly and the reference is 12-hourly. Minutes in
  between are not validated by either; interpolation must be labelled as such.
- **Observer height.** 2 m is assumed. A real lander's camera or antenna sits at a
  different height, which shifts the geometric horizon by ~0.0005° per km and the
  terrain horizon much more.
- **Site elevation provenance.** Elevations are a 125 m-window median of a
  5 m/pixel LOLA DEM, not a surveyed datum, and the sites are study coordinates,
  not certified landing pads.
- **Frame.** Moon Mean Earth / Polar Axis, planetocentric, with the 1.54242°
  lunar-equator inclination in the analytic model. PA/ME differences (~0.5 km at
  the surface) and any future IAU frame change are below the tolerances, not zero.
- **No atmosphere or refraction** — physically right for the Moon, and a reason
  these elevations are not comparable with Earth-based observing conventions.
- **No power or comms meaning.** Sun elevation is illumination geometry, never
  electrical power; Earth elevation is line-of-sight geometry, never a link budget.
- **Scope.** Only the three mission candidates and the two mission windows are
  validated. Custom coordinates and other dates use the same code but are not
  covered by the report.

## Reproducing the evidence

`--live` rewrites both committed files and reports what changed:

1. `reproduction` — a fresh 1 h Horizons fetch at each site's initial landing
   date must equal the committed records at the same timestamps (tolerance
   0.002°, 1 km). Observed difference: 0.
2. `echoed_observer` — Horizons must echo the exact observer it used.
3. `reference_stable` — the re-fetched reference table must match the committed
   one row for row, so the evidence is deterministic rather than a one-off.

If the live checks fail, the committed values are stale or a convention changed;
do not use them until the cause is understood.

## Phase 3 Task 10 — NASA illumination cross-check

The tasks list asks the Phase 3 calculations to be checked against NASA
illumination reference data "where comparable". The comparable product is the
**LROC/LOLA south-pole permanent-shadow catalogue** (`data/reference/psrs.json`,
traced from the LOLA shadow masks of Mazarico et al. 2011): a PSR is ground that
never receives direct sunlight, which is exactly the question the terrain model
answers.

```bash
cd backend
python scripts/check_psr_illumination.py   # needs the cached 189 MB LOLA wide DEM
```

The script takes the mapped PSRs larger than 100 km² (44 of them). Of those, 37
lie inside the committed 80 m/pix `LDEM_80S_80MPP_ADJ` wide DEM with at least
30 km of ground around them and are ray-marched from the recorded centroid (2 m
observer, lunar curvature, 1° azimuths, up to 150 km and capped at the DEM edge);
the other 7 are recorded as skipped, never tested against clipped data. The script
compares the Sun's topocentric
elevation against that skyline for every day from 2026-12-01 to 2027-11-30. The
result is committed as `data/reference/illumination_crosscheck.json`
(`lunanav.illumination_crosscheck.v1`), and
`backend/tests/test_illumination_crosscheck.py` validates it offline: no sampled
PSR receives a sunlit sample, every agreement has a non-flat skyline, and the DEM
checksum matches `wide_dem.json`.

What this proves and does not:

- It is a **shadow / no-shadow classification** comparison, not a time-series
  illumination percentage. NASA's product is a polygon mask; a per-sample
  percentage would need an illumination raster the project does not have.
- Sun positions come from the analytic model (a few hundredths of a degree from
  Horizons). The agreement margins are degrees, so the classification is not
  sensitive to that error.
- A PSR centroid represents a compact region. For elongated PSRs the lit end is
  outside the sampled point; the check reports the margin rather than claiming a
  polygon-wide proof.
- The 80 m/pix DEM resolves rims and massifs, not ridges narrower than ~80 m.
  The ray-march stops at 150 km or the DEM edge, whichever comes first; 21 of the
  37 checked rows are edge-limited, so their skyline is a lower bound on
  obstruction. It remains a limitation rather than a guarantee.
