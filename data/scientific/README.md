# Scientific datasets

Generated data lives here. Every file records its source, request, conventions
and checks, so any value can be traced back to one JPL request.

| Path | Contents | Producer |
| --- | --- | --- |
| `site_series/<site>-<window>.json` | Sun and Earth azimuth/elevation for a candidate site, one record per timestamp (`schema: lunanav.site_series.v1`) | `backend/scripts/generate_site_series.py` |
| `site_series/index.json` | Manifest: windows, expected sample counts, per-file checks and cross-check results | same |
| `ephemeris/{sun,earth}.json` | Moon-centred sub-point tables for Scientific Mode | `backend/scripts/fetch_horizons.py` |
| `horizon_masks/<site-id>.json` | LOLA terrain horizons | `backend/scripts/build_horizon_mask.py` |
| `spice/` | Optional NAIF kernels for the SPICE provider | provided separately |

The site series is committed because it is the Phase 2 Task 2 deliverable.
`ephemeris/*.json` and `horizon_masks/*.json` stay gitignored: they are large
and rebuilt from NASA sources.

```bash
cd backend
python scripts/generate_site_series.py                # live JPL Horizons, 12 requests
python scripts/generate_site_series.py --verify-only  # re-check the committed files offline
```

Formats and steps: `docs/ADAPTATION_GUIDE.md` sections 3 and 4, and
`docs/JPL_CONNECTION.md` section 2.

Terrain lives outside this folder: `data/reference/site_terrain.json` describes
the LOLA DEMs (see [docs/TERRAIN.md](../docs/TERRAIN.md)), and the DEM files are
cached under `data/cache/lola_5mpp/`.
