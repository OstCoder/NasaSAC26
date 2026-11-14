# LunaNav architecture

## Principles

1. **Science is separate from presentation.** All calculations live in `backend/app/services` and `backend/app/providers`. The frontend only renders API responses; it never computes visibility.
2. **Data enters through two interfaces.** `EphemerisProvider` and `LunarTerrainProvider` are the only places scientific inputs come from. Swapping a dataset means writing one class.
3. **No silent substitution.** A provider that cannot answer raises `DataUnavailableError`. The API turns it into `503 SCIENTIFIC_DATA_UNAVAILABLE`.
4. **Every result is labelled.** `ScenarioResult` and `Snapshot` include a `Provenance` block (mode, weakest data level, providers, effects included, caveats).
5. **Config over code.** Date range, providers per mode, dataset paths and feature flags are in `config/lunanav.config.json`.
6. **Locations are coordinates.** Predefined sites are a convenience. Every endpoint accepts `{latitude_deg, longitude_deg}`.

## Data flow

```text
                  config/lunanav.config.json
                              │
     ┌────────────────────────┴───────────────────────┐
     ▼                                                ▼
providers/registry.py ──► ProviderBundle(mode, ephemeris, terrain)
                              │
LocationInput ─► SiteRepository.resolve() ─► ResolvedLocation
                              │
                              ▼
               services/visibility.py  VisibilityCalculator
                 1. ephemeris.sub_points(sun|earth, times)
                 2. core/coords.topocentric_az_el()   ← parallax, ENU frame
                 3. terrain.horizon_mask()  → HorizonMask
                 4. services/horizon.HorizonCalculator.evaluate()
                       clearance = elevation − skyline(azimuth)
                 5. services/intervals: edges by interpolated sign change,
                       intersect / complement / union
                 6. services/metrics: registry of MetricDef → MetricValue[]
                 7. services/provenance.build_provenance()
                              │
                              ▼
            ScenarioResult / Snapshot  (models/schemas.py)
                              │
            services/comparison.py  ScenarioComparisonService
                compare_results(a, b) → deltas, trade-offs, comparability
                reschedule()          → same, with headline metrics
                              │
                              ▼
                   api/routes.py (FastAPI)  ──JSON──►  frontend
```

## Backend modules

| Module | Responsibility |
| --- | --- |
| `core/settings.py` | Loads central config; env overrides `LUNANAV_MODE`, `LUNANAV_CONFIG`, `LUNANAV_ROOT`. |
| `core/timeutil.py` | Strict UTC parsing (naive timestamps rejected), time grids, UTC→TT. |
| `core/coords.py` | Coordinate validation, body-fixed vectors, ENU azimuth/elevation with parallax. |
| `core/errors.py` | Typed domain errors with HTTP status and stable `code`. |
| `models/schemas.py` | All request/response contracts. |
| `providers/base.py` | `EphemerisProvider`, `LunarTerrainProvider`, `HorizonMask`, `SubPointTable`. |
| `providers/ephemeris_analytic.py` | Meeus analytic Sun/Moon + optical libration. |
| `providers/ephemeris_tabulated.py` | Static Horizons tables + shared interpolation. |
| `providers/ephemeris_horizons_live.py` | Live Horizons: monthly fetch, disk cache, cross-check against the analytic model. |
| `providers/ephemeris_spice.py` | NAIF SPICE (integration point, unvalidated). |
| `providers/horizons_format.py` | Horizons query builder and CSV parser. |
| `providers/terrain.py` | Synthetic, LOLA-mask and flat horizon providers. |
| `providers/registry.py` | Config id → provider factory; per-mode bundles. |
| `services/horizon.py` | `HorizonCalculator`, solar-disk fraction, DEM → horizon-mask ray-march. |
| `services/intervals.py` | Interval detection and algebra. |
| `services/metrics.py` | Metric registry. |
| `services/visibility.py` | `VisibilityCalculator`: scenario series, snapshot, event refinement. |
| `services/comparison.py` | `ScenarioService`, `ScenarioComparisonService`. |
| `services/provenance.py` | Builds the `Provenance` block: mode, weakest data level, providers used, effects included, caveats. |
| `services/sites.py` | Site catalogue: candidate resolution against the mission, PSR-proximity enrichment, elevation cross-check. |
| `services/psr.py` | PSR boundary catalogue: nearest-PSR geometry and within-radius queries. |
| `services/requirements.py` | Requirement check: one scenario measured against the config thresholds, three-state verdict, PSR preference reported but never scored. |
| `services/imagery.py` | Moon Trek tile cache, reprojection to the polar map grid, global texture. |
| `services/jpl_status.py` | Live reachability of Horizons and Moon Trek. |
| `core/http.py` | Single outbound HTTP function (mocked in tests). |

