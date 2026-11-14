# Connecting LunaNav to NASA/JPL

LunaNav uses two public NASA/JPL services. Neither needs an account or API key.

| Service | What LunaNav gets from it | Used in |
| --- | --- | --- |
| **JPL Horizons** (`ssd.jpl.nasa.gov/api/horizons.api`) | Sun and Earth positions relative to the Moon (sub-solar and sub-Earth points, distances), every 30 min | "JPL live" and "Scientific" modes |
| **NASA/JPL Moon Trek** (`trek.nasa.gov/tiles`) | LROC WAC mosaic, LOLA colour shaded relief and LOLA elevation tiles | Polar map, whole-Moon map, and the 3D Moon's imagery and shape |

The **LunaNav backend** talks to JPL, not your browser. So "connecting" just means the computer running `uvicorn` can reach those two addresses.

## 1. Check the connection (30 seconds)

```bash
cd backend
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # adds Pillow for imagery
python scripts/check_jpl.py
```

Expected:

```text
JPL Horizons: https://ssd.jpl.nasa.gov/api/horizons.api
  [ok]   HTTP 200, 2 rows, sub-Earth lon ...°, sub-solar lon ...°
NASA/JPL Moon Trek: https://trek.nasa.gov/tiles
  [ok]   lola_shade: tile received
  [ok]   wac: tile received
  [ok]   lola_dem: tile received
LunaNav live provider (fetch + cross-check, current month):
  [ok]   sub-solar point ...; cross-check max difference {'sun': 0.0x, 'earth': 0.0x}
All checks passed. Start the app and choose 'JPL live'.
```

In the app, the **JPL** indicator in the top bar shows the same result (click it to re-check).

## 2. Use it

1. Start the backend and frontend as in the README.
2. LunaNav opens in **JPL live** (top right). To open in another mode, set `mode.default` in the config or `LUNANAV_MODE`.
3. The polar map shows a quick preview, then sharpens. The **first** sharp load downloads ~500 tiles and can take 30–90 s; after that it's instant from `data/cache/`.
4. **Whole Moon** is the 2D map of the full surface. Scroll to zoom; tiles load as needed. The shaded area is the night side at the inspected time, on a sphere with no terrain.
5. **3D Moon** opens on the sunlit side, lit from the Horizons Sun direction at the inspected time. Scrub the timeline to watch the light move, or choose **Even light** to inspect the far side of the terminator.

### Before a demo (or flaky venue Wi-Fi)

```bash
python scripts/warm_imagery.py --months 2027-01 2027-02 2027-03
```

This caches both imagery layers and the listed Horizons months. Afterwards the app works offline for those dates.

### Live sunlight and crater names

**Sun now** (the default, under each map view) lights the views from the Sun's position at this moment, from `GET /api/sky/now`, refreshed each minute. Moving the timeline switches to **Mission time**, which lights them for the inspected time.

Live sunlight moves the day/night boundary and the lighting. It can't move shadows already in the LRO mosaic, which were recorded during LRO's mapping. Near the poles, treat the shaded night side as today's sunlight and the black crater interiors as the mosaic.

Crater names, centres and diameters come from the IAU Gazetteer of Planetary Nomenclature (`data/reference/moon_craters.json`). Rebuild them with `python scripts/fetch_craters.py`.

### Sun and Earth from a surface site (Phase 2, Task 1)

The app's scenario maths starts from Moon-centred sub-points. Surface geometry needs a different Horizons query: an **observer table for someone standing on the Moon** (`CENTER='coord@301'`, `COORD_TYPE='GEODETIC'`, `QUANTITIES='4,20'`, airless), which returns apparent azimuth and elevation directly.

```bash
cd backend
python scripts/horizons_site.py --site shackleton-rim \
    --start 2026-12-01T00:00Z --stop 2026-12-08T00:00Z --step "1 h" \
    --out ../data/scientific/site_series/shackleton-rim-sample.json
```

It prints the series, compares every sample with LunaNav's independent analytic model, and writes one record per timestamp (`site_id`, `timestamp_utc`, `sun`, `earth`, each with `azimuth_deg` and `elevation_deg`) — the structure Task 2 builds on. Custom coordinates use `--lat`, `--lon` and `--elevation-m`. Against the live service on 14 Nov 2026 the two paths agreed to 0.020° in elevation and 0.017° in azimuth over 24 h, so the frame, longitude sense and units are confirmed rather than assumed.

