# LunaNav

A lunar landing-site visibility explorer, built as a foundation for the NASA Space Apps Challenge 2026 problem *Lunar Landing Site Navigator*.

Pick a site near the lunar south pole (or click anywhere on the polar map), choose a landing date and mission length, and LunaNav shows when the Sun and Earth are above the **terrain** horizon, not just above a flat one. You can compare two site/date scenarios side by side, or see what changes if a landing slips.

Every result carries a provenance label. Three modes:

- **JPL live** (default): Sun/Earth positions fetched live from **NASA JPL Horizons**, plus LRO imagery and LOLA elevation from **NASA/JPL Moon Trek** on the polar map, the whole-Moon map and a **3D Moon** lit by the real Sun direction. Visibility calculations apply terrain only where LOLA masks exist; otherwise results say "geometric only".
- **Demo data**: built-in approximate ephemeris over **synthetic** terrain skylines. Works offline.
- **Scientific**: JPL Horizons + LOLA terrain masks, and refuses to compute if either is missing.

For details on the JPL connection, see [docs/JPL_CONNECTION.md](docs/JPL_CONNECTION.md). To check it: `python scripts/check_jpl.py`.

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

The Vite dev server proxies `/api` to the backend, so no CORS or URL configuration is needed locally. Or run `./scripts/dev.sh`, which installs dependencies on first run and starts both.

### Tests

```bash
cd backend && pytest          # 133 tests: coordinates, time, ephemeris vs Meeus, horizon logic,
                              # intervals, API contract, mission config and site-catalogue validation,
                              # site provenance and PSR geometry, requirement checks, comparison,
                              # rescheduler, mode switching,
                              # JPL Horizons live provider and Moon Trek imagery (mocked network)
cd frontend && npm test       # projection round-trips
cd frontend && npm run build  # strict TypeScript + production bundle
```

## What it does

| View | What you can do |
| --- | --- |
| **Mission planner** | Polar map with published candidate landing sites and click-to-pick custom coordinates; landing time (UTC) with the mission's initial/alternative date presets, and duration; saved candidate dates; Sun/Earth elevation, azimuth, terrain skyline, clearance, time to sunset/Earthset; 360° horizon panorama; scrubbable visibility timeline; mission summary metrics. Sites carry their LOLA elevation, slope and nearest permanently shadowed region (PSRs drawn on the map). |
| **Compare scenarios** | Two site/date/duration scenarios side by side with every metric, change highlighting, aligned visibility bands, and data-derived trade-off statements. |
| **Reschedule a mission** | Same site and duration, original vs proposed date: changes in sunlight, Earth visibility, simultaneous visibility and longest blackouts. |
| **Lunar viewer** | Moon Trek imagery (LROC WAC, LOLA shaded relief or LOLA elevation) on three views: south polar map; zoomable whole-Moon 2D map with the night side and the Sun and Earth sub-points; 3D Moon shaped by LOLA elevation. All are lit by the Sun's position right now, or at the inspected mission time, and label craters from the IAU gazetteer. |
| **Data & methodology** | Calculation pipeline, providers per mode and their availability, which physical effects each includes, conventions, and what results do not mean. |

## Data honesty, in short

- **Demo Mode** = analytic ephemeris (Meeus, ~0.05–0.1° accuracy, verified against published worked examples) + **synthetic** horizon skylines. Labelled "Demonstration data: synthetic terrain, not real lunar conditions" on every view.
- **Custom coordinates** in Demo Mode have no skyline, so they use the flat geometric horizon and are labelled "Geometric only".
- **Scientific Mode** requires `data/scientific/ephemeris/{sun,earth}.json` (from JPL Horizons) and `data/scientific/horizon_masks/*.json` (from LOLA DEMs). If either is missing, the API returns `503 SCIENTIFIC_DATA_UNAVAILABLE` and the UI says so. Nothing is substituted.
- Sun visibility is never presented as power; Earth visibility is never presented as a comms link.
- Comparisons describe differences. They do not rank or recommend sites.
- Candidate sites use exact published coordinates (Mazarico et al. 2011 / NASA 2020 site numbering) with LOLA elevations — see [docs/SITES.md](docs/SITES.md). Demo Mode horizon skylines are still synthetic.

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
│   ├── demo/            # sites.json, horizon_masks.json (synthetic skylines)
│   ├── reference/       # PSR catalogue, LOLA site-elevation evidence, IAU crater centres
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
| JPL Horizons live provider (monthly cache, cross-check, status endpoint) | Working against a format-faithful mock; **not yet run against live Horizons** (build environment had no access to JPL). Run `scripts/check_jpl.py`. |
| Moon Trek imagery (tile cache, polar reprojection, global texture, 3D globe) | Working against a mock; reprojection verified numerically. Global WAC endpoint confirmed from public docs; **LOLA shaded-relief layer path unverified**, so check with `check_jpl.py`. |
| LOLA horizon-mask builder (DEM ray-march with curvature) | Algorithm working and tested on synthetic DEMs; GeoTIFF script needs `rasterio` and a real LOLA product |
| SPICE provider | Implemented, **not validated**: needs `spiceypy` + kernels |
| 3D terrain, power model, link budget, rankings, AI explanations, report export | Extension points and feature flags only |

## API

`GET /api/config`, `GET /api/sites`, `GET /api/psrs`, `GET /api/providers?mode=`, `GET /api/horizon-mask`, `POST /api/scenario`, `POST /api/snapshot`, `POST /api/compare`, `POST /api/reschedule`, `GET /api/jpl/status`, `GET /api/imagery/layers`, `GET /api/imagery/south-pole`, `GET /api/imagery/global`. Interactive docs at `http://localhost:8000/docs`. Errors share one shape: `{code, message, details}`.

## Further reading

- [docs/SPECIFICATIONS.md](docs/SPECIFICATIONS.md): the finalized Phase 1 specification — sites, requirements, Phase 2 datasets, sign-off
- [docs/MISSION.md](docs/MISSION.md): the 7-day solar-powered robotic mission and its three candidate sites
- [docs/SITES.md](docs/SITES.md): the selected sites, their published coordinates, LOLA elevations and PSR context
- [docs/SITE_REQUIREMENTS.md](docs/SITE_REQUIREMENTS.md): the measurable criteria a site must meet, and what those numbers do not prove
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): layers, data flow, extension points
- [docs/METHODOLOGY.md](docs/METHODOLOGY.md): the math, conventions, accuracy, what is and isn't modelled
- [docs/ADAPTATION_GUIDE.md](docs/ADAPTATION_GUIDE.md): how to respond when NASA releases more information
- [docs/JPL_CONNECTION.md](docs/JPL_CONNECTION.md): connecting to JPL Horizons and Moon Trek, troubleshooting
