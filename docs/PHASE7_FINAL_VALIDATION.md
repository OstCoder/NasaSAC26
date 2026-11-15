# Phase 7 — Final local validation

**Result (14 November 2026; rechecked 15 November 2026): release candidate verified locally. Public deployment, recorded video and the official NASA submission are not complete yet.**

This document records what was actually run against the final repository state. It does not treat a local server as a public deployment, and it does not treat a test matrix as a NASA submission. The single pre-submission gate is [finalize.md](../finalize.md).

## 1. Release checks

| Check | Command | Result |
| --- | --- | --- |
| Backend suite | `cd backend && ./.venv/bin/python -m pytest -q` | **353 passed**, 0 skipped on Python 3.14. Includes the new top-level `/health` test. One non-failing Starlette/httpx deprecation warning. |
| Frontend suite | `cd frontend && npm test -- --run` | **52 passed** in 13 files |
| TypeScript | `cd frontend && npm run typecheck` | passed |
| Production build | `cd frontend && npm run build` | passed; entry chunk 1,066.01 kB / 316.26 kB gzip |
| Phase 4 browser matrix | `cd frontend && npm run acceptance` | **13/13 passed** |
| Phase 5 browser matrix | `cd frontend && npm run acceptance:phase5` | **6/6 passed** |
| Phase 6 browser matrix | `cd frontend && npm run acceptance:phase6` | **8/8 passed** |
| Dataset catalogue | `cd backend && ./.venv/bin/python scripts/check_datasets.py` | **all datasets consistent** |
| NASA data validation | `cd backend && ./.venv/bin/python scripts/validate_nasa_data.py` | **10/10 checks**, 1,014 records; live check recorded 2026-11-14T21:01:36Z |
| Initial mission window | `./.venv/bin/python scripts/analyze_mission.py --start 2026-12-01 --days 7 --compare-all` | passed; JSON written to ignored `backend/outputs/` |
| Alternative mission window | `./.venv/bin/python scripts/analyze_mission.py --start 2026-12-11 --days 7 --compare-all` | passed; JSON written to ignored `backend/outputs/` |
| Secret scan | tracked-file scan for env files, common token/private-key patterns and credential filenames | no matches |
| Debug scan | `console.log`, `console.debug`, `debugger`, `TODO`, `FIXME`, `XXX` under `frontend/src` and `backend/app` | no matches |
| Generated-file scan | tracked `.tmp`, `.log`, `__pycache__`, `.DS_Store`, `node_modules`, `dist` | no matches |
| Slow-connection check (Task 5) | throttled API link via `scripts/slow_connection_proxy.py` (400 kbit/s, 600 ms RTT) | all analysis endpoints < 1 s; repeat-visit boot interactive ≈ 8.7 s; zero errors; see [PHASE6_PERFORMANCE.md](PHASE6_PERFORMANCE.md) |
| README screenshots (Task 8) | 8 captured views in `assets/screenshots/`, linked from the README | done |

On 15 November the backend suite, frontend suite, TypeScript check and production build were rerun against this repository state and all passed. The browser matrices and live scientific checks below remain the 14 November evidence; they were not rerun in this documentation pass.

The browser matrices use the installed Google Chrome through Playwright and the real FastAPI backend; they do not mock analysis responses. The Phase 6 science page rendered in **3.117 s** with a **641 ms** navigation load in this run. The 390 px layout had no horizontal overflow.

The build warning that the entry chunk exceeds 500 kB remains visible. It is a performance warning, not a failing build, and the 3D scene and Science page are route/feature split.

## 2. Scientific validation

### Data integrity

`scripts/check_datasets.py` reports all eleven catalogue entries with the expected availability and count:

- 6 sites, 3 mission candidates
- 1,014 committed hourly Sun/Earth records
- 3 LOLA terrain references and 3,360-point horizon masks
- 653 PSR polygons
- 1,615 crater centres
- 180 independent Horizons reference rows and 10 validation checks
- 5 cached Horizons months and 1,571 Moon Trek tile files
- tabulated ephemeris **unavailable by design**, reported rather than silently replaced

