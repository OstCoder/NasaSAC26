# Engineering budgets: power, link and the mission report (Phase 5)

The project's visibility work says *when* the Sun and Earth clear the terrain.
Phase 5 answers the two questions a reviewer asks next: **can the lander keep
running**, and **can it talk**. Both answers are textbook engineering formulas
applied to committed geometry, with every assumption printed next to the number.

- Code: `backend/app/services/engineering.py`, `backend/app/services/report_export.py`
- Endpoints: `GET /api/engineering`, `GET /api/mission-report.md`
- Tests: `backend/tests/test_engineering.py`
- Acceptance: `npm run acceptance:phase5` ([docs/PHASE5_ACCEPTANCE.md](PHASE5_ACCEPTANCE.md))
- Assumptions: `config/lunanav.config.json -> power / link`

## Power

```text
irradiance  = S * (1 AU / sun_range)^2          S = 1361 W/m2, range from the series
conversion  = A * eta_cell * packing * harness   A = 2 m2, 30 % cells
incidence   = sin(elevation)   fixed horizontal array
            = cos(elevation)   vertical array, azimuth-tracking
            = sin(tilt)*cos(el)*cos(sun_az - panel_az) + cos(tilt)*sin(el)
                               arbitrary fixed tilt/azimuth
P           = irradiance * conversion * incidence, zero when terrain blocks the Sun
```

At the lunar south pole the Sun never rises more than ~2°, so `sin(elevation)` is
~0.03 and `cos(elevation)` is ~1. The reference designs are reported side by side
because that is the design decision: a horizontal array is nearly useless at
these sites, and a vertical, Sun-tracking array is not. On the committed data the
vertical array produces ~118 kWh over a 168 h window where the horizontal array
produces ~2.5–4.5 kWh.

`GET /api/engineering?panel_design=fixed&panel_tilt_deg=45&panel_azimuth_deg=180`
adds a third, user-selected design. Tilt 0° is horizontal, 90° is vertical; azimuth
is the direction the panel faces, 0° north and clockwise. The selected design
drives the battery, `series` and `sensitivity`; the two reference designs stay in
`designs` for comparison. This is an orientation calculator, not an optimizer.
The decision API accepts the same three fields so a ranking can use the chosen
array rather than a hidden default.

Energy is a left-rectangle sum over the stored hourly samples, so its error is the
step, not a numerical-integration guarantee. The battery is stepped through the
same samples: charge above the depth-of-discharge floor is clamped to capacity,
charge below it is counted as **unserved load** rather than spent. A site whose
skyline blocks the Sun for the whole window (Shackleton Rim, 9.43° obstruction)
therefore reports zero array energy, a depleted battery and the exact unserved
energy — not an optimistic average.

### Per-sample trace and energy timeline

`power.series` repeats the same UTC samples as the scenario (169 hourly points
for a committed seven-day window), with the selected array's
`solar_w`, the flat `load_w`, `battery_wh`, `battery_soc_pct`, `sun_visible`,
`charging`/`discharging` flags and cumulative `unserved_wh`. `power.extremes`
gives the minimum battery and its index plus the count and duration of samples
whose array output is below load.

The power panel's **Energy timeline** draws this trace. Shaded spans are the
`sun_visible == false` samples, not a second irradiance model. The load line,
battery reserve line and minimum marker are explicit, and the tooltip repeats the
measured sample values. The chart is absent, with a status message, if the arrays
are not aligned. The summary table and verdict remain the source of truth for the
budget numbers.

### Sensitivity

`power.sensitivity` runs seven deterministic cases: base, solar conversion
±10 %, load ±20 % and battery capacity ±10 %. Each case changes one assumption
and re-runs the same battery model; the result carries array energy, minimum SOC,
unserved load and reserve status, plus the SOC range. It is a bounded
one-at-a-time check, not a probability distribution, and correlations are not
modelled. The power panel exposes the table and its limits.

## Mission-delay power comparison

`POST /api/reschedule` compares the original and proposed scenario using the same
requirement evaluator and, when it can, the same power model. `requirements`
contains both check sets, the new failures and the improvements. `power` contains
both `DecisionPower` summaries and deltas for array energy, net energy, minimum
battery and unserved load.

This comparison is deliberately narrow. It is available only when:

- the location is a catalogue site (custom coordinates have no committed series);
- both landing times are exactly the committed 1 Dec and 11 Dec 2026 windows;
- the requested duration is the committed 168 h window.

Otherwise `power.available` is false and the response explains why. No power curve
is interpolated, extrapolated or fabricated for another date or duration. The
visibility and requirement comparison still runs for every supported scenario.

## Link

```text
lambda = c / f                                      f = 8.4 GHz
FSPL   = 20 log10(4 pi d / lambda)                  d = committed Earth range
G_rx   = 10 log10(eta_ap * (pi D / lambda)^2)       D = 34 m dish
G/T    = G_rx - 10 log10(T_sys)                     T_sys = 25 K
EIRP   = 10 log10(P_tx) + G_tx - L_impl
C/N0   = EIRP - FSPL + G/T + 228.6                  (Boltzmann in dB)
rate   = C/N0 - Eb/N0_required                      in dB-Hz, at 9.6 dB
```

Only samples with terrain-adjusted Earth line of sight contribute; blocked
samples are zero rate, not an average. The response keeps the **best** and
**worst** case (nearest and farthest Earth) with the margin, the closing verdict,
and a data-volume **bound** — the link running for every visible second at the
supported peak rate, before recorder limits and station scheduling.

With the committed ranges (376,000–406,000 km) and these assumptions the link
closes with ~72 dB of margin, at up to ~16 Mbps. That is what the formulas say
for a 5 W transmitter into an 18 dBi antenna and a 34 m dish; it is not a
negotiated DSN pass, and the response says so.

## The Markdown report

`GET /api/mission-report.md?site_id=<id>&window=initial|alternative` renders the
Phase 3 envelope plus both budgets as one readable document: terrain basis and
coverage, visibility table, requirement checks, power table and battery verdict,
link cases, assumptions, provenance, and an explicit "what this report does not
claim" list. No wall clock and no random ordering, so the same committed inputs
produce the same bytes; a test asserts it and checks the required headings.

## What is deliberately not modelled

- **No power hardware.** Efficiency, packing, harness loss, load and battery size
  are config values, not measured hardware. No temperature derating, dust,
  degradation or partial shading.
- **No RF detail.** No atmospheric/ionospheric loss, polarization, pointing,
  scintillation, coding gain curves or interference. One representative
  modulation and required Eb/N0.
- **No operations.** No recorder limits, station schedule, light-time,
  thermal constraints or downlink duty cycle. The data volume is a bound.
- **No probability distribution.** The sensitivity cases are deterministic
  one-at-a-time bounds, not a Monte Carlo or correlated uncertainty model.
- **No ranking here.** These are budgets for one site and window. The separate
  decision service applies eligibility and transparent ranking; the budget page
  does not recommend a landing site.
