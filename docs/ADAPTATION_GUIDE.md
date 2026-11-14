# Adaptation guide: updating LunaNav when NASA publishes more information

Additional challenge details are expected around **November 4–5, 2026**. This guide is a triage checklist: find the kind of change, then follow the steps. Most changes touch one config entry and one module.

## 0. First hour after the release

1. Read the new material and list every **dataset**, **constraint**, **metric**, **date range**, **site/region** and **deliverable** it mentions.
2. Map each item to a section below.
3. Check whether any official landing regions or coordinates are given; update `data/demo/sites.json` first, because everything else is demonstrated against it.
4. Decide what moves to Scientific Mode now vs. stays Demo for the hackathon. Keep the provenance labels honest either way.
5. Run `cd backend && pytest` after every step.

## 1. New or changed date range

Edit `config/lunanav.config.json` → `simulation.supported_start_utc` / `supported_end_utc` (and `default_landing_utc`). Both backend and frontend read it. Tabulated providers also enforce their own table range; the API reports the intersection.

If you move `default_landing_utc` or `default_duration_hours`, update `mission.landing_dates.initial` and `mission.duration_days` to match: the loader rejects a config where they disagree, so the default scenario can never drift from the defined mission.

If the window extends past 2030, also reconsider the fixed UTC→TT offset in `core/timeutil.py` (fine unless a leap second is announced).

## 2. New or official landing sites / regions

- **Points:** edit `data/demo/sites.json` (id, name, lat, lon east-positive, description, `coordinate_note`, `source`). Then `python scripts/generate_demo_data.py` to give each a synthetic skyline, or add real masks (section 4).
- **Regions (polygons):** add a `regions.json` alongside, a `Region` schema in `models/schemas.py`, a `GET /api/regions` route, and draw polygons in `features/lunar-map/LunarMap.tsx` using `toLeaflet()` for every vertex. Do not draw lat/lon directly; the map is stereographic.
- Analyses already accept arbitrary coordinates, so no service changes are needed.

## 3. NASA provides ephemeris data

| Format | Steps |
| --- | --- |
| Horizons access (default plan) | Already live: JPL and Scientific modes fetch from Horizons on demand (see docs/JPL_CONNECTION.md). For a frozen offline table instead, `python scripts/fetch_horizons.py ...` and set `providers.scientific.ephemeris` to `"horizons_table"`. |
| SPICE kernels | Put kernels in `data/scientific/spice/`, `pip install spiceypy`, adjust `KERNELS` in `providers/ephemeris_spice.py`, set `providers.scientific.ephemeris` to `"spice"` in config. Validate with `validate_ephemeris.py` (swap the provider). |
| Pre-computed Sun/Earth az/el per site | Write a provider that returns sub-points, or (simpler) a terrain-independent `SiteSkyProvider` and bypass `topocentric_az_el` in `VisibilityCalculator._geometry`. Keep the same `ScenarioResult` output. |
| Their own CSV/JSON of sub-points | Convert to the `{times_utc, sub_lat_deg, sub_lon_deg, distance_km}` format in `providers/ephemeris_tabulated.py` and drop into `data/scientific/ephemeris/`. |

## 4. NASA provides terrain data

| Format | Steps |
| --- | --- |
| LOLA DEM GeoTIFF (polar stereographic) | `pip install rasterio`; `python scripts/build_horizon_mask.py --dem <file> --site-id <id> --lat .. --lon ..` for each site. Check the CRS printout and height units (`--scale 1000` if km). |
| Pre-computed horizon masks | Write JSON `{site_id, latitude_deg, longitude_deg, source, azimuth_deg[], elevation_deg[]}` into `data/scientific/horizon_masks/`. Azimuth 0–<360 clockwise from north, elevation in degrees. |
| Illumination/visibility rasters (% time lit, etc.) | New `LunarTerrainProvider` method or a separate provider; expose as a new metric category or map layer. These are summaries; they don't replace time-resolved masks. |
| New Moon Trek layer | Add an entry under `imagery.layers` in the config (Trek path, extensions, max zoom, credit). It appears in the map's Imagery picker and the 3D globe. |
| Imagery / hillshade tiles from elsewhere | Tile them on the same south-polar-stereographic km grid (origin at the pole, y up, 0° at top) and set `VITE_LUNAR_TILE_URL` (+ `VITE_LUNAR_TILE_ATTRIBUTION`). For other projections, use Proj4Leaflet and update `features/lunar-map/projection.ts`. |

