# Mission report envelope (Phase 3 Task 11, Phase 4 Task 3)

One JSON document per site and mission window that a chart, a report or a
reviewer can consume without joining four endpoints by hand.

- Code: `backend/app/services/mission_report.py`
- Endpoint: `GET /api/mission-report?site_id=<id>&window=initial|alternative`
- Tests: `backend/tests/test_mission_report.py`
- Schema string: `lunanav.mission_report.v1`, `version: 1`

## Where the numbers come from

Nothing is recalculated here. The envelope reads:

- `/api/terrain-horizon` (Task 3): terrain basis, profile summary, coverage,
  uncertainty, sample counts above and blocked by the skyline;
- `/api/phase3` (Tasks 4–6): adjusted visibility, intervals, metrics;
- `services/requirements.CHECKS` (Task 8): the same three Phase 1 checks and
  thresholds the `/api/requirements` endpoint uses.

If those numbers change, the envelope changes with them; if you want a different
number, change the module that owns it.

## Shape

| Field | Unit | Meaning |
| --- | --- | --- |
| `schema`, `version` | — | document type and format version |
| `site.site_id`, `site.name` | — | candidate identifier and display name |
| `site.latitude_deg`, `site.longitude_deg` | deg | published site coordinates, planetocentric east-positive |
| `site.elevation_m`, `site.height_m` | m | LOLA surface elevation and lander height |
| `window.key`, `window.label` | — | `initial` or `alternative` |
| `window.start_utc`, `window.stop_utc` | ISO-8601 UTC | analysis window |
| `window.step`, `window.samples` | — | stored sampling (1 h) and record count |
| `terrain.basis` / `terrain.geometric_only` | — | `terrain`/`false`, or `geometric`/`true` when no LOLA skyline exists |
| `terrain.source`, `terrain.provenance` | — | mask source string and provenance label |
| `terrain.observer_height_m` | m | eye height the mask was built with (2.0) |
| `terrain.azimuth_step_deg` | deg | skyline sampling (1°) |
| `terrain.max_obstruction_deg`, `..._azimuth_deg` | deg | highest skyline angle and where it is |
| `terrain.coverage` | m, km, deg | near/far pixel sizes and ranges, curvature model |
| `terrain.uncertainty` | m, deg | pixel sizes, observer height uncertainty, unmodelled effects |
| `terrain.sun_above_skyline`, `terrain.sun_blocked_by_terrain` | samples | Sun samples above the skyline, and samples a flat horizon would have counted |
| `terrain.earth_above_skyline`, `terrain.earth_blocked_by_terrain` | samples | same for Earth |
| `sunlight.availability_percent` | % | Sun above the skyline over the window |
| `sunlight.visible_hours` | h | total measured sunlight |
| `sunlight.darkness_hours` | h | total time the Sun is below the skyline, i.e. window minus sunlight |
| `sunlight.longest_sunlight_hours` | h | longest single sunlight interval |
| `sunlight.longest_darkness_hours` | h | longest Sun blackout (window-limited, `null` if none) |
| `sunlight.windows[]` | ISO-8601 UTC, h | each sunlight interval (`start_utc`, `end_utc`, `duration_hours`) |
| `earth.visibility_percent`, `.visible_hours`, `.longest_visible_hours`, `.longest_blackout_hours`, `.windows[]` | % / h | direct line of sight past terrain, not a link budget |
| `simultaneous_visibility.availability_percent`, `.visible_hours`, `.longest_gap_hours`, `.windows[]` | % / h | sunlight and Earth at once |
| `metrics[]` | per metric | the full metric registry: `id`, `value`, `unit`, `censored`, labels |
| `requirements.source` | — | `config/lunanav.config.json -> requirements` |
| `requirements.satisfied` | — | `true`, `false`, or `null` when any check is `unknown` |
| `requirements.checks[].status` | — | `met`, `not_met`, `unknown` — `unknown` is **not** a pass |
| `requirements.checks[].threshold`, `.value`, `.comparison`, `.censored` | % / h | measured value, target, direction, and whether the window truncated it |
| `model.visibility_type`, `.status` | — | `terrain-adjusted geometry`, `calculated` |
| `model.ephemeris`, `.terrain`, `.sampling`, `.time` | — | provenance labels |
| `model.units` | — | one-line unit reminder |
| `sources.series_endpoint`, `.terrain_endpoint` | — | where each block came from |
| `notes[]` | — | what the document does not claim |

Intervals are `{start_utc, end_utc, duration_hours}`; edges are interpolated
between hourly samples, so their timing is finer than 1 h but is not a new
measurement.

## Reproducibility

`mission_report_json()` serialises with sorted keys and no wall-clock field, so a
re-run on the committed data produces the same bytes. The test suite asserts
that, and that a `json.loads` round-trip equals the dict.

```bash
curl 'http://localhost:8000/api/mission-report?site_id=shackleton-rim&window=initial'
```

## Limits

Geometry, not a mission verdict: Sun above terrain is not available power, Earth
above terrain is not a working link, `unknown` is not a pass, and no ranking or
recommendation is made. Errors share the usual shape `{code, message, details}`:
unknown site 404, unknown window 422, missing committed data 503.
