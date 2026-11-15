# Submission packet

**Project:** LunaNav — Lunar Landing Site Navigator
**Challenge:** NASA Space Apps Challenge 2026 — Lunar Landing Site Navigator
**Repository:** <https://github.com/OstCoder/NasaSAC26>
**Validation date:** 14 November 2026

## Status

| Item | Status |
| --- | --- |
| Working application | Verified locally |
| Scientific validation | Passed (10/10 data checks; 13/13 + 6/6 + 8/8 browser matrices) |
| GitHub repository | Public |
| Public deployment | **Not yet deployed** |
| Demonstration video | **Not yet recorded** |
| Official Project tab | **Not yet submitted** |
| Submission confirmation | **Not yet available** |

Do not mark the official submission complete from this packet alone. The current Project tab on the registered team page determines the required fields and media.

## Proposed submission text

### Short description

LunaNav is an interactive lunar south-pole landing-site explorer. It combines NASA JPL Horizons Sun/Earth geometry with LRO LOLA terrain to show when a candidate site has sunlight, direct Earth visibility and usable mission windows — and how those conditions change when a landing is delayed.

### Full description

Landing near the lunar south pole requires balancing competing conditions: the Sun stays close to the horizon, terrain can block it for long periods, and Earth may be below the local skyline even when a flat-horizon calculation says it is visible. LunaNav turns those conditions into an explorable decision-support workspace.

For three published candidate sites — Shackleton Rim, Connecting Ridge and de Gerlache Rim — the application displays terrain-adjusted Sun and Earth visibility, 360° horizon profiles, visibility timelines, mission metrics, side-by-side comparisons, landing-delay analysis and adjustable mission requirements. A transparent decision-support view ranks only candidates that satisfy the selected requirements; FAIL and UNDECIDED remain visible. A science view adds mapped PSRs and explicitly reports water ice as `not_assessed`.

The astronomical records come from NASA JPL Horizons, and the terrain masks and PSR catalogue come from LRO LOLA/LROC data. The committed series contains 1,014 hourly records across both mission windows. Independent checks agree within 0.032° in elevation and 0.020° in azimuth. The app labels geometric-only results, missing data and every modelling assumption rather than filling gaps with invented values.

LunaNav is a prototype decision-support tool, not a NASA-approved, flight-certified or landing-safety system. It is designed to make trade-offs understandable and reproducible for judges, students and mission planners.

## Links and credits

- **GitHub:** <https://github.com/OstCoder/NasaSAC26>
- **Public app:** To be added after deployment (see [DEPLOYMENT.md](DEPLOYMENT.md)).
- **Video:** To be added after recording.
- **Validation evidence:** [PHASE7_FINAL_VALIDATION.md](PHASE7_FINAL_VALIDATION.md)
- **Data and licenses:** [ATTRIBUTION.md](ATTRIBUTION.md)
- **Demo script and pitch:** [DEMO_AND_PITCH.md](DEMO_AND_PITCH.md)
- **Team:** OstCoder and Aarush Gutha (repository history)
- **Code license:** MIT

## Required-field checklist

- [x] Project title
- [x] Challenge selection
- [x] Problem and proposed solution
- [x] How the application works
- [x] GitHub repository URL
- [x] Scientific references and data sources
- [x] License and attribution
- [ ] Public website URL
- [ ] Demonstration video / media link, if required
- [ ] Confirmed team-member list on the registered team page
- [ ] Official Project tab reviewed in the current event UI
- [ ] Submission completed
- [ ] Submission status verified

## Final submission procedure

1. Deploy using [DEPLOYMENT.md](DEPLOYMENT.md).
2. Put the public URL and deployment commit SHA in this packet and the README.
3. Run the public workflow in a private window and on a second device.
4. Record the demonstration using [DEMO_AND_PITCH.md](DEMO_AND_PITCH.md); verify the current official media requirements.
5. Open the registered team page and review the current Project tab.
6. Confirm every team member, link, reference and license field.
7. Submit before **15 November 2026, 11:59 PM local time**.
8. Open every public link in a private window and save the submission confirmation.
9. Keep a backup of the final repository, screenshots, video and submission receipt.

Official event information: <https://www.spaceappschallenge.org/2026/>
