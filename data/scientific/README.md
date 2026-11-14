# Scientific datasets

Generated data lives here. Every file records its source, request, conventions
and checks, so any value can be traced back to one JPL request.

| Path | Contents | Producer |
| --- | --- | --- |
| `site_series/<site>-<window>.json` | Sun and Earth azimuth/elevation for a candidate site, one record per timestamp (`schema: lunanav.site_series.v1`) | `backend/scripts/generate_site_series.py` |
| `site_series/index.json` | Manifest: windows, expected sample counts, per-file checks and cross-check results | same |
| `ephemeris/{sun,earth}.json` | Moon-centred sub-point tables for Scientific Mode | `backend/scripts/fetch_horizons.py` |
| `horizon_masks/<site-id>.json` | LOLA terrain horizons, 360 azimuths at a 2 m observer, 5 m/pix near field + 80 m/pix to 150 km | `backend/scripts/build_site_horizon_masks.py` |
| `spice/` | Optional NAIF kernels for the SPICE provider | provided separately |

The site series and the three horizon masks are committed: the series is the
Phase 2 Task 2 deliverable, and the masks are ~10 kB each and are what makes
Scientific Mode work without re-downloading the DEMs. `ephemeris/*.json` and
`spice/` are not committed, and neither are the DEMs (`data/cache/lola_5mpp/`,
`data/cache/lola_wide/`).

```bash
cd backend
python scripts/generate_site_series.py                # live JPL Horizons, 12 requests
python scripts/generate_site_series.py --verify-only  # re-check the committed files offline
python scripts/build_site_horizon_masks.py              # masks from the cached LOLA DEMs
python scripts/build_site_horizon_masks.py --verify-only
python scripts/inspect_wide_terrain.py --download       # 80 m far-tier DEM (~181 MB)
python scripts/inspect_wide_terrain.py --verify-only
```

Formats and steps: `docs/ADAPTATION_GUIDE.md` sections 3 and 4, and
`docs/JPL_CONNECTION.md` section 2.

Terrain lives outside this folder: `data/reference/site_terrain.json` describes
the LOLA DEMs (see [docs/TERRAIN.md](../docs/TERRAIN.md)), and the DEM files are
cached under `data/cache/lola_5mpp/`.
