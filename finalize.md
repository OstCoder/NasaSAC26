# Finalize LunaNav — pre-submission checklist

**Status: 15 November 2026 — verified local release candidate; not deployed, recorded or submitted.**

`tasks.md` currently has **202 items verified and 80 open**. Most open items need a hosting account, a public URL, recorded media, the registered team page or a human rehearsal. This file is the release gate: do not mark a box complete without the evidence named beside it.

Detailed instructions live in:

- [Deployment guide](docs/DEPLOYMENT.md)
- [Submission packet](docs/SUBMISSION_PACKET.md)
- [Demo, video and pitch](docs/DEMO_AND_PITCH.md)
- [Local validation evidence](docs/PHASE7_FINAL_VALIDATION.md)
- [Attribution and licenses](docs/ATTRIBUTION.md)

## Gate summary

| Gate | Current state | Required evidence |
| --- | --- | --- |
| Local application, tests and data | **Pass** | Commands below |
| Public backend | **Open** | Working Render URL and `/health` |
| Public frontend | **Open** | Working Vercel URL, no login |
| Public end-to-end workflow | **Open** | Private-window and second-device pass |
| Screenshots in README | **Local set committed** | 8 views in `assets/screenshots/`; refresh if the deployed UI changes |
| Demonstration video | **Open** | Accessible video URL |
| Team rehearsal and time limit | **Open** | Team sign-off |
| Official Project tab and submission | **Open** | Submitted project and saved confirmation |

## 1. Freeze the release

- [ ] `git status -sb` is clean and `main` is level with `origin/main`.
- [ ] Record the release commit: `git rev-parse --short HEAD`.
- [ ] Deploy that exact commit; do not mix a deployed frontend with a different backend revision.
- [ ] Confirm the repository is public and contains frontend, backend, data, docs and license.

Run these checks from the repository root before freezing:

```bash
cd backend && ./.venv/bin/python -m pytest -q                 # expect 353 passed
./.venv/bin/python scripts/check_datasets.py                  # expect all datasets consistent
./.venv/bin/python scripts/validate_nasa_data.py              # expect 10/10 checks
./.venv/bin/python scripts/analyze_mission.py --start 2026-12-01 --days 7 --compare-all
./.venv/bin/python scripts/analyze_mission.py --start 2026-12-11 --days 7 --compare-all

cd ../frontend
npm test -- --run                                             # expect 52 passed
npm run typecheck
npm run build
npm run lint                                                  # expect 0 errors

cd ..
git diff --check
```

Expected local baseline:

- Backend **353 passed**, 0 skipped; dataset catalogue consistent; NASA validation **10/10**, 1,014 records.
- Frontend **52 passed**; TypeScript and production build pass.
- Lint has **0 errors**, with non-blocking React/script warnings.
- Both committed mission windows run without network access.
- No committed secrets, debug statements or generated caches.

The browser matrices are the latest run from 14 November 2026: Phase 4 **13/13**, Phase 5 **6/6**, Phase 6 **8/8**. Rerun them if application code changes after this freeze.

## 2. Deploy the exact commit

### Backend — Render

- [ ] Create the Render Blueprint from this repository; `render.yaml` uses `rootDir: backend`.
- [ ] Set `LUNANAV_CORS` to the final Vercel origin, with no trailing slash.
- [ ] Confirm the health check `/health` passes.
- [ ] Confirm these return real data, not an error page:
  - `GET /api/config`
  - `GET /api/sites`
  - `GET /api/phase3/windows`
  - `GET /api/validation`
- [ ] Confirm no API key or database is required for the default mode.

Record after verification:

| Field | Value |
| --- | --- |
| Backend URL | |
| Render service / region | |
| Deployed commit | |
| Health-check time (UTC) | |

### Frontend — Vercel

- [ ] Import the repository with **Root Directory** set to `frontend`.
- [ ] Set `VITE_API_BASE` to the backend origin only, with no trailing slash.
- [ ] Confirm `LUNANAV_CORS` exactly matches the final frontend origin, then restart the backend.
- [ ] Confirm the app loads with no browser console errors and no 5xx API responses.

Record after verification:

| Field | Value |
| --- | --- |
| Frontend URL | |
| Vercel project | |
| `VITE_API_BASE` origin | |
| `LUNANAV_CORS` origin | |
| Deployment time (UTC) | |

A green hosting status is not acceptance. The public workflow below must pass.

## 3. Run the public acceptance pass

Open the public frontend in a **private window** and repeat on a **second device**:

- [ ] No login, invitation or local server is required.
- [ ] Select Shackleton Rim, Connecting Ridge and de Gerlache Rim.
- [ ] Switch between 1 December and 11 December 2026.
- [ ] Inspect Sun/Earth elevation, skyline, clearance, timeline and metrics.
- [ ] Compare two sites over the same window.
- [ ] Compare the original and delayed landing.
- [ ] Change a requirement and confirm PASS/FAIL/UNDECIDED updates.
- [ ] Confirm Decision support never promotes a failing or undecided candidate.
- [ ] Open Science exploration; confirm PSR proximity is shown and water ice says **not assessed**.
- [ ] Enable the optional 3D terrain view; confirm it is labelled illustrative.
- [ ] Download the Markdown mission report.
- [ ] Check desktop and approximately 390 px width for overflow.
- [ ] Check the console for errors and the network panel for 5xx responses.

