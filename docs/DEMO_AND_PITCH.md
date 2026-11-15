# Demonstration, video and pitch

This is the repeatable Phase 7 presentation package. Every number comes from the committed JPL Horizons series and LOLA terrain masks; use the live application during the demo and the tables below only as a backup.

## 1. Demonstration scenario

**Mission:** Polar Ice Scout — 7 Earth days, solar-powered robotic lander.

- **Original window:** 1–8 December 2026
- **Delayed window:** 11–18 December 2026
- **Sites:** Shackleton Rim, Connecting Ridge, de Gerlache Rim
- **Requirement targets:** Sun ≥60%, Earth ≥50%, Earth blackout ≤12 h, darkness ≤16 h

### Validated comparison

| Site | Initial Sun / Earth | Delayed Sun / Earth | Initial blackout | Delayed blackout |
| --- | --- | --- | ---: | ---: |
| Shackleton Rim | 0.0% / 0.0% | 0.0% / 0.0% | ≥168.0 h | ≥168.0 h |
| Connecting Ridge | 100.0% / 0.0% | 100.0% / 20.5% | ≥168.0 h | ≥133.5 h |
| de Gerlache Rim | 100.0% / 1.4% | 100.0% / 60.0% | ≥165.7 h | ≥67.2 h |

The delay improves de Gerlache's Earth visibility by **58.7 percentage points** and Connecting Ridge's by **20.5 points**, but both still fail the 12 h blackout target. No site meets every requirement in either window. That is the story: a better date can materially improve communications without turning an unsafe or infeasible site into a winner.

### Presentation sequence

1. **Problem (20 s):** the south pole has attractive science targets but extreme, terrain-controlled Sun and Earth visibility.
2. **Open the planner (10 s):** show the three published candidate sites on the LOLA polar map.
3. **Select Shackleton Rim, 1 Dec 2026, 7 days (20 s):** point out 0% Sun, 0% Earth and the all-dark timeline.
4. **Select Connecting Ridge (20 s):** show 100% Sun but 0% Earth. This is the core trade-off.
5. **Select de Gerlache Rim (20 s):** show 100% Sun and only 1.4% Earth, with a long blackout.
6. **Open Compare scenarios (25 s):** compare two sites over the same window; read the differences, not a winner.
7. **Move to 11 Dec 2026 (25 s):** show de Gerlache reaching 60% Earth and the blackout shrinking to ≥67.2 h.
8. **Open Decision support (20 s):** apply the requirements and show that every candidate remains ineligible; explain FAIL/UNDECIDED rather than forcing a recommendation.
9. **Open Science exploration (15 s):** show the nearest mapped PSR, boundary distance, uncertainty and “Water ice: not assessed.”
10. **Close (10 s):** LunaNav makes the trade-offs visible, with explicit sources and limits. It is decision support, not a flight-certified planner.

### Backup

- Use the **Demo data** mode only if the live providers are unavailable; it is clearly labelled synthetic.
- Keep the local app and both servers ready with `./scripts/dev.sh`.
- Keep [PHASE7_FINAL_VALIDATION.md](PHASE7_FINAL_VALIDATION.md) open for the validated tables.
- Never replace a failed live value with a remembered number during the demo. State that the provider is unavailable and switch to the labelled fallback.

## 2. Video script (approximately 2 minutes 30 seconds)

| Time | Visual | Narration |
| --- | --- | --- |
| 0:00–0:18 | Title / south-pole map | “Landing at the lunar south pole means choosing between sunlight, Earth contact and science. LunaNav makes those trade-offs visible.” |
| 0:18–0:35 | Planner with three sites | “We use NASA JPL Horizons for the Sun and Earth, and LRO LOLA terrain for the actual horizon — not a flat-sphere approximation.” |
| 0:35–1:00 | Shackleton and Connecting Ridge | “Shackleton is dark in this window. Connecting Ridge has continuous sunlight but no direct Earth view. Those are different mission risks.” |
| 1:00–1:25 | de Gerlache and timeline | “de Gerlache has sunlight but only 1.4% Earth visibility on 1 December. The timeline shows the long blackout directly.” |
| 1:25–1:50 | Delay to 11 December | “A ten-day delay raises Earth visibility to 60%, but the blackout is still at least 67 hours. The tool does not hide the remaining failure.” |
| 1:50–2:10 | Decision support and Science | “Requirements stay visible as PASS, FAIL or UNDECIDED. The science layer shows nearby PSRs without claiming water ice or a safe traverse.” |
| 2:10–2:30 | Sources / close | “Every result carries its source, terrain basis and limits. LunaNav is a transparent decision-support prototype, not a NASA-approved or flight-certified system.” |

Record at 1080p, use the deployed URL if available, and add captions. Confirm the current official submission form's video requirement before recording; do not assume the suggested length is an official rule.

## 3. Pitch

### Structure

1. The problem: polar landing sites trade sunlight, Earth contact and science access.
2. Why it is hard: low Sun angles and terrain make a flat horizon wrong.
3. The solution: a browser-based comparison and decision-support tool.
4. How it works: JPL Horizons + LOLA masks + deterministic calculations.
5. Live demonstration: the 1 Dec → 11 Dec de Gerlache scenario.
6. Scientific validation: 1,014 records, 10/10 checks, 13/13 + 6/6 + 8/8 browser matrices.
7. Impact and limits: rapid trade-off exploration, not flight certification.

### Likely judge questions

**Why is the south pole difficult?**
The Sun stays near the horizon, so small terrain features create long shadows, and Earth can be below the local skyline even when it is above a flat horizon.

**How are Sun and Earth positions calculated?**
The committed series comes from NASA JPL Horizons at each site's topocentric observer. An independent Meeus model is used as a cross-check, not as the source of the displayed records.

**Does the model account for terrain?**
Yes for the three candidates: a 360-point LOLA horizon mask uses 5 m/pixel data near the site and 80 m/pixel data out to 150 km. Other coordinates are labelled geometric-only.

**How accurate is it?**
The committed records agree with the independent model within 0.032° elevation and 0.020° azimuth. The PSR boundary uncertainty is ±60 m at candidate latitudes. These are model/data uncertainties, not a landing-safety guarantee.

**Does Earth visibility mean communications work?**
No. It is direct line of sight. The link-budget panel adds representative antenna and power assumptions; it is not a negotiated DSN service or a flight RF analysis.

**How is the best site chosen?**
It is not chosen automatically. Users set requirements and weights; only eligible candidates are ranked, and FAIL or UNDECIDED is never counted as a pass.

**What about water ice?**
Nearby PSRs are investigation leads. The committed data does not establish ice concentration, depth or temperature; the app reports `not_assessed`.

**What is the biggest limitation?**
The terrain horizon is authoritative at the mapped sites, but the 3D shadow view is illustrative and PSRs below 5 km² are absent. The product is decision support, not a flight-certified mission planner.

**What would you improve next?**
More validated landing sites, higher-fidelity terrain and thermal models, live link-budget validation, and a formal low-end device performance benchmark.

## 4. What not to claim

- Do not claim NASA approval, certification, partnership or operational adoption.
- Do not claim confirmed water ice, ice concentration or a safe traverse.
- Do not call the 3D shadow preview the visibility calculation.
- Do not present the hypothetical power/link assumptions as measured hardware.
- Do not say the project is deployed or submitted until the public URL and submission confirmation exist.
