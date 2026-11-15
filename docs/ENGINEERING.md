# Engineering budgets: power, link and the mission report (Phase 5)

The project's visibility work says *when* the Sun and Earth clear the terrain.
Phase 5 answers the two questions a reviewer asks next: **can the lander keep
running**, and **can it talk**. Both answers are textbook engineering formulas
applied to committed geometry, with every assumption printed next to the number.

- Code: `backend/app/services/engineering.py`, `backend/app/services/report_export.py`
- Endpoints: `GET /api/engineering`, `GET /api/mission-report.md`
- Tests: `backend/tests/test_engineering.py`
- Assumptions: `config/lunanav.config.json -> power / link`

## Power

```text
irradiance  = S * (1 AU / sun_range)^2          S = 1361 W/m2, range from the series
conversion  = A * eta_cell * packing * harness   A = 2 m2, 30 % cells
incidence   = sin(elevation)   fixed horizontal array
            = cos(elevation)   vertical array, azimuth-tracking
P           = irradiance * conversion * incidence, zero when terrain blocks the Sun
```

At the lunar south pole the Sun never rises more than ~2°, so `sin(elevation)` is
~0.03 and `cos(elevation)` is ~1. The two designs are reported side by side
because that is the design decision: a horizontal array is nearly useless at
these sites, and a vertical, Sun-tracking array is not. On the committed data the
vertical array produces ~118 kWh over a 168 h window where the horizontal array
produces ~2.5–4.5 kWh.

Energy is a left-rectangle sum over the stored hourly samples, so its error is the
step, not a numerical-integration guarantee. The battery is stepped through the
same samples: charge above the depth-of-discharge floor is clamped to capacity,
charge below it is counted as **unserved load** rather than spent. A site whose
skyline blocks the Sun for the whole window (Shackleton Rim, 9.43° obstruction)
therefore reports zero array energy, a depleted battery and the exact unserved
energy — not an optimistic average.

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
- **No ranking.** These are budgets for one site and window. They do not rank
  candidates or recommend a landing site.