## Frontend modules

| Path | Responsibility |
| --- | --- |
| `types/api.ts` | Mirror of `models/schemas.py`. |
| `services/api.ts` | The only place that calls `fetch`. Typed `ApiError` with backend `code`. |
| `hooks/useAppContext.tsx` | Boot (config + sites), mode, feature flags, scenario drafts A/B. |
| `hooks/useApiResource.ts` | Debounced, abortable fetch keyed by request body. |
| `features/lunar-map` | `LunarMapProps` contract + 2D south-polar-stereographic Leaflet implementation. |
| `features/visibility` | `SnapshotPanel`, `HorizonPanorama`, `VisibilityTimeline`, `IntervalBands`, `MetricsTable`. Each takes API types only. |
| `features/mission-planner` | `ScenarioEditor` (shared) and the planner page. |
| `features/comparison` | `DeltaTable`, `PairedBands`, `TradeoffNotes`, page. |
| `features/rescheduler` | Rescheduling workflow, reusing comparison components. |
| `features/lunar-globe` | three.js 3D Moon (lazy-loaded), lit from the snapshot's sub-solar point. |
| `features/methodology` | Provider/effects/conventions page driven by `/api/providers`. |
| `lib/` | `format.ts` (durations, percentages, coordinates) and `utils.ts` (the `cn` class-name helper). |
| `components/` | Shared UI: provenance badge and legends, JPL status, error notice/boundary, layout and nav, and the shadcn-style primitives in `ui/`. |
| `config/` | `features.ts` (server flags + local overrides via `?ff=flag:on`) and `app.ts` (chart colours, tile URL overrides). |

## Extension points

| Want to add | Where | Notes |
| --- | --- | --- |
| New ephemeris source | `providers/` class implementing `EphemerisProvider`, register in `providers/registry.py`, set id in config | Return sub-points + distances in the Moon ME frame. |
| New terrain source | `LunarTerrainProvider` with `horizon_mask()` | Raise `DataUnavailableError` when you can't answer. |
| New metric | `services/metrics.py` → `register(MetricDef(...))` | Appears in summary, comparison and (if listed in `HEADLINE_METRICS`) rescheduler. |
| New constraint (slope, hazard, thermal) | New provider method (e.g. `surface_elevation_m`) + a metric or a separate `ConstraintService` | Add a schema field to `ScenarioResult` rather than overloading metrics. |
| Solar power model | New service consuming `series.sun_disk_fraction` + sun az/el; gate behind `experimental_power_model` | Keep power separate from visibility. |
| Comm link analysis | New service consuming Earth az/el + mask; gate behind `experimental_comm_link_budget` | Include antenna and ground-station assumptions explicitly. |
| Candidate ranking | Service over many `ScenarioResult`s with explicit, user-visible weights; flag `experimental_site_ranking` | Never rank without stating the criteria. |
| 3D terrain view | Implement `LunarMapProps` and export from `features/lunar-map/index.ts`; flag `experimental_3d_terrain` | |
| Report export | Serialize `ScenarioResult`/`ComparisonResult` (already self-describing incl. provenance); flag `experimental_report_export` | |
| AI explanations | Feed `ComparisonResult.deltas` + provenance into a prompt; flag `experimental_ai_explanations` | Must quote provenance caveats. |

## Error contract

| Code | HTTP | Meaning |
| --- | --- | --- |
| `INVALID_INPUT` | 422 | Bad coordinates, naive timestamp, duration out of bounds, schema violation |
| `OUT_OF_SUPPORTED_RANGE` | 422 | Window outside config range or provider range; `details` holds the supported range |
| `UNKNOWN_SITE` | 404 | `site_id` not in catalogue |
| `JPL_UNAVAILABLE` | 503 | Horizons/Moon Trek unreachable, errored, or failed the cross-check |
| `SCIENTIFIC_DATA_UNAVAILABLE` | 503 | Required provider/dataset missing; `message` names the missing file |
