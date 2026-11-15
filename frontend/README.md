# LunaNav frontend

React 19 + TypeScript + Vite single-page app. It only renders what the API
returns: every visibility, requirement and comparison number comes from the
backend, so there is no science logic here. Start with the
[root README](../README.md); [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
explains how the pieces fit together.

## Scripts

| Command | What it does |
| --- | --- |
| `npm run dev` | Vite dev server on :5173, proxying `/api` to `http://127.0.0.1:8000` (override the target with `LUNANAV_API`) |
| `npm run build` | `tsc -b` across all project references, then the production bundle |
| `npm run typecheck` | Types only, no bundle |
| `npm test` | Vitest/jsdom: 52 tests covering maps, visibility, comparison, decision support, rescheduling, power helpers and 3D shadows |
| `npm run lint` | Oxlint |
| `npm run preview` | Serve the built bundle |

## Environment

| Variable | Effect |
| --- | --- |
| `VITE_API_BASE` | API origin when the app is not served behind the Vite proxy; empty means same origin |
| `VITE_LUNAR_TILE_URL` | Replaces Moon Trek with your own south-polar-stereographic tile server |
| `VITE_LUNAR_TILE_ATTRIBUTION` | Attribution for those tiles (defaults to NASA/GSFC/ASU LRO) |
| `LUNANAV_API` | Dev-proxy target only; read by `vite.config.ts`, not by the bundle |

## Layout

- `src/features/` — one folder per view: `mission-planner`, `visibility`,
  `comparison`, `rescheduler`, `lunar-map`, `lunar-globe`, `methodology`.
- `src/components/` — shared primitives, provenance callouts, error states, nav.
- `src/services/api.ts` — the only place that calls `fetch`; typed `ApiError`
  carrying the backend's `code`.
- `src/types/api.ts` — mirror of `backend/app/models/schemas.py`.
- `src/config/` — feature-flag resolution and presentation constants.

When a schema changes, update `src/types/api.ts` in the same commit and run
`npm run build`: strict TypeScript catches a field the UI forgot.

Feature flags come from `GET /api/config`. Any of them can be toggled locally
with `?ff=<flag>:on` or `?ff=<flag>:off`; the override persists in localStorage.
