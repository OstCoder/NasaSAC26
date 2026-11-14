# Task 6 — Data access for Phase 3 (deliverable)

The Phase 2 data is only useful if a calculation module can ask for it without
knowing a file path or a JSON key. This is that layer:

- **Sun/Earth direction** for a candidate site at a UTC instant, from the
  committed Task 2 series (`lunanav.site_series.v1`);
- **terrain skyline** for the same site, from the LOLA mask
  (`lunanav.horizon_mask.v1`);
- **clearance** per body — elevation minus skyline — which is what a Phase 3
  visibility rule consumes.

Everything is local. No network, no science in the frontend, no value invented
outside a stored window.

## What Task 6 added

| Piece | Where | What it gives Phase 3 |
| --- | --- | --- |
| Horizon masks | `data/scientific/horizon_masks/*.json` (committed) | 360-point skyline per candidate, ray-marched from the 5 m/pix LOLA DEM |
| Mask builder | `backend/scripts/build_site_horizon_masks.py` | Rebuilds the masks from the cached DEMs; `--verify-only` checks the committed ones offline |
| Data-access layer | `backend/app/services/site_data.py` | `load_series`, `sample_records`, `load_mask`, `apply_mask`, `build_readiness` |
| HTTP access | `GET /api/series`, `GET /api/readiness` | The same records and readiness matrix for any client |
| Format contract | `frontend/src/types/api.ts` | TypeScript mirror of the two responses, field for field |

The three masks:

| Site | Azimuth points | Radius | Max obstruction (2 m eye) | At azimuth |
| --- | --- | --- | --- | --- |
| `shackleton-rim` | 360 | 6.258 km | 9.428° | 236° |
| `connecting-ridge` | 360 | 7.692 km | 2.849° | 161° |
| `de-gerlache-rim` | 360 | 7.579 km | 1.284° | 287° |

These are **lower** than the `terrain.max_obstruction_deg` values in
`data/reference/site_terrain.json` (12.66°, 10.63°, 5.95°) because those were
measured from the ground (0 m eye). A 2 m eye sees a nearby rim lower, by
`atan(2 m / distance)`: at `connecting-ridge`, azimuth 160°, the maximum comes
from terrain 5 m away at ground level (10.63°) and from 20 m away at 2 m
(2.83°). Everything beyond 500 m there is below the geometric horizon
(−1.2°). The mask and the Sun/Earth track therefore describe the same observer.

## Load it from Python

```python
from app.services.site_data import (
    apply_mask, build_readiness, load_mask, load_series, sample_records,
)

table = load_series("shackleton-rim", "initial")     # 169 hourly records, 1-8 Dec 2026
table.sun.azimuth_deg[:3], table.sun.elevation_deg[:3]
# (array([75.799377, 75.292744, 74.786098]), array([1.524114, 1.525762, 1.527408]))

# Any grid inside the stored window; azimuth is interpolated circularly.
records, meta = sample_records(table, "2026-12-01T00:00:00Z", "2026-12-01T06:00:00Z", 30)
meta["interpolated"]  # True - not every 30 min sample is stored

mask = load_mask("shackleton-rim")                   # HorizonMask, 360 points
geometry = apply_mask(records, mask)
geometry["sun"]["clearance_deg"]                     # elevation - skyline(azimuth)
geometry["sun"]["above_skyline"]                     # boolean, not a mission verdict
```

`load_series` refuses a record with missing or extra fields, an unknown window
or a mismatched site. `sample_records` raises `OutOfSupportedRangeError` instead
of extrapolating. `load_mask` raises `DataUnavailableError` instead of falling
back to a flat horizon; use the `lola_or_flat` provider if a flat fallback is
what you want, and keep its `geometric_only` label.

Readiness per candidate:

```python
report = build_readiness()
report["summary"]   # {'sites': 3, 'ready': 3, 'with_mask': 3, 'missing': []}
```

## Load it over HTTP

