# Connecting LunaNav to NASA/JPL

LunaNav uses two public NASA/JPL services. Neither needs an account or API key.

| Service | What LunaNav gets from it | Used in |
| --- | --- | --- |
| **JPL Horizons** (`ssd.jpl.nasa.gov/api/horizons.api`) | Sun and Earth positions relative to the Moon (sub-solar and sub-Earth points, distances), every 30 min | "JPL live" and "Scientific" modes |
| **NASA/JPL Moon Trek** (`trek.nasa.gov/tiles`) | LOLA colour shaded relief and LROC WAC mosaic tiles | Polar map imagery and the 3D Moon |

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
LunaNav live provider (fetch + cross-check, current month):
  [ok]   sub-solar point ...; cross-check max difference {'sun': 0.0x, 'earth': 0.0x}
All checks passed. Start the app and choose 'JPL live'.
```

In the app, the **JPL** indicator in the top bar shows the same result (click it to re-check).

## 2. Use it

1. Start the backend and frontend as in the README.
2. Click **JPL live** (top right).
3. The polar map loads Moon Trek imagery. The **first** load downloads ~500 tiles and can take 30–90 s; after that it's instant from `data/cache/`.
4. Switch the map card to **3D Moon** to see the Moon lit from the Horizons Sun direction at the inspected time. Scrub the timeline to watch the light move.

### Before a demo (or flaky venue Wi-Fi)

```bash
python scripts/warm_imagery.py --months 2027-01 2027-02 2027-03
```

This caches both imagery layers and the listed Horizons months. Afterwards the app works offline for those dates.

## 3. What "JPL live" does and doesn't include

- **Included:** Sun/Earth geometry from JPL Horizons (with physical libration and light-time), real LRO imagery for orientation.
- **Not included yet:** terrain. Without LOLA horizon masks, visibility uses the flat geometric horizon. Every result says "Geometric only: terrain obstruction not applied", which **overestimates** visibility near the pole. Add masks with `scripts/build_horizon_mask.py` (see ADAPTATION_GUIDE.md §4) and the same mode starts applying them automatically.
- **Scientific** mode uses the same Horizons data but refuses to compute without a LOLA mask.
- The imagery is for orientation. Visibility numbers never come from the pictures.

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
| `backend/app/providers/horizons_format.py` | Horizons query builder and CSV parser |
| `backend/app/services/imagery.py` | Moon Trek tile cache, polar reprojection, global texture |
| `backend/app/services/jpl_status.py` | `/api/jpl/status` |
| `backend/app/core/http.py` | The only place that makes outbound requests |
| `frontend/src/features/lunar-globe/LunarGlobe.tsx` | three.js 3D Moon |
| `config/lunanav.config.json` → `jpl`, `imagery` | URLs, timeouts, tolerance, layers |

Override URLs (e.g. to route via a proxy or mirror) with `LUNANAV_HORIZONS_URL` and `LUNANAV_TREK_URL`. Move the cache with `LUNANAV_CACHE_DIR`.
