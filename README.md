# LunaNav

A lunar landing-site visibility explorer, built as a foundation for the NASA Space Apps Challenge 2026 problem *Lunar Landing Site Navigator*.

Pick a site near the lunar south pole (or click anywhere on the polar map), choose a landing date and mission length, and LunaNav shows when the Sun and Earth are above the **terrain** horizon, not just above a flat one. You can compare two site/date scenarios side by side, or see what changes if a landing slips.

Every result carries a provenance label. Out of the box the app runs in **Demo Mode**: real (approximate) celestial geometry over **synthetic** terrain skylines. Scientific Mode refuses to compute until real Horizons and LOLA-derived data are loaded.

## Quick start

Requirements: Python 3.11+ and Node 20+.

```bash
# 1. Backend (http://localhost:8000, API docs at /docs)
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 2. Frontend (http://localhost:5173), in a second terminal
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to the backend, so no CORS or URL configuration is needed locally. Or run both with `./scripts/dev.sh`.

### Tests

```bash
cd backend && pytest          # 57 tests: coordinates, time, ephemeris vs Meeus, horizon logic,
                              # intervals, API contract, comparison, rescheduler, mode switching
cd frontend && npm test       # projection round-trips
cd frontend && npm run build  # strict TypeScript + production bundle
```

## What it does

| View | What you can do |
| --- | --- |
| **Mission planner** | Polar map with 5 example sites and click-to-pick custom coordinates; landing time (UTC) and duration; saved candidate dates; Sun/Earth elevation, azimuth, terrain skyline, clearance, time to sunset/Earthset; 360° horizon panorama; scrubbable visibility timeline; mission summary metrics. |
| **Compare scenarios** | Two site/date/duration scenarios side by side with every metric, change highlighting, aligned visibility bands, and data-derived trade-off statements. |
| **Reschedule a mission** | Same site and duration, original vs proposed date: changes in sunlight, Earth visibility, simultaneous visibility and longest blackouts. |
| **Data & methodology** | Calculation pipeline, providers per mode and their availability, which physical effects each includes, conventions, and what results do not mean. |

## Data honesty, in short

- **Demo Mode** = analytic ephemeris (Meeus, ~0.05–0.1° accuracy, verified against published worked examples) + **synthetic** horizon skylines. Labelled "Demonstration data: synthetic terrain, not real lunar conditions" on every view.
- **Custom coordinates** in Demo Mode have no skyline, so they use the flat geometric horizon and are labelled "Geometric only".
- **Scientific Mode** requires `data/scientific/ephemeris/{sun,earth}.json` (from JPL Horizons) and `data/scientific/horizon_masks/*.json` (from LOLA DEMs). If either is missing, the API returns `503 SCIENTIFIC_DATA_UNAVAILABLE` and the UI says so. Nothing is substituted.
- Sun visibility is never presented as power; Earth visibility is never presented as a comms link.
- Comparisons describe differences. They do not rank or recommend sites.
- Demo site coordinates are approximate points near named features, not official Artemis region definitions.

## Repository layout

```text
lunanav/
├── config/lunanav.config.json   # central config: date range, providers per mode, datasets, feature flags
├── backend/
│   ├── app/
│   │   ├── core/        # settings, UTC time, lunar coordinates, errors
│   │   ├── models/      # Pydantic API contracts (schemas.py)
│   │   ├── providers/   # EphemerisProvider + LunarTerrainProvider implementations, registry
│   │   ├── services/    # HorizonCalculator, VisibilityCalculator, intervals, metrics, comparison
│   │   └── api/         # FastAPI routes (thin)
│   ├── scripts/         # generate demo data, fetch Horizons, validate ephemeris, build LOLA masks
│   └── tests/
├── frontend/src/
│   ├── features/        # lunar-map, mission-planner, visibility, comparison, rescheduler, methodology
│   ├── components/      # shared UI (shadcn-style primitives, provenance, errors, nav)
│   ├── services/api.ts  # typed API client
│   ├── types/api.ts     # mirror of backend schemas
│   ├── hooks/           # app state, data fetching
│   └── config/          # feature-flag resolution, presentation constants
├── data/
│   ├── demo/            # sites.json, horizon_masks.json (synthetic)
│   └── scientific/      # empty until real data is added
└── docs/
    ├── ARCHITECTURE.md
    ├── METHODOLOGY.md
    └── ADAPTATION_GUIDE.md   # read this when NASA publishes new details
```

## Status of each part

| Part | Status |
| --- | --- |
| Analytic ephemeris, topocentric geometry, horizon obstruction, interval detection, metrics, comparison, rescheduler | Working, tested |
| Demo terrain skylines | Working, **synthetic by design** |
| Horizons table provider + parser + fetch script | Working against fixtures; not run against live Horizons in this repo (no network in the build environment) |
| LOLA horizon-mask builder (DEM ray-march with curvature) | Algorithm working and tested on synthetic DEMs; GeoTIFF script needs `rasterio` and a real LOLA product |
| SPICE provider | Implemented, **not validated**: needs `spiceypy` + kernels |
| Imagery basemap | Not bundled. Map shows graticule and approximate crater outlines; a tile layer in the same projection can be enabled via `VITE_LUNAR_TILE_URL` |
| 3D terrain, power model, link budget, rankings, AI explanations, report export | Extension points and feature flags only |

## API

`GET /api/config`, `GET /api/sites`, `GET /api/providers?mode=`, `GET /api/horizon-mask`, `POST /api/scenario`, `POST /api/snapshot`, `POST /api/compare`, `POST /api/reschedule`. Interactive docs at `http://localhost:8000/docs`. Errors share one shape: `{code, message, details}`.

## Further reading

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): layers, data flow, extension points
- [docs/METHODOLOGY.md](docs/METHODOLOGY.md): the math, conventions, accuracy, what is and isn't modelled
- [docs/ADAPTATION_GUIDE.md](docs/ADAPTATION_GUIDE.md): how to respond when NASA releases more information