Scientific Mode terrain turns on when at least one mask exists. Custom coordinates without a mask stay unavailable in Scientific Mode by design (within 0.25 km match tolerance, `MATCH_TOLERANCE_KM`).

## 5. New metric or evaluation criterion

```python
# backend/app/services/metrics.py
register(MetricDef(
    id="sun_visible_first_72h_hours", label="Sunlight in first 72 h", unit="h", category="sun",
    description="Sun-visible time during the first 72 h after landing.",
    availability_direction=1,
    fn=lambda c: (sum(min(e, c.window[0] + 72*3600) - s
                      for s, e in c.spans["sun_visible"] if s < c.window[0] + 72*3600) / 3600, False),
))
```

It appears automatically in the planner summary, the comparison table and the API. Add its id to `HEADLINE_METRICS` in `services/comparison.py` to feature it in the rescheduler, and add a test.

## 6. New mission constraint (slope, hazards, thermal, comms windows, minimum sunlight)

1. Put data access in a provider (e.g. `surface_elevation_m` on a DEM-backed terrain provider).
2. Put logic in a new service, e.g. `services/constraints.py` returning `ConstraintResult{id, label, satisfied: bool | None, value, threshold, provenance}`.
3. Add `constraints: list[ConstraintResult]` to `ScenarioResult` (optional field, so the frontend keeps working).
4. Render with a new component in `features/visibility/` or a new `features/constraints/` folder.
5. Gate with a new flag in `config/lunanav.config.json → features` until it's solid.

Thresholds (e.g. "≥ 70% sunlight") should come from NASA's text and be stored in config, not hardcoded.

## 7. New visualization

Create a component that takes `ScenarioResult` (or `ComparisonResult`) as props, export it from the feature's `index.ts`, and place it on a page. No other component needs to change. Use `CHART_COLORS` from `config/app.ts` so Sun/Earth/both colors stay consistent.

## 8. New feature flagged as experimental

Add `"my_feature": false` to `features` in the config. Read it with `useApp().features.my_feature`. Developers can enable it locally without touching the config via `?ff=my_feature:on` (persisted in localStorage; `?ff=my_feature:off` to clear).

## 9. Changes to deliverables or judging

| If they ask for | Start from |
| --- | --- |
| Exportable report | `ScenarioResult` / `ComparisonResult` JSON is self-describing (includes provenance). Add `GET /api/scenario/report` producing Markdown/PDF; flag `experimental_report_export`. |
| Site ranking | Compute `ScenarioResult` for each site, score with **explicit, user-visible weights**, and show provenance next to every score. Flag `experimental_site_ranking`. |
| Power estimate | New service from `sun_disk_fraction` and Sun az/el with a stated panel model. Keep it separate from visibility; flag `experimental_power_model`. |
| Communications analysis | New service from Earth az/el, mask, and stated antenna/ground-station assumptions; flag `experimental_comm_link_budget`. |
| 3D view | Implement `LunarMapProps` (features/lunar-map/types.ts). |
| Different body or hemisphere | `projection.ts` is south-polar; add a north-polar variant and choose by latitude. Backend math is global already. |

## 10. Keeping the API contract in sync

When you change `backend/app/models/schemas.py`, mirror the change in `frontend/src/types/api.ts` and run `npm run build` (strict TypeScript catches missing fields). Prefer **adding optional fields** over changing existing ones so older UI code keeps working mid-hackathon.

## 11. Honesty checklist before demoing

- [ ] Mode toggle shows the mode you intend to demo.
- [ ] Provenance callout on the planner reads correctly for the data you loaded.
- [ ] Any site whose coordinates came from NASA has `source` set; others still say "approximate".
- [ ] Nothing in narration equates sunlight with power or Earth visibility with a working link.
- [ ] `pytest` and `npm run build` pass.
