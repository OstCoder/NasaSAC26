# Mission decision support (Phase 5)

LunaNav's decision dashboard answers a narrower question than “which site is
best?”: **under the requirements the user selected, which candidates pass every
check, and how do the passing candidates compare on measured conditions?**

- UI: **Decision support** in the main navigation
- Endpoint: `POST /api/decision`
- Code: `backend/app/services/decision.py`, `frontend/src/features/decision/`
- Tests: `backend/tests/test_decision.py`, `frontend/src/features/decision/DecisionDashboard.test.tsx`
- Browser acceptance: `npm run acceptance:phase5` ([docs/PHASE5_ACCEPTANCE.md](PHASE5_ACCEPTANCE.md))
- Power/delay tests: `backend/tests/test_engineering.py`, `backend/tests/test_api_and_modes.py`,
  `frontend/src/features/rescheduler/ReschedulerPanel.test.tsx`, `frontend/src/features/phase3/energySeries.test.ts`

## What is evaluated

Each candidate is run through the same scenario engine as the rest of the
application. The decision layer adds no new Sun/Earth positions and no new
terrain. It checks:

| Check | Source | Rule |
| --- | --- | --- |
| Minimum sunlight | terrain-adjusted `sun_visible_pct` | measured ≥ target |
| Minimum Earth visibility | terrain-adjusted `earth_visible_pct` | measured ≥ target |
| Maximum Earth blackout | `longest_earth_blackout_hours` | measured ≤ target |
| Maximum darkness | `longest_sun_blackout_hours` | measured ≤ target |
| Battery reserve | Phase 5 engineering model at the user's `power_demand_w` | no unserved load and reserve respected |

The first four reuse the requirement status rules. A window-censored “at most”
value remains **UNDECIDED**, even when its lower bound is below the target,
because the true interval could be longer. A censored “at least” value can pass
only when its lower bound already clears the target.

The battery check is available only for the two committed mission windows
(1 Dec and 11 Dec 2026 UTC). For another landing time the API returns
`power.available: false` and an UNDECIDED battery check instead of guessing.

## Eligibility and ranking

1. A candidate with any **required FAIL** is not eligible.
2. A candidate with any **required UNDECIDED** check is not eligible.
3. A check can be marked **advisory** for one evaluation (for example, the
   window-censored Earth blackout). It remains visible with its measurement and
   status, but it does not gate eligibility. It is not reported as a pass.
4. Only eligible candidates receive a score and rank.
5. If none are eligible, the recommendation is
   `"no_eligible_site"` and the dashboard says so. It does not promote the
   highest raw measurement.

Scores are normalised over the eligible set only:

```text
sunlight        min/max of sun_visible_pct                 higher is better
earth           min/max of earth_visible_pct               higher is better
communication   inverse min/max of longest blackout        shorter is better
science         inverse min/max of PSR distance            closer is better
score = 100 * sum(weight_i * component_i) / sum(weight_i)
```

The UI exposes four documented presets: **Balanced**, **Sunlight first**,
**Communications first**, and **Science exploration**. The API accepts explicit
weights, so a client can supply its own. These are demonstration weights, not a
NASA suitability score. Each ranked row exposes its normalised
`score_components` (sunlight, Earth visibility, communication, science) so the
weighted result can be checked rather than taken on trust.

**Science exploration** is a visible mode, not a separate calculation path. It
raises the science weight and displays every candidate's nearest mapped PSR and
its 10 km count alongside the operational checks. Proximity never makes a failing
or undecided operational check eligible. The section states that this is not a
traverse plan, water-ice measurement, or landing-safety assessment.

When the science weight is non-zero, the explanations name the nearest mapped
PSR, its straight-line distance, and explicitly say that this is not water-ice or
rover-access evidence. If a site has no mapped PSR, the science component uses the
least favourable value and the risk list says so.

## Power timeline and delay analysis

The dashboard's decision rows summarise the battery model. The Mission Planner's
power panel now draws the supporting per-sample `series` (solar, load, battery
state of charge, Sun-blocked spans and the reserve/minimum markers). The trace is
the same committed hourly record used by the decision check, not a separate
visualisation model.

The **Reschedule a mission** view compares requirement verdicts in addition to
visibility. For the two committed windows it also compares array energy, net
energy, minimum battery and unserved load, and reports the deltas. It returns
`power.available: false` with a reason for custom coordinates, non-preset dates
or any duration other than the committed 168 h window; it never interpolates a
power curve.

## Orientation and sensitivity

The decision API accepts `panel_design` (`horizontal`, `vertical_tracking` or
`fixed`), `panel_tilt_deg` and `panel_azimuth_deg`; the selected design drives the
battery check rather than a hidden default. The engineering API returns the same
design and a seven-case one-at-a-time sensitivity table (solar conversion ±10 %,
load ±20 %, battery capacity ±10 %). These are deterministic bounds around a
point-estimate config, not measured uncertainty. The power panel exposes both the
orientation controls and the sensitivity table; the Phase 5 acceptance run
exercises them in the browser.

## Explanations

Explanations are deterministic strings built from the checks and metrics. They
state which checks passed, failed or remained undecided, give the measured values
and targets, and identify the strongest comparison and operational risks. There
is no generated text and no AI model in the recommendation path.

## PSR context

The decision row includes the nearest mapped PSR distance from the Phase 1 site
catalogue. It is optional science context, not an eligibility rule. A short
straight-line distance is **not** proof of water ice, a safe route, or rover
accessibility.

## Current data caveat

In the committed seven-day windows, every `longest_earth_blackout_hours` value is
window-censored. Under the conservative “at most” rule, that check can never be
PASS in these windows. The dashboard therefore keeps Earth blackout **advisory by
default**: the measurement and its UNDECIDED status stay visible, but they do not
make every candidate ineligible. Requiring it with **Require for eligibility**
shows the honest result — no candidate can pass an at-most check that the window
cannot decide — and never converts it to a pass.

With the remaining defaults (60 % Sun / 50 % Earth / 16 h darkness / 40 W), the
1 Dec 2026 window has no eligible candidate because no site reaches 50 % Earth
visibility. Changing the landing date to 11 Dec 2026 makes de Gerlache eligible
and top-ranked, which is the key Phase 5 date-change workflow. This is a measured
date-dependent result, not a default winner. Dates outside the committed windows
still return UNDECIDED for the battery check, so they cannot produce a ranking.

## What is not modelled

- Landing hazards, radiation, thermal limits, hardware health and operations.
- A flight power or communications budget. Power assumptions are configuration.
- Power comparison for non-committed dates or durations; those cases are
  explicitly undecided rather than interpolated.
- PSR water-ice concentration, traversability or route planning. Science
  exploration is a ranking preference and context view, not a traverse planner.
- AI-generated explanations. All recommendation text is deterministic.
- Sensitivity correlations and probability distributions; the sensitivity cases
  change one assumption at a time.
