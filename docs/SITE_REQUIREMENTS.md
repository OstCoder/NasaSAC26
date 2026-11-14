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
| Proximity to PSRs | optional scientific preference | `nearest_psr.distance_km`, `psrs_within_10_km` | no direction | Measured to mapped PSRs > 5 km²; see section 4 |

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
- **Task 1 has landed.** The candidates are Task 1's exact published coordinates
  with recorded LOLA elevations, slopes, coordinate sources and PSR distances, so
  no verdict is blocked on site data. Terrain is the remaining dependency: the
  same coordinate can pass against one skyline and fail against another.
- **Terrain quality is part of the answer.** In Demo Mode the skylines are
  synthetic; custom coordinates get a flat mask. A site can meet 60 % against an
  invented skyline. Verdicts carry the run's provenance level for that reason.

### Worked example: the three candidates as measured today

Demo Mode, 168 h from each landing preset (00:00 UTC landings), 30 min step,
Task 1's coordinates and **synthetic** skylines (`horizon_mask.source` says so
on every response). The verdicts come from the app's own check,
`POST /api/requirements`, with the thresholds read from the config — the same
numbers a planner would see. This shows the criteria are computable from what
the API already returns; it is not evidence about the real sites.

| Site | Date | Sun ≥ 60 % | Earth ≥ 50 % | Blackout ≤ 12 h | `both_visible_pct` |
| --- | --- | --- | --- | --- | --- |
| `shackleton-rim` | 2026-12-01 | 100.0 % pass | 0.0 % fail | 168.0 h not met (≥, limited by the window) | 0.0 % |
| `shackleton-rim` | 2026-12-11 | 100.0 % pass | 45.0 % fail | 92.4 h not met (≥, limited by the window) | 45.0 % |
| `connecting-ridge` | 2026-12-01 | 100.0 % pass | 0.0 % fail | 168.0 h not met (≥, limited by the window) | 0.0 % |
| `connecting-ridge` | 2026-12-11 | 43.4 % fail | 38.4 % fail | 103.5 h not met | 0.0 % |
| `de-gerlache-rim` | 2026-12-01 | 91.7 % pass | 0.0 % fail | 168.0 h not met (≥, limited by the window) | 0.0 % |
| `de-gerlache-rim` | 2026-12-11 | 0.0 % fail | 42.7 % fail | 96.2 h not met | 0.0 % |

Read it as a demonstration of the procedure, not a ranking: no candidate clears
all three gates on either preset date, and the deciding factor is Earth sitting
below invented terrain rather than a property of the site. Against the synthetic
skyline every Earth outage lasts the window or tens of hours, so the blackout
limit fails outright; on a real LOLA mask some of those outages would shrink, but
none of that is claimed here. Repeating the same calls in Scientific Mode, where
the horizon masks come from LOLA terrain, is what would turn this table into an
actual qualification.

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

PSR proximity is a **preference, not a gate**. Task 1 records it two ways: the
nearest mapped PSR with its boundary distance and area, and the count of mapped
PSRs within 10 km, both filled at load time from the LROC south-pole PSR
catalogue (`data/reference/psrs.json`). The planner prints them beside the site
and does not score them.

| Site | Nearest mapped PSR | Distance | Area | Mapped PSRs within 10 km |
| --- | --- | --- | --- | --- |
| `shackleton-rim` | PSR near Shackleton (`SP_896450_1282030`) | 2.48 km | 233.7 km² | 1 |
| `connecting-ridge` | PSR near Spudis (`SP_895060_2806850`) | 11.52 km | 53.3 km² | 0 |
| `de-gerlache-rim` | PSR near de Gerlache (`SP_883120_2691430`) | 12.11 km | 243.4 km² | 0 |

That is a number, but not yet a criterion: no threshold says how close is close
enough, and the product only maps PSRs larger than 5 km². Sub-kilometre PSRs next
to the lit clusters — published values of 30–370 m at the Shackleton rim and
70–100 m on the connecting ridge, quoted per site in [SITES.md](SITES.md) — fall
below that threshold, so the 2.5 km and 11.5 km figures are gaps in the mapped
product as much as they are separations. `experimental_site_ranking` stays off: a
preference with no stated weights is read by a planner, not applied by the build.

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

- Site data are Task 1's published coordinates and LOLA elevations, but the
  terrain is not: Demo Mode skylines are invented, so every percentage in the
  worked example is terrain-limited and not flight-quality.
- Only mapped PSRs larger than 5 km² carry a distance; smaller published PSRs are
  a stated gap rather than a measured separation.
- No power, thermal, communications-link, or Earth-station visibility model; no
  atmospheric refraction (there is no atmosphere).
- The Sun moves only ~0.5°/day in elevation near the pole, so a small ephemeris
  or terrain error can move a grazing sunrise by hours; near-threshold results
  should be treated as ties.
- Thresholds are demonstration values chosen for this challenge build, not
  requirements from a real mission.

## 7. Where the thresholds live

The thresholds live in `config/lunanav.config.json` → `requirements`, served
through `GET /api/config` and evaluated by `POST /api/requirements`, which
checks one scenario against all three gates and reports `met` / `not_met` /
`unknown` per threshold plus a three-state overall verdict. The frontend
mirrors the contract in `frontend/src/types/api.ts` and shows the thresholds on
the methodology page. Every verdict carries the run's provenance level.
The combined specification — sites, requirements, Phase 2 datasets and
sign-off — is collected in [SPECIFICATIONS.md](SPECIFICATIONS.md).
