# Edit Recommendations — LunaNav for NASA Space Apps 2026

Generated from the challenge statement and a review of `OstCoder/NasaSAC26`. The codebase already implements most of the challenge objectives (terrain-aware horizon masks, JPL Horizons ephemeris, LOLA DEMs, side-by-side comparison, delay analysis, decision support, PSR science). The remaining work is **deployment, media, submission, and a small set of UX/presentation shifts** that move the project from "solid prototype" to "winning submission."

## 1. Immediate submission gates (do these first)

These are the only items marked incomplete in `tasks.md`, `docs/PHASE7_FINAL_VALIDATION.md`, and `docs/SUBMISSION_PACKET.md`. Without them the project cannot be judged.

| # | Item | File(s) to edit | Notes |
|---|------|-----------------|-------|
| 1 | Deploy backend (Render) + frontend (Vercel) | `docs/DEPLOYMENT.md`, `render.yaml`, `frontend/vercel.json` | Required to get a public URL. |
| 2 | Record and upload the 2–3 min demo video | `docs/DEMO_AND_PITCH.md` (video script included) | Judges watch this first. Use the deployed URL. |
| 3 | Complete the official Project tab on the NASA Space Apps team page | `docs/SUBMISSION_PACKET.md` | Submit before 15 Nov 2026, 11:59 PM local. Verify in a private window. |
| 4 | Add public URL + video link to submission packet & README | `docs/SUBMISSION_PACKET.md`, `README.md` | `SUBMISSION_PACKET.md` has unchecked fields for these. |
| 5 | Confirm no credentials committed | `.gitignore`, tracked-file scan | Already verified clean; re-check before final push. |

## 2. Content edits — README.md

Update the status line at the top once deployed:

**Old:**
```
> **Status (14 Nov 2026):** verified local release candidate. ... A public deployment, demonstration video and official NASA submission are still pending — see docs/PHASE7_FINAL_VALIDATION.md.
```

**New:**
```
> **Status (15 Nov 2026):** publicly deployed at <DEPLOYMENT_URL>. Backend tests (348 passed + 4 skipped), frontend tests (52 passed), typecheck, and Phase 4–6 browser matrices (13/13 + 6/6 + 8/8) all green. Official NASA submission complete — see docs/SUBMISSION_PACKET.md.
```

Add a short **"Why this wins the challenge"** section after "Our solution" (or link to it):

```
### How this addresses the challenge

- **Rapid site & date comparison:** pick from six published south-pole sites or click custom coordinates; switch between the 1–8 and 11–18 Dec 2026 windows instantly; see terrain-adjusted Sun/Earth visibility in one view.
- **Terrain-aware horizons:** LOLA DEM masks mean Sun/Earth are shown against the real skyline, not a flat sphere — the key differentiator vs Quickmap/Moon Trek for rapid planning.
- **Operational metrics:** time-to-sunset/Earthset, sunlight %, Earth visibility %, longest blackout, simultaneous visibility, power and link-budget estimates.
- **Delay resilience:** same site, original vs delayed date — see exactly what a schedule slip changes (the core NASA scenario).
- **Dual audience:** planner mode (metrics, requirements, exports) + public/education mode (plain-language PSR and lighting explanations).
```

In the "What it does" table, the rows are already strong. Keep them. Consider adding one row for the **public/education toggle** if it exists in code; if not, add it as a recommended feature (section 4).

Update the "Data honesty" section to explicitly state the public deployment URL and video link once they exist.

## 3. Content edits — docs/SUBMISSION_PACKET.md

Check the remaining boxes and fill in:

- [x] Public website URL → `<DEPLOYMENT_URL>`
- [x] Demonstration video / media link → `<VIDEO_URL>`
- [x] Confirmed team-member list on the registered team page → OstCoder and Aarush Gutha (verify on the team page)
- [x] Official Project tab reviewed → completed + verification date
- [x] Submission completed → date/time
- [x] Submission status verified → screenshot/confirmation saved

Add a line after submission: "Submission confirmation saved at `<path>`; public links verified in a private window on `<date>`."

## 4. Recommended UX / presentation shifts (the "winning" differentiators)

These are not blocking submission, but they directly answer the challenge's asks and give judges a memorable story.

### Shift A — Frame "no site passes" as the insight, not a dead end