`scripts/validate_nasa_data.py` passes all ten checks. The independent Meeus model agrees with the committed JPL Horizons records to **≤ 0.032° in elevation** and **≤ 0.020° in azimuth**; UTC, continuity, observer location and same-site/different-date independence also pass.

### Mission-window results

Committed terrain-adjusted results from the final run:

| Site | 1–8 Dec Sun | 1–8 Dec Earth | 11–18 Dec Sun | 11–18 Dec Earth | Initial blackout | Delayed blackout |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Shackleton Rim | 0.0% | 0.0% | 0.0% | 0.0% | ≥168.0 h | ≥168.0 h |
| Connecting Ridge | 100.0% | 0.0% | 100.0% | 20.5% | ≥168.0 h | ≥133.5 h |
| de Gerlache Rim | 100.0% | 1.4% | 100.0% | 60.0% | ≥165.7 h | ≥67.2 h |

The 10-day delay improves Earth visibility at Connecting Ridge by 20.5 percentage points and at de Gerlache Rim by 58.7 points, but no candidate meets the configured 60% Sun / 50% Earth / 12 h blackout targets in either window. The app reports those failures rather than selecting a winner.

A real release bug was found and fixed during this check: `backend/scripts/analyze_mission.py` did not add `backend/` to `sys.path`, so the README command failed with `ModuleNotFoundError: app`. The script now runs from `backend/` exactly as documented.

### What the numbers do not mean

- Sun above the terrain is not a power estimate.
- Earth above the terrain is not a working radio link.
- A requirement verdict is not a landing-safety or mission-feasibility certification.
- PSR proximity is not water ice and not a traverse.
- The 3D shadow view is illustrative; the 2D terrain-horizon calculation is authoritative.

## 3. Application checks

The Phase 4–6 matrices cover the complete workflow:

- all three candidate sites and custom coordinates;
- landing date and duration changes;
- Sun/Earth positions, skyline, clearance, timeline and panorama;
- site comparison and mission-delay comparison;
- adjustable requirements and decision support;
- invalid input, HTTP 500, aborted request and full boot failure handling;
- 1440 px and 390 px layouts;
- PSR layer, proximity context, 390 px science page and no-overclaim language;
- playback speeds, next-transition marker, lazy 3D terrain, marker and scale;
- no page errors or 5xx API responses in the final browser runs.

## 4. Repository check

- The repository is public: <https://github.com/OstCoder/NasaSAC26>.
- The final code and documentation are committed on `main`.
- `.gitignore` contains virtual environments, dependency trees, build output, generated caches, logs, test artifacts and env files.
- No API keys are required for the default live JPL mode; no credentials are committed.
- Code is MIT-licensed; NASA data is separately attributed and is not relicensed by this project.

## 5. Open release gates

Completed on 14 Nov 2026 (no longer open): **gate 3 — final screenshots captured and added
to the README** (`assets/screenshots/`, 8 views).

These are deliberately **not** marked complete because they need an external account, a public URL, recorded media or human sign-off:

1. Deploy the backend to Render and the frontend to Vercel using [DEPLOYMENT.md](DEPLOYMENT.md).
2. Record the public URLs and run the complete workflow from a second device.
3. Record and upload the demonstration video.
4. Rehearse the pitch with the team and confirm the event time limit.
5. Complete the current official Project tab, submit, and verify the submission in a private window.

## 6. Night upgrades (15 Nov 2026)

Autonomous follow-up work committed after the initial Phase 7 package:

- `GET /api/version` (app name, version, API contract, supported window, git SHA).
- CORS `max_age=86400` plus `X-Response-Time` and weak ETag/304 on `/api/config`, `/api/sites`, `/api/craters`, `/api/psrs`, `/api/science/psrs`.
- Frontend data-saver mode (localStorage + auto-detect slow link) with a TopNav toggle; 512 px imagery when on.
- Shareable scenario links: "Copy scenario link" button and URL-param prefill on load.

Backend suite: **353 passed**, 0 skipped. Frontend: **52 passed**; typecheck and build clean.

Until those steps are done, Phase 7 is a verified local release candidate, not a completed submission.