Azimuth is degrees clockwise from lunar north; elevation is degrees above the local horizontal, airless and terrain-free, so it is comparable with the terrain skyline but does not include it. Unusable responses raise `JplUnavailableError` (the API's `JPL_UNAVAILABLE`) instead of returning a short or filled-in series.

For the whole Phase 2 Task 2 dataset — all three candidates × both 7-day windows at 1 h — run `python scripts/generate_site_series.py`; `--verify-only` re-checks the committed files without the network.

## 3. What "JPL live" does and doesn't include

- **Included:** Sun/Earth geometry from JPL Horizons (with physical libration and light-time), real LRO imagery for orientation, and a 3D shape from LOLA elevation.
- **The 3D shape is for display.** It comes from 8-bit map tiles, smoothed and exaggerated 3x, and assumes those tiles span LOLA's ~19.9 km range. Terrain does not cast shadows on the globe. Don't measure from it.
- **Terrain:** the three mission candidates have committed LOLA horizon masks (`data/scientific/horizon_masks/`, built by `scripts/build_site_horizon_masks.py`), so their visibility is terrain-adjusted. Any other location still gets "Geometric only: terrain obstruction not applied", which **overestimates** visibility near the pole; build a mask with `scripts/build_horizon_mask.py` (see ADAPTATION_GUIDE.md §4) and the same mode applies it automatically.
- **Scientific** mode uses the same Horizons data but refuses to compute without a LOLA mask.
- The imagery and 3D shape are for orientation. Visibility numbers never come from them.

## 4. Safety checks built in

- Every Horizons download is compared with LunaNav's independent built-in model. Agreement is expected to within ~0.1°. If they differ by more than 0.5° (`jpl.horizons_crosscheck_tolerance_deg`), the download is **rejected and not cached**, and the error says why (e.g. a longitude-sign convention mismatch, with the exact config fix).
- If JPL can't be reached, LunaNav shows "NASA/JPL data could not be used" and never quietly falls back to the built-in model.
- Missing imagery tiles stay transparent; nothing is painted in.

## 5. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Connection refused`, `timed out`, `Name or service not known` | No internet from the backend machine, or DNS blocked. Try `curl -I https://ssd.jpl.nasa.gov` in the same terminal. |
| `CERTIFICATE_VERIFY_FAILED` | Corporate/school network inspecting TLS. Point Python at your organisation's CA bundle: `export SSL_CERT_FILE=/path/to/ca.pem` (Windows: `set SSL_CERT_FILE=...`) and restart. On macOS python.org installs, run *Install Certificates.command* once. |
| `Tunnel connection failed: 403` / proxy errors | A proxy is blocking JPL. Ask for `ssd.jpl.nasa.gov` and `trek.nasa.gov` to be allowed, or run from another network. Python honours `HTTPS_PROXY`. |
| `JPL Horizons answered HTTP 503` | Horizons is busy or in maintenance. Wait a few minutes; cached months keep working. |
| `API ERROR: ... query parameter was not recognized` | A hand-built Horizons URL is missing a parameter. Use `scripts/horizons_site.py` or `build_site_query()`, which send the verified parameter set. |
| `disagree with the independent cross-check ... set jpl.horizons_lon_sign to -1` | Change that value in `config/lunanav.config.json`, restart, and delete `data/cache/horizons/` if anything was cached. |
| Imagery shows "Imagery unavailable" | Run `check_jpl.py`. If only Moon Trek fails, JPL mode calculations still work; pick "Imagery: None". |
| 3D Moon says "needs WebGL" | Your browser has hardware acceleration off (Chrome: Settings, System, "Use graphics acceleration when available"), or a managed laptop/VM blocks WebGL. The polar map works without it. Test at https://get.webgl.org. |
| 3D Moon shows a grey sphere with "No Sun position" | The calculation failed (the notice says why, usually Horizons unreachable). Switch to Demo data to see real-geometry lighting from the built-in model. |
| 3D Moon says "The 3D viewer stopped" / "could not be downloaded" | The dev server restarted after an update. Reload the page. |
| Imagery error "returned no data … layer path may be wrong" | That Moon Trek layer name has changed. Pick the other layer in the Imagery dropdown, or update its `path` in the config. |
| A Moon Trek layer always 404s | Trek renamed or retired it. Find the current layer in the Moon Trek portal (trek.nasa.gov/moon) and update `imagery.layers.<id>.path` in the config. |

## 6. Where the code lives

| File | Role |
| --- | --- |
| `backend/app/providers/ephemeris_horizons_live.py` | Horizons fetch, monthly cache, cross-check |
| `backend/app/providers/horizons_format.py` | Horizons query builder and CSV parser (Moon-centred sub-points) |
| `backend/app/providers/horizons_site.py` | Topocentric Sun/Earth azimuth and elevation for a lunar site (Phase 2) |
| `backend/scripts/horizons_site.py` | Fetches a site's series and writes the Task 2 JSON records |
| `backend/scripts/fetch_craters.py` | Rebuilds the IAU crater catalogue |
| `backend/app/services/site_data.py` | Phase 2 Task 6 data access: one record contract, interpolation inside a stored window, LOLA mask loading and clearance |
| `backend/app/services/imagery.py` | Moon Trek tile cache, polar reprojection, global texture, relief maps |
| `backend/app/services/jpl_status.py` | `/api/jpl/status` |
| `backend/app/core/http.py` | The only place that makes outbound requests |
| `frontend/src/features/lunar-globe/LunarGlobe.tsx` | three.js 3D Moon |
| `frontend/src/features/lunar-map/GlobalMoonMap.tsx` | Leaflet whole-Moon 2D map |
| `config/lunanav.config.json` → `jpl`, `imagery` | URLs, timeouts, tolerance, layers |

Override URLs (e.g. to route via a proxy or mirror) with `LUNANAV_HORIZONS_URL` and `LUNANAV_TREK_URL`. Move the cache with `LUNANAV_CACHE_DIR`.