The validated demo shows **no candidate meets every requirement in either window**. That is scientifically honest, but a judge may read it as "the tool found no answer." Reframe:

- In **Decision support**, add a clearly labelled **"What would make this pass?"** panel: e.g. "To meet the 50% Earth target at de Gerlache Rim, shift the landing ≥X days or add a relay satellite; to meet 60% Sun at Shackleton Rim, relocate ≥Y km to a near-eternal-light peak."
- In the **demo video**, narrate the "no winner" result as the point: schedule changes move the needle but don't override terrain. That is exactly the NASA scenario (hardware delays force re-evaluation).
- Add one **comparative win**: at minimum, show that the *delayed* date is strictly better than the *initial* date for Earth visibility (already true in data: de Gerlache 1.4% → 60%). Lead with that improvement.

### Shift B — Make custom coordinates feel first-class

Today custom coordinates are "geometric only" (no terrain mask). The challenge explicitly lists custom coordinates alongside curated sites.

- Add a banner in the planner when custom coordinates are selected: "Terrain mask not available for this coordinate — showing geometric horizon only. Use a published candidate site for terrain-adjusted results."
- Offer a **"fill nearby candidate"** button: snap the custom click to the nearest published site so the user instantly gets terrain data.

### Shift C — Add a public / educator mode toggle

The challenge names educators and the public as users. The current UI is planner-dense.

- Add a top-nav toggle: **Planner mode** vs **Public mode**.
- Public mode: plain-language cards ("Will the rover have power?", "Can we call Earth?"), the six education topics already referenced, bigger text, fewer decimal places, and the PSR "water ice: not assessed" explained without jargon.
- Keep all calculations identical; only the presentation layer changes.

### Shift D — Shareable scenario links already exist

`docs/PHASE7_FINAL_VALIDATION.md` notes shareable scenario links ("Copy scenario link" + URL-param prefill) are landed. Verify this works in the deployed build and feature it in the demo ("send this link to your science team").

### Shift E — Export / one-pager

The challenge wants mission planners to evaluate and hand off. `GET /api/mission-report.md` already exports a deterministic Markdown report. Add a visible **"Download mission one-pager"** button in the planner and reference it in the video.

## 5. Key strategic shifts to win (summary)

| Shift | From | To | Why it wins |
|-------|------|-----|-------------|
| 1 | Local release candidate | Publicly deployed URL + video + official submission | Submission is a hard gate; nothing else matters without it. |
| 2 | "No site passes" hidden as data | "No site passes" narrated as the key insight | Judges remember the story; honesty + clear trade-off framing builds trust. |
| 3 | Three curated sites only | Custom coordinates + snap-to-nearest-candidate | Matches the challenge's explicit "curated list + custom coordinates" ask. |
| 4 | Planner-only UI | Dual planner / public-education mode | Addresses the "accessibility across skill levels" objective. |
| 5 | Internal validation only | Public demo link + video + one-pager export | Makes the work visible and shareable for judges and the public. |

## 6. Pre-submission checklist

```
[ ] Backend deployed to Render; /health responds
[ ] Frontend deployed to Vercel; VITE_API_BASE set
[ ] CORS set to frontend origin; no 5xx on public workflow
[ ] Public URL recorded in SUBMISSION_PACKET.md and README.md
[ ] Demo video recorded at 1080p with captions; URL added
[ ] Official Project tab completed and submitted before deadline
[ ] Submission verified in a private window on a second device
[ ] No secrets committed; .gitignore clean
[ ] Final push to main (OstCoder/NasaSAC26)
```

## 7. Files already in good shape (no edits needed)

- `README.md` feature list, technology stack, data honesty, and screenshots are complete.
- `docs/ATTRIBUTION.md`, `docs/VALIDATION.md`, `docs/DATASETS.md`, `docs/TERRAIN.md`, `docs/JPL_CONNECTION.md` cover NASA data sourcing.
- `docs/DECISION_SUPPORT.md`, `docs/ENGINEERING.md`, `docs/MISSION_REPORT.md` document the methodology.
- `docs/DEPLOYMENT.md` and `docs/DEMO_AND_PITCH.md` contain ready-to-use procedures.
- Backend (349 tests) and frontend (52 tests + typecheck + build) are green locally.
