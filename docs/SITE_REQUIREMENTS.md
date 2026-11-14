# Landing site requirements

The measurable criteria a south-polar site has to meet for the Polar Ice Scout
mission, and what the numbers behind them can and cannot support.

This is Phase 1, Task 3. The thresholds are **hypothetical demonstration
requirements**, taken from `tasks.md`, not official NASA mission specifications.
The mission itself is defined in [MISSION.md](MISSION.md); how LunaNav computes
each number is in [METHODOLOGY.md](METHODOLOGY.md).

## 1. Requirements

| Requirement | Threshold | Measured by | Better when | Notes |
| --- | --- | --- | --- | --- |
| Minimum sunlight availability | ≥ 60 % of the mission window | `sun_visible_pct` | higher | Sun centre above the terrain skyline |
| Minimum Earth visibility | ≥ 50 % of the mission window | `earth_visible_pct` | higher | Earth centre above the terrain skyline |
| Maximum communication blackout | ≤ 12 h | `longest_earth_blackout_hours` | shorter | Longest single Earth outage, not a dropped link |
| Proximity to PSRs | optional scientific preference | `nearby_psrs` | no direction | Names only; see section 4 |

Reported alongside the requirements, but not gates:

| Metric | Why it is shown |
| --- | --- |
| `both_visible_pct` | Sun and Earth available at the same time |
| `longest_no_simultaneous_hours` | Longest stretch where both are never up together |
| `longest_sun_blackout_hours`, `hours_until_first_sunset` | Shape of the illumination profile behind the 60 % figure |
| `hours_until_first_earthset`, `max_earth_elevation_deg` | How much margin a site has before its first Earthset |

The thresholds, ids and definitions are the ones the app already computes
(`backend/app/services/metrics.py`); Task 3 adds no new measurement.

## 2. What a verdict means

- **Window.** Every percentage is a share of the 7-day (168 h) surface mission,
  not of the lunar day. The mission has two landing dates (2026-12-01 and
  2026-12-11), so a site **meets the requirement only if it meets it on both
  dates**. A site that passes on one date and fails on the other is reported as
  date-dependent, not as a pass.
- **Sampling.** Values come from the configured step (30 min by default). When a
  window would exceed `max_samples` the step is coarsened and the response
  reports the step actually used; edges are interpolated between samples. Two
  runs at different steps are not directly comparable.
- **Censored values.** A longest-blackout figure that touches the window edge is
  a lower bound and is shown as "≥". A 12 h limit against a censored value is
  *unproven*, not passed.
- **Provisional until Task 1 lands.** All of these metrics are functions of the
  site's coordinate and its terrain mask. Until Task 1's exact coordinates,
  elevation and source are in `data/demo/sites.json`, every verdict is
  provisional and must be labelled that way wherever it is shown.
- **Terrain quality is part of the answer.** In Demo Mode the skylines are
  synthetic; custom coordinates get a flat mask. A site can meet 60 % against an
  invented skyline. Verdicts carry the run's provenance level for that reason.

## 3. Sunlight is not power, and Earth visibility is not a link

- `sun_visible_pct` says the Sun's centre is above the terrain horizon. It does
  not model panel orientation or tracking, lander self-shadowing, dust,
  temperature, eclipse, or battery state of charge. The mission assumes solar
  panels with battery storage, and `features.experimental_power_model` is off:
  there is no power model to check the 60 % against.
- `earth_visible_pct` and `longest_earth_blackout_hours` say Earth's centre is
  above the terrain horizon. They do not model antenna pattern, pointing, link
  budget, DSN scheduling, or relay satellites
  (`features.experimental_comm_link_budget` is off). The mission assumes
  direct-to-Earth, which is why line of sight is the only comm-related quantity
  this build can offer — it is a **necessary** condition, never a sufficient one.
- Neither requirement can be tightened into a guarantee without one of those
  models. They stay planning thresholds.

## 4. Proximity to PSRs

PSR proximity is a **preference, not a gate**. It is recorded as the feature
names in `nearby_psrs` (Task 1's column), and the app displays them next to the
site without scoring them. This build has no PSR geometry and no distance field,
so "proximity" cannot be turned into a number such as "within 5 km" without new
source data; `experimental_site_ranking` is off, and the project's rule is that
nothing is ranked without visible, stated criteria.

If PSR proximity is later made measurable, it needs (a) PSR outlines or a nearest-
PSR distance per site, and (b) explicit weights shown in the UI. Until then it
stays a scientific preference a planner reads, not a metric a machine applies.

## 5. Assumptions

- 7 Earth days on the surface, robotic, solar panels with battery storage,
  direct-to-Earth communication (Task 2).
- Both landing dates are in scope, and both sit inside the supported
  2026–2030 window.
- The site is on the surface; the observer is 2 m above it; the terrain horizon
  is the run's mask (synthetic in Demo Mode, LOLA-derived in Scientific Mode).
- Requirements apply to the three mission candidates in
  `mission.candidate_sites`, in their A/B/C order; other catalogue sites may be
  inspected but are not being qualified.
- Coordinates are selenographic planetocentric, Mean Earth / Polar Axis,
  longitude east-positive, on the 1737.4 km reference sphere.

## 6. Limitations

- Task 1's numbers are not final: coordinates are approximate, elevation is
  unrecorded, and PSR proximity has no distance. Verdicts inherit all three gaps.
- Site elevation is not yet added to the observer radius, and demo skylines are
  invented, so illumination percentages are not flight-quality.
- No power, thermal, communications-link, or Earth-station visibility model; no
  atmospheric refraction (there is no atmosphere).
- The Sun moves only ~0.5°/day in elevation near the pole, so a small ephemeris
  or terrain error can move a grazing sunrise by hours; near-threshold results
  should be treated as ties.
- Thresholds are demonstration values chosen for this challenge build, not
  requirements from a real mission.

## 7. Where the thresholds live

These criteria are documented here, on purpose: Phase 1 is a planning
deliverable and the app does not yet evaluate pass/fail against thresholds.
When that check is implemented, the thresholds belong in
`config/lunanav.config.json` (a `requirements` block next to `mission`, served
through `GET /api/config`) so the frontend and backend read the same numbers,
and every verdict must be displayed with its provenance. Task 4 collects the
shared specification that carries them.