Expected comparison from the committed data:

| Site | 1–8 Dec Sun / Earth | 11–18 Dec Sun / Earth | Initial blackout | Delayed blackout |
| --- | --- | --- | ---: | ---: |
| Shackleton Rim | 0.0% / 0.0% | 0.0% / 0.0% | ≥168.0 h | ≥168.0 h |
| Connecting Ridge | 100.0% / 0.0% | 100.0% / 20.5% | ≥168.0 h | ≥133.5 h |
| de Gerlache Rim | 100.0% / 1.4% | 100.0% / 60.0% | ≥165.7 h | ≥67.2 h |

No candidate meets every configured requirement in either window. Do not “fix” that result for the demo; it is the finding.

## 4. Capture submission media

- [x] Eight local JPL-live screenshots are committed in `assets/screenshots/` and linked from the README.
- [ ] Capture one phone-width screenshot.
- [ ] Confirm every visible number matches the deployed app, not an older local build.
- [ ] Refresh any screenshot that no longer matches the deployed build and update the README.
- [ ] Open the current official Project tab and verify its video and image requirements before recording.
- [ ] Record a concise demonstration using [docs/DEMO_AND_PITCH.md](docs/DEMO_AND_PITCH.md).
- [ ] Show site selection, Sun/Earth visibility, comparison, delay analysis, sources and limits.
- [ ] Add captions; verify audio, legibility and that no private browser data is visible.
- [ ] Upload the video and open the link in a private window.
- [ ] Confirm the video link is accessible to judges without an account.

## 5. Assemble the submission

Use the prepared text in [docs/SUBMISSION_PACKET.md](docs/SUBMISSION_PACKET.md), but confirm every field against the live Project tab.

- [ ] Log in to the registered NASA Space Apps team page.
- [ ] Review the current Project tab; it overrides older instructions.
- [ ] Confirm project title: **LunaNav — Lunar Landing Site Navigator**.
- [ ] Confirm the selected challenge.
- [ ] Confirm every registered team member is listed.
- [ ] Paste and proofread the short and full descriptions.
- [ ] Add the public frontend URL.
- [ ] Add the public GitHub repository URL.
- [ ] Add the video and screenshots required by the current form.
- [ ] Add scientific references and data sources from [docs/ATTRIBUTION.md](docs/ATTRIBUTION.md).
- [ ] Complete licensing fields; code is MIT, data is separately attributed.
- [ ] Remove every placeholder, local URL and unverified claim.
- [ ] Confirm the deadline shown in the event UI before submitting.
- [ ] Save a copy of the final text and every link.

Do not submit with a localhost URL, a private repository, an inaccessible video or an unchecked team list.

## 6. Claim audit

Every public description and the video must preserve these limits:

- [ ] LunaNav is **not** NASA-approved, certified, affiliated or operationally adopted.
- [ ] Sun visibility is **not** generated power.
- [ ] Earth visibility is **not** a working communications link.
- [ ] Power and link-budget assumptions are representative, not measured hardware.
- [ ] PSR proximity is **not** confirmed water ice, ice concentration, a traverse or a safe landing site.
- [ ] The terrain-horizon calculation is authoritative; the 3D shadow preview is illustrative.
- [ ] Demo-mode horizons are synthetic and labelled as such.
- [ ] Results are decision support, not a flight-certified or landing-safety system.

## 7. Submit and verify

- [ ] Submit the project from the registered team page.
- [ ] Save the submission confirmation and a timestamped screenshot.
- [ ] Verify the project appears on the team page and is marked as submitted.
- [ ] Open the public app, repository and video in a fresh private window.
- [ ] Confirm every public link works without login.
- [ ] Confirm all required fields, credits and team members are present.
- [ ] Keep a backup of the final commit, screenshots, text, video and receipt.

Do not mark Phase 7 complete until the confirmation exists and all public links have been rechecked.

## 8. Final evidence record

| Item | Value |
| --- | --- |
| Release commit | |
| Public frontend URL | |
| Public backend URL | |
| Video URL | |
| Submission confirmation file | |
| Submitted at (UTC) | |
| Verified by | |
| Verification date | |

## Where things are listed

| Topic | Source of truth |
| --- | --- |
| Phase task status and open work | [tasks.md](tasks.md) — 202 verified, 80 open |
| Project overview, local run, tests and API | [README.md](README.md) |
| Final local test and data evidence | [docs/PHASE7_FINAL_VALIDATION.md](docs/PHASE7_FINAL_VALIDATION.md) |
| Render/Vercel steps, env vars and CORS | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| Proposed submission copy and open fields | [docs/SUBMISSION_PACKET.md](docs/SUBMISSION_PACKET.md) |
| Demo sequence, video script and judge Q&A | [docs/DEMO_AND_PITCH.md](docs/DEMO_AND_PITCH.md) |
| Data provenance, references and licenses | [docs/ATTRIBUTION.md](docs/ATTRIBUTION.md) |
| Site coordinates and candidate provenance | [docs/SITES.md](docs/SITES.md) |
| Mission requirements and thresholds | [docs/SPECIFICATIONS.md](docs/SPECIFICATIONS.md) |

**Final rule:** if a required item is not visible in the public deployment or the official submission page, it is not complete — regardless of what passes locally.