```bash
curl -s 'localhost:8000/api/series?site_id=shackleton-rim' | python -m json.tool | head -30
curl -s 'localhost:8000/api/series?site_id=connecting-ridge&start=2026-12-11T00:00:00Z&stop=2026-12-11T06:00:00Z&step_minutes=30'
curl -s localhost:8000/api/readiness | python -m json.tool
```

`/api/series` returns the **on-disk record shape**, so a client parses one
format whether it reads the JSON file or the API:

```json
{
  "schema": "lunanav.series_access.v1",
  "records_schema": "lunanav.site_series.v1",
  "site": {"site_id": "shackleton-rim", "name": "...", "latitude_deg": -89.78,
           "longitude_deg": -155.73, "elevation_m": 1734.05, "height_m": 2.0,
           "altitude_km": 1.73605},
  "window": {"key": "initial", "label": "...", "start_utc": "2026-12-01T00:00:00Z",
             "stop_utc": "2026-12-08T00:00:00Z"},
  "request": {"start_utc": "...", "stop_utc": "...", "step_minutes": 60.0,
              "native_step": "1 h", "interpolated": false, "samples": 169},
  "mask": {"site_id": "shackleton-rim", "source": "LOLA 5 m/pix ...", "max_range_km": 6.258,
           "max_obstruction_deg": 9.4281, "max_obstruction_azimuth_deg": 236.0, "...": "..."},
  "series": [{"site_id": "shackleton-rim", "timestamp_utc": "2026-12-01T00:00:00Z",
              "sun": {"azimuth_deg": 75.799377, "elevation_deg": 1.524114, "range_km": 147553095.89},
              "earth": {"azimuth_deg": 162.397841, "elevation_deg": -1.820125, "range_km": 376568.371}}]
}
```

- Omitting `window` with a `start`/`stop` range selects the window that contains
  it; a bare request returns the initial window.
- Omitting `start`/`stop` returns the stored hourly records unchanged.
- Values are geometry only. Nothing in the payload claims a body is visible.

## The field contract

| Field | Type | Meaning |
| --- | --- | --- |
| `site_id` | string | Candidate id; always the same point as `data/demo/sites.json` |
| `timestamp_utc` | string | ISO-8601 UTC with `Z` |
| `sun` / `earth` | object | One body |
| `.azimuth_deg` | float | Degrees clockwise from local lunar north, `[0, 360)` |
| `.elevation_deg` | float | Degrees above the local horizontal, airless, no terrain |
| `.range_km` | float (optional) | Observer-target range; omitted when Horizons did not return one |

Anything else is rejected at load time. The TypeScript interfaces
`SeriesRecord`, `SiteSeries` and `ReadinessReport` in
`frontend/src/types/api.ts` mirror this, and `npm run build` fails if they drift
from the fields the client sends.

## Limits you must carry into Phase 3

- **Radius.** Each mask stops at the nearest DEM edge (6.3–7.7 km). Obstruction
  beyond that is unknown, so the mask is a lower bound: a real skyline can only
  be higher, and a body that clears the mask can still be hidden by a massif
  20 km away.
- **Observer height.** 2 m, matching the Sun/Earth track. A different lander
  height needs a new mask: near-field angles change by `atan(Δh / distance)`.
- **Sampling.** The stored track is hourly. `sample_records` interpolates, and
  `request.interpolated` says so; the interpolation is not a new measurement.
  Sunrise/Earthrise timing needs the finer sampling Phase 3 plans.
- **Resolution.** 5 m/pixels and ~0.3 m height uncertainty: rocks and
  lander-scale roughness are not resolved.
- **Visibility is a policy.** `above_skyline` uses the body's centre; whether
  the solar disk counts partially visible, and how Earth's 0.95° radius is
  treated, stays in the visibility service (`services/horizon.py`), not here.
- **No power, no link budget.** Sun elevation is illumination geometry; Earth
  elevation is line-of-sight geometry.
