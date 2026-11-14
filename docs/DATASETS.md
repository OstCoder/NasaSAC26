# Task 4 — Data organization (deliverable)

One catalogue over every dataset the backend loads, so "where is the data, in
what units, from where, and does it agree with the other files" has one answer.

The catalogue is computed from the files at request time
(`backend/app/services/dataset_catalogue.py`), served at **`GET /api/datasets`**,
and checked by:

```bash
cd backend
python scripts/check_datasets.py          # table + cross-dataset problems; exit 1 on failure
python scripts/check_datasets.py --json   # the full payload
```

## What is stored where

| id | Dataset | Path | Records | Owner |
| --- | --- | --- | --- | --- |
| `sites` | Landing-site catalogue (verified coordinates, elevation, slope, PSR) | `data/demo/sites.json` | 6 sites, 3 mission candidates | `services/sites.py` |
| `site_series` | Hourly Sun/Earth azimuth + elevation (Phase 2 Task 2) | `data/scientific/site_series/` | 6 files, 1,014 records | `services/site_series.py` |
| `site_terrain` | LOLA 5 m/pix DEM inventory: extents, CRS, checksums, skyline (Task 3) | `data/reference/site_terrain.json` | 3 sites | `services/terrain_inventory.py` |
| `site_elevations` | LOLA 125 m-window elevation/slope evidence | `data/reference/site_elevations.json` | 4 sites | `scripts/sample_site_elevation.py` |
| `psr_catalogue` | LROC/LOLA PSR polygons (> 5 km²) | `data/reference/psrs.json` | 653 | `scripts/build_psr_catalogue.py` |
| `craters` | IAU Gazetteer crater centres | `data/reference/moon_craters.json` | gazetteer subset | `scripts/fetch_craters.py` |
| `ephemeris` | Optional tabulated Horizons sub-points | `data/scientific/ephemeris/` | **absent by design** | `scripts/fetch_horizons.py` |
| `horizon_masks` | LOLA-derived skyline masks | `data/scientific/horizon_masks/` | **absent — Task 6** | `scripts/build_horizon_mask.py` |
| `cache` | Horizons monthly tables + Moon Trek tiles | `data/cache/` | months + tiles on this machine | providers |

Absent datasets are listed with `available: false` and a reason; they are never
silently dropped from the catalogue, because "no file" and "no data" are
different claims.

## Canonical conventions (declared once, checked against every file)

| Quantity | Convention |
| --- | --- |
| Longitude | selenographic **east-positive**, stored in **[−180°, 180°)** (204.27°E is stored as −155.73°) |
| Latitude | selenographic planetocentric, Mean Earth / Polar Axis frame |
| Angles | degrees; azimuth clockwise from local lunar north, [0, 360) |
| Heights | metres above the **1737.4 km IAU mean sphere** (the Moon has no geoid) |
| Distances | kilometres |
| Time | UTC, ISO-8601 with `Z`; naive timestamps are rejected |
| Radius | 1737.4 km, also the DEM projection sphere |

`config/lunanav.config.json → coordinates` is the declared source of the
longitude convention; the catalogue fails if a file disagrees with it.

## Validation the catalogue performs

Cross-dataset, not just per-file:

1. every site has finite coordinates inside the legal ranges and a `source`;
2. every mission candidate exists and has a recorded elevation;
3. each series file's `site` block matches the catalogue's latitude, longitude
   (within 1e-6°) and elevation (within 0.05 m), and its `site_id` and window
   match the entry in `index.json` that lists it;
4. each terrain entry matches the same coordinates, its DEM records a 5 m pixel
   size, a checksum and the 1737.4 km frame, its obstruction angle is physical,
   and its pixel elevation agrees with the LOLA sampling evidence (0.05 m);
5. the series index total equals the records actually on disk, timestamps are
   chronological, and every value is finite;
6. the declared longitude convention is east-positive and [−180°, 180°);
7. the cache is reported unavailable (not "empty") when its directory is absent.

A failing check is reported by `problems[]` in the payload and by exit status 1
from the script — the API still serves the catalogue so a UI can show what is
broken rather than a blank page.

## Access from the backend and from Python

```bash
curl -s localhost:8000/api/datasets | python -m json.tool | head -40
curl -s 'localhost:8000/api/datasets?force=true'   # bypass the in-process cache
```

```python
from app.services.dataset_catalogue import build_catalogue

catalogue = build_catalogue()
series = next(d for d in catalogue["datasets"] if d["id"] == "site_series")
print(series["records"], series["details"]["step"], series["sources"])
```

Reading one site series record:

```python
import json
from pathlib import Path

payload = json.loads(Path("data/scientific/site_series/shackleton-rim-initial.json").read_text())
by_time = {r["timestamp_utc"]: r for r in payload["series"]}
by_time["2026-12-01T00:00:00Z"]
# {'site_id': 'shackleton-rim', 'timestamp_utc': '2026-12-01T00:00:00Z',
#  'sun':  {'azimuth_deg': 75.799377, 'elevation_deg': 1.524114, 'range_km': 147553095.89},
#  'earth': {'azimuth_deg': 162.397841, 'elevation_deg': -1.820125, 'range_km': 376568.371}}
```

## Caching (avoiding unnecessary requests)

- **Horizons sub-point tables** are fetched one month at a time and cached under
  `data/cache/horizons/<YYYY-MM>.json`; a repeated scenario reuses them.
- **Moon Trek tiles** are cached per tile under `data/cache/trek/` (including
  "no tile" markers, so a missing region is not re-requested).
- **The Task 2 series is itself a cache**: committed, so the mission windows do
  not need a live request for analysis.
- Neither cache directory is committed, and a cached file is never extended
  with invented values; the catalogue reports which months and how many tiles
  exist on the machine.

## Source information

Every dataset entry carries `sources` (label + URL) and `schema`. The series
files carry their exact Horizons query URLs, the terrain reference carries DEM
checksums and WGS-style descriptions, and both record when they were generated.

## Limitations

- There is no single database: datasets stay as human-readable JSON in the
  locations above, with the catalogue as the index. That is deliberate for a
  hackathon repository — a reviewer can read every value.
- Terrain rasters are ~41 MB each and stay in `data/cache/`, referenced by
  checksum; the repository stores the description, not the raster.
- `ephemeris` and `horizon_masks` are empty until Phase 2 Task 6 fills them.
- The catalogue validates structure and cross-file agreement. It cannot prove a
  value is correct; that is what the per-dataset verifiers and tests are for.
