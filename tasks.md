
# Phase 7 — Final Validation, Deployment & Submission

> **Status (14 Nov 2026): local release validation complete.** Application readiness, scientific validation, automated tests, performance, repository cleanup and presentation materials have been verified locally. Public deployment, a recorded video, team rehearsal and the official NASA submission remain open because they require hosting credentials, recorded media or the registered team account. See [docs/PHASE7_FINAL_VALIDATION.md](docs/PHASE7_FINAL_VALIDATION.md).

## Objective

Finalize, validate, deploy, demonstrate, and submit
our Lunar Landing Site Navigator for the
NASA Space Apps Challenge 2026.

Combine the work completed in Phases 1–6 into
one reliable, publicly accessible application.

Ensure that the final project:

1. Addresses NASA's lunar landing-site challenge.
2. Uses scientifically grounded astronomical data.
3. Provides accurate and understandable visualizations.
4. Supports landing-site and date comparisons.
5. Explains mission-planning trade-offs.
6. Clearly documents scientific assumptions.
7. Includes a working demonstration.
8. Meets official NASA Space Apps submission requirements.

By the end of Phase 7, our project should be
deployed, documented, demonstrated, and submitted.

---

## Task 1: Finalize the Core Application

- [x] Review all completed features from Phases 1–6.
- [x] Identify unfinished or unstable functionality.
- [x] Prioritize fixing critical issues over adding features.
- [x] Confirm all three landing sites are supported.
- [x] Verify landing-site selection works.
- [x] Verify date selection works.
- [x] Verify mission duration controls work.
- [x] Verify Sun position calculations are displayed.
- [x] Verify Earth position calculations are displayed.
- [x] Verify sunlight and communication timelines work.
- [x] Verify site comparisons work.
- [x] Verify mission-delay comparisons work.
- [x] Verify mission requirements can be evaluated.
- [x] Remove or disable incomplete features.
- [x] Ensure the application operates without crashes.

### Required Core Features

The final application should allow users to:

1. Select a lunar landing site.
2. Choose a landing date and mission duration.
3. View Sun and Earth positions.
4. Examine visibility windows.
5. Compare different landing sites.
6. Compare different landing dates.
7. Understand relevant mission constraints.

### Important

A reliable application with fewer features
is preferable to a visually impressive
application that produces incorrect results.

Do not add unfinished capabilities to the
final presentation as if they are working.

### Deliverable

A feature-complete and stable version
of the Lunar Landing Site Navigator.

---

## Task 2: Validate Scientific Accuracy

- [x] Verify all landing coordinates.
- [x] Verify coordinate reference systems.
- [x] Verify lunar longitude conventions.
- [x] Confirm observer locations are on the Moon.
- [x] Verify JPL Horizons integration.
- [x] Check Sun azimuth and elevation calculations.
- [x] Check Earth azimuth and elevation calculations.
- [x] Verify UTC timestamp handling.
- [x] Test geometric horizon calculations.
- [x] Test terrain horizon calculations if supported.
- [x] Validate sunlight availability percentages.
- [x] Validate Earth visibility percentages.
- [x] Validate longest darkness calculations.
- [x] Validate maximum communication blackouts.
- [x] Validate simultaneous visibility calculations.
- [x] Validate mission-delay comparisons.
- [x] Verify missing-data handling.
- [x] Check model assumptions and limitations.

### Scientific Validation Requirements

For each selected landing site:

- Confirm coordinates against the recorded source.
- Compare sample ephemeris values with JPL Horizons.
- Check that azimuth and elevation conventions match.
- Ensure time intervals are calculated consistently.
- Verify visibility transitions when possible.
- Verify terrain-adjusted calculations separately.

### Important Distinctions

Sun Visibility:
Indicates whether the Sun is geometrically
or terrain-wise visible.

Solar Power:
Depends on panel orientation, efficiency,
incident sunlight, and spacecraft hardware.

Earth Visibility:
Indicates whether a direct line of sight
toward Earth is geometrically available.

Communication Availability:
Also depends on the spacecraft antenna,
radio hardware, link budget, and other factors.

PSR Proximity:
Indicates geographic distance to a mapped
permanently shadowed region.

Water-Ice Confirmation:
Requires separate scientific evidence.

### Deliverable

A scientifically validated application
with documented calculation methods,
sources, assumptions, and limitations.

---

## Task 3: Run Automated Backend Tests

- [x] Run all astronomy data integration tests.
- [x] Run Sun visibility calculation tests.
- [x] Run Earth visibility calculation tests.
- [x] Run terrain horizon tests when supported.
- [x] Run visibility window detection tests.
- [x] Run simultaneous visibility tests.
- [x] Run mission constraint evaluation tests.
- [x] Run mission-delay comparison tests.
- [x] Run solar power simulation tests if implemented.
- [x] Run battery simulation tests if implemented.
- [x] Run PSR proximity tests if implemented.
- [x] Fix failing tests.
- [x] Confirm no hardcoded demonstration values
      are presented as actual scientific results.
- [x] Record the final test outcomes.

### Suggested Commands

```bash
cd backend

python -m pytest
```

If using unittest:

```bash
python -m unittest discover
```

Use the test framework actually configured
in the project.

### Important Test Cases

Test 1:
Sun elevation above the applicable horizon.

Expected:
Sun visibility is True.

Test 2:
Earth elevation below the applicable horizon.

Expected:
Earth visibility is False.

Test 3:
Communication blackout exceeds allowed duration.

Expected:
Mission communication constraint fails.

Test 4:
Required scientific data is missing.

Expected:
The result is UNKNOWN or unavailable.

Test 5:
Mission date changes.

Expected:
The application evaluates the new date range
rather than reusing outdated results.

### Deliverable

A backend test suite with no unresolved
critical failures and documented results.

---

## Task 4: Test the Complete Website

- [x] Open the website in a browser.
- [x] Select Site A and run an analysis.
- [x] Select Site B and run an analysis.
- [x] Select Site C and run an analysis.
- [x] Change the landing date.
- [x] Change the mission duration.
- [x] Test Sun and Earth position visualizations.
- [x] Test visibility timelines.
- [x] Test site comparison charts.
- [x] Test mission requirement controls.
- [x] Test mission-delay comparisons.
- [x] Test the time slider and animations.
- [x] Test PSR map overlays if implemented.
- [x] Test optional 3D terrain functionality.
- [x] Test unavailable datasets.
- [x] Test invalid user inputs.
- [x] Test frontend loading states.
- [x] Test API failure handling.
- [x] Test mobile and desktop layouts.
- [x] Check browser console errors.

### Critical End-to-End Test

1. Open the Lunar Landing Site Navigator.
2. Select Shackleton Rim.
3. Set the landing date to December 1, 2026.
4. Set the mission duration to seven days.
5. Run the mission analysis.
6. Examine Sun and Earth visibility results.
7. Compare Shackleton Rim with Connecting Ridge.
8. Change the landing date to December 11, 2026.
9. Compare the original and delayed scenarios.
10. Review mission feasibility results.

All supported interactions should function
without crashes or misleading measurements.

### Deliverable

An end-to-end tested website that successfully
demonstrates the central NASA challenge.

---

## Task 5: Optimize Website Performance

- [x] Measure application loading performance.
- [x] Optimize unnecessary backend requests.
- [x] Cache previously computed ephemeris results.
- [x] Optimize large lunar imagery assets.
- [x] Optimize terrain data loading.
- [x] Reduce unnecessary React rendering.
- [x] Ensure charts remain responsive.
- [x] Test animation performance if implemented.
- [x] Provide loading indicators.
- [x] Provide clear errors when requests fail.
- [x] Confirm the application handles
      multiple consecutive user interactions.
- [x] Test the application on slower connections.
- [x] Ensure advanced features do not block
      the core mission dashboard.

### Performance Priorities

1. Reliable initial page loading.
2. Responsive site selection.
3. Accurate and timely analysis results.
4. Smooth interaction with charts.
5. Stable mission comparison functionality.

### Deliverable

A responsive website suitable for
public demonstration and judging.

---

## Task 6: Deploy the Application

- [x] Choose a frontend hosting platform.
- [x] Choose a backend hosting platform.
- [ ] Configure production environment variables.
- [ ] Deploy the backend application.
- [ ] Deploy the frontend application.
- [ ] Configure the production API URL.
- [ ] Configure CORS for the deployed frontend.
- [x] Verify all required scientific data is available.
- [ ] Confirm production API endpoints respond.
- [ ] Test the complete application after deployment.
- [x] Check for exposed secrets or API credentials.
- [ ] Confirm the public website requires no login.
- [ ] Test the website from another device.
- [ ] Verify the deployment URL is stable.
- [x] Prepare a fallback demonstration if necessary.

### Suggested Hosting

Frontend:
Vercel or Netlify

Backend:
Render, Railway, or another Python-compatible host

Repository:
GitHub

### Example Environment Configuration

```text
Frontend:
VITE_API_BASE_URL=<production-backend-url>

Backend:
ALLOWED_ORIGINS=<production-frontend-url>
```

Set real deployment values in environment
configuration rather than committing secrets.

### Important

A deployment is not complete simply because
the hosting platform reports success.

Open the public URL and run the actual
mission-analysis workflow.

If the backend has cold starts or external
API dependencies, ensure the demo remains
usable under expected conditions.

### Deliverable

A publicly accessible deployment of
the Lunar Landing Site Navigator.

---

## Task 7: Finalize the GitHub Repository

- [x] Ensure the latest working code is committed.
- [x] Confirm frontend and backend code is included.
- [x] Remove unnecessary temporary files.
- [x] Remove debugging code where appropriate.
- [x] Verify no credentials are committed.
- [x] Verify the .gitignore configuration.
- [x] Add or verify dependency files.
- [x] Add clear installation instructions.
- [x] Document how to run the backend.
- [x] Document how to run the frontend.
- [x] Document how to execute tests.
- [ ] Add the public deployment link.
- [x] Add scientific data-source references.
- [x] Add license information.
- [x] Confirm all team contributions are preserved.
- [x] Make the repository publicly accessible
      if required by official submission rules.

### Suggested Repository Structure

```text
lunar-landing-site-navigator/
├── frontend/
│   ├── src/
│   └── package.json
│
├── backend/
│   ├── services/
│   ├── data/
│   ├── tests/
│   └── requirements.txt
│
├── docs/
│   ├── PHASE_1.md
│   ├── PHASE_2.md
│   ├── PHASE_3.md
│   ├── PHASE_4.md
│   ├── PHASE_5.md
│   ├── PHASE_6.md
│   └── PHASE_7.md
│
├── assets/
│   └── screenshots/
│
├── LICENSE
├── .gitignore
└── README.md
```

### Deliverable

A clean, documented GitHub repository
containing the project's code and resources.

---

## Task 8: Write the Final Project README

- [x] Add the project name.
- [x] Add a concise project description.
- [x] Explain the lunar landing-site problem.
- [x] Describe the proposed solution.
- [x] List the application's main features.
- [x] Explain the technology stack.
- [x] Describe the architecture.
- [x] Document NASA data sources.
- [x] Explain key scientific calculations.
- [x] List assumptions and limitations.
- [x] Include installation instructions.
- [x] Include local development commands.
- [ ] Include the deployment URL.
- [x] Add screenshots of the website.
- [x] Include team contribution information.
- [x] Include license and attribution information.

### Suggested README Sections

# Lunar Landing Site Navigator

## Overview

## The Problem

## Our Solution

## Key Features

## Scientific Methodology

## NASA Data Sources

## Technology Stack

## System Architecture

## Installation

## Running Locally

## Testing

## Screenshots

## Limitations

## Team

## License and Credits

### Suggested Project Description

Lunar Landing Site Navigator is an interactive
mission-planning application that helps users
compare lunar south-pole landing sites and
mission dates.

The application uses NASA-derived astronomical
data to visualize Sun and Earth positions,
estimate visibility windows, and evaluate
hypothetical operational requirements.

It helps users understand trade-offs between
solar illumination, direct-to-Earth communication,
and scientific exploration opportunities.

### Deliverable

A complete, professional README that allows
judges and developers to understand and
reproduce the project's main functionality.

---

## Task 9: Document Scientific Sources and Attribution

- [x] List all NASA datasets used.
- [x] List all space agency partner resources used.
- [x] Document JPL Horizons usage.
- [x] Document lunar imagery sources.
- [x] Document terrain elevation sources.
- [x] Document PSR data sources if applicable.
- [x] Include relevant dataset names and versions.
- [x] Include access dates when applicable.
- [x] Document third-party software dependencies.
- [x] Check licenses for images and datasets.
- [x] Check licenses for libraries and other assets.
- [x] Include appropriate scientific references.
- [x] Distinguish NASA data from our own calculations.
- [x] Avoid suggesting NASA endorses the application.

### Primary Scientific Resources

NASA JPL Horizons:
https://ssd.jpl.nasa.gov/horizons/

NASA LROC QuickMap:
https://quickmap.lroc.asu.edu/

NASA Moon Trek:
https://trek.nasa.gov/moon/

NASA LOLA Topography:
https://pgda.gsfc.nasa.gov/products/78

Canadian Space Agency Moon Exploration:
https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/

### Important

Only claim to have used a dataset if it was
actually integrated into the project.

Do not list a resource as a computational data
source if it was only consulted for background
research.

Properly attribute all third-party materials
and follow their license and usage requirements.

### Deliverable

A complete scientific references,
data attribution, and licensing section.

---

## Task 10: Prepare the Demonstration Scenario

- [x] Choose a representative landing site.
- [x] Choose the initial mission date.
- [x] Choose the delayed mission date.
- [x] Select at least one alternative landing site.
- [x] Generate validated analysis results.
- [x] Identify meaningful differences between scenarios.
- [x] Prepare the exact demonstration sequence.
- [x] Verify every visualization used in the demo.
- [x] Prepare a backup set of precomputed results.
- [x] Avoid using invented measurements as real data.
- [ ] Practice navigating the website.
- [ ] Test the demonstration on the deployed version.

### Recommended Demo Scenario

Mission:
Polar Ice Scout

Mission Duration:
7 Earth days

Original Landing Date:
December 1, 2026

Delayed Landing Date:
December 11, 2026

Landing Sites:
Shackleton Rim, Connecting Ridge,
and de Gerlache Rim.

### Demonstration Sequence

Step 1:
Introduce the lunar south-pole landing challenge.

Step 2:
Select the original landing site and date.

Step 3:
Display Sun and Earth visibility windows.

Step 4:
Show sunlight and communication metrics.

Step 5:
Introduce a ten-day landing delay.

Step 6:
Compare the changed conditions.

Step 7:
Evaluate alternative landing locations.

Step 8:
Explain the operational trade-offs.

Step 9:
Show nearby PSRs if the science layer is ready.

Step 10:
Summarize what the mission planner learned.

### Important

Use results actually produced by the
application during the demonstration.

If the analysis reveals no meaningful difference
for a selected example, use another verified
scenario rather than manipulating measurements.

### Deliverable

A complete, repeatable demonstration that
shows the practical value of the application.

---

## Task 11: Create a Project Demonstration Video

- [ ] Verify current video requirements in the
      official NASA Space Apps submission form.
- [ ] Choose the appropriate video length.
- [ ] Prepare a concise presentation script.
- [ ] Record the working website.
- [ ] Demonstrate landing-site selection.
- [ ] Demonstrate Sun and Earth visualization.
- [ ] Demonstrate landing-site comparison.
- [ ] Demonstrate mission-delay analysis.
- [ ] Explain the scientific data sources.
- [ ] Explain what makes the application useful.
- [ ] Include optional PSR analysis if completed.
- [ ] Edit for clarity and pacing.
- [ ] Add readable captions if possible.
- [ ] Verify audio and video quality.
- [ ] Upload the video if required or useful.
- [ ] Confirm judges can access the video link.
- [ ] Review applicable NASA media and
      minor-participant rules.

### Suggested 2–3 Minute Demo Structure

0:00–0:20
Explain the problem.

0:20–0:40
Introduce the Lunar Landing Site Navigator.

0:40–1:20
Demonstrate landing-site selection and
Sun/Earth visibility.

1:20–1:50
Compare landing dates and alternatives.

1:50–2:15
Explain mission feasibility and recommendations.

2:15–2:40
Discuss scientific value and unique features.

2:40–3:00
Summarize impact and limitations.

This is a suggested presentation structure,
not an official NASA video duration requirement.

### Deliverable

A clear demonstration video that communicates
the project's purpose, implementation, and impact.

---

## Task 12: Prepare the Final Pitch

- [x] Explain the problem in simple language.
- [x] Identify the intended users.
- [x] Explain how the application solves the problem.
- [x] Describe the scientific foundation.
- [x] Highlight key features.
- [x] Demonstrate actual functionality.
- [x] Explain what differentiates the project.
- [x] Describe potential real-world impact.
- [x] Acknowledge current limitations.
- [x] Prepare answers to technical questions.
- [ ] Practice as a team.
- [ ] Verify the pitch fits any local event time limit.

### Suggested Pitch Structure

1. The Problem
2. Why the Lunar South Pole Is Challenging
3. Our Solution
4. How the System Works
5. Live Demonstration
6. Scientific Validation
7. Impact and Future Improvements

### Questions Judges May Ask

- Why is landing near the lunar south pole difficult?
- How does your website calculate Sun positions?
- How do you calculate Earth visibility?
- Does your model account for lunar terrain?
- How accurate are your visibility predictions?
- Why is your application better for rapid comparisons?
- How do you evaluate mission delays?
- How do you determine which site is preferable?
- How does the application support water-ice research?
- What are your biggest scientific limitations?
- What would you improve with more time?

### Important

Be prepared to explain the difference between
a scientifically informed decision-support tool
and a flight-certified mission planning system.

Do not claim NASA approval, certification,
or operational adoption.

### Deliverable

A practiced project pitch supported by
a reliable working demonstration.

---

## Task 13: Complete the Official NASA Submission

- [ ] Log in to the NASA Space Apps website.
- [ ] Open the registered team page.
- [ ] Navigate to the Project tab.
- [ ] Review the current submission instructions.
- [ ] Confirm the project title.
- [ ] Confirm the selected challenge.
- [ ] Confirm all team members are listed.
- [ ] Complete required project description fields.
- [ ] Explain the problem and proposed solution.
- [ ] Describe how the application works.
- [ ] Provide the public website URL.
- [ ] Provide the GitHub repository URL.
- [ ] Add video or presentation links as requested.
- [ ] Include scientific references and data sources.
- [ ] Complete all required licensing fields.
- [ ] Verify any additional required information.
- [ ] Review the entire submission.
- [ ] Submit before the official deadline.
- [ ] Verify the submission status afterward.

### Official Event Information

Event:
NASA Space Apps Challenge 2026

Hackathon:
November 14–15, 2026

Submission Deadline:
November 15, 2026, 11:59 PM local time

Submission Location:
Project tab on the registered team's page.

Official Website:
https://www.spaceappschallenge.org/2026/

### Important

The current official Project tab determines
the exact required fields and accepted media.

Do not assume requirements from older
NASA Space Apps submission guides.

Submitting successfully is separate from
deploying the application or pushing code.

### Deliverable

A completed NASA Space Apps project submission,
with accessible project materials and verified
submission status.

---

## Task 14: Verify the Final Submission

- [ ] Confirm the project appears on the team page.
- [ ] Confirm the submission is marked appropriately.
- [ ] Open the public website link.
- [ ] Open the GitHub repository link.
- [ ] Open the demonstration video link.
- [ ] Test links in a private browser window.
- [ ] Confirm no login is required to view public materials.
- [ ] Confirm all required project fields are complete.
- [ ] Verify references and credits are present.
- [ ] Check the final project description for errors.
- [ ] Check all team members are included.
- [ ] Save the submission confirmation.
- [ ] Keep a backup of the final project materials.

### Final Verification Questions

1. Can judges open our website?
2. Can judges access our GitHub repository?
3. Can judges understand what problem we solved?
4. Can judges see the application working?
5. Are our scientific measurements supported by data?
6. Are our assumptions and limitations clear?
7. Are all required submission fields complete?
8. Has the project actually been submitted?

### Deliverable

A verified final submission with all necessary
project links and documentation accessible.

---

## Phase 7 Completion Checklist

### Application Readiness

- [x] Core application complete.
- [x] Astronomical calculations verified.
- [x] Landing-site comparisons working.
- [x] Mission-delay comparisons working.
- [x] Scientific assumptions documented.
- [x] No unresolved critical bugs.
- [x] Backend tests passing.
- [x] Frontend testing completed.

### Deployment Readiness

- [ ] Frontend deployed.
- [ ] Backend deployed.
- [ ] Production API connected.
- [ ] Public website tested.
- [x] No exposed secrets.
- [ ] Deployment URL confirmed.
- [x] Fallback demo available.

### Documentation Readiness

- [x] README completed.
- [x] Architecture documented.
- [x] Data sources cited.
- [x] Scientific methodology documented.
- [x] Limitations documented.
- [x] License information included.
- [x] Repository prepared for judging.

### Presentation Readiness

- [x] Demonstration scenario prepared.
- [ ] Live demo tested.
- [ ] Video created if required.
- [x] Pitch prepared.
- [ ] Team members understand the project.
- [x] Technical questions reviewed.

### Submission Readiness

- [ ] Official requirements checked.
- [ ] Project page completed.
- [ ] Team members listed.
- [x] GitHub link included.
- [ ] Deployment link included.
- [ ] Required media links included.
- [x] References included.
- [ ] Final submission completed.
- [ ] Submission status verified.

---

## Project Success Criteria

Our Lunar Landing Site Navigator should
successfully demonstrate the following:

1. Select real lunar south-pole locations.

2. Retrieve or use verified Sun and Earth
   ephemeris data from JPL Horizons.

3. Visualize Sun and Earth positions
   relative to the lunar horizon.

4. Calculate sunlight and Earth
   visibility windows.

5. Compare multiple landing locations
   and mission dates.

6. Evaluate selected mission constraints.

7. Explain operational trade-offs
   using understandable measurements.

8. Optionally connect landing-site choices
   with nearby permanently shadowed regions.

9. Clearly communicate data quality,
   assumptions, and scientific limitations.

10. Provide a working, publicly accessible
    demonstration and complete submission.

---

## Official NASA Space Apps Resources

### NASA Space Apps Challenge 2026
https://www.spaceappschallenge.org/2026/

Official event information and project submission.

### NASA LROC QuickMap
https://quickmap.lroc.asu.edu/

Lunar imagery, site selection, and terrain data.

### NASA Moon Trek
https://trek.nasa.gov/moon/

Lunar terrain visualization and geographic context.

### NASA JPL Horizons
https://ssd.jpl.nasa.gov/horizons/

Astronomical calculations for the Sun and Earth.

### NASA LOLA South-Pole Topography
https://pgda.gsfc.nasa.gov/products/78

Lunar elevation data for terrain analysis.

### Canadian Space Agency — Moon Exploration
https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/

Lunar exploration background and mission context.

### NASA Space Apps Legal Information
https://www.spaceappschallenge.org/legal/

Licensing, references, and submission-related terms.

---

## Expected Final Outcome

By completing Phase 7, our team should have:

1. A stable Lunar Landing Site Navigator website.
2. Scientifically validated visibility calculations.
3. Functional lunar site and date comparisons.
4. Mission-planning decision-support features.
5. Clear scientific data attribution.
6. A public deployment.
7. A documented GitHub repository.
8. A prepared project demonstration.
9. A concise presentation of the project's impact.
10. A verified NASA Space Apps submission.

Phase 7 is complete only when the project
has been tested, deployed, documented,
and successfully submitted.

The final application should demonstrate
how NASA-derived data can help users
understand the trade-offs between lunar
sunlight conditions, Earth communication,
mission schedules, and scientific exploration.

Our project is a prototype decision-support
tool, not an officially approved or
flight-certified NASA mission system.

---

## Night upgrades (autonomous, 15 Nov 2026)

> Working autonomously overnight. Each item is committed individually so a
> second agent can resume mid-flight. Statuses are updated as work lands.

### UI overhaul (in progress: Phase 1)

> Follows docs/UI_OVERHAUL_PHASES.md. Less text-heavy, more clickable, smooth CSS
> transitions, accessible, NASA-guideline aligned. No new heavy deps; backend tests
> (349) + frontend tests (52) + typecheck stay green every commit.

- [ ] Phase 1: Design tokens & shell polish (fade-in Page wrapper, TopNav active states, focus rings)
- [ ] Phase 2: Mission planner visual overhaul (ScenarioEditor stacked cards, MissionPlannerPage scannable cards)
- [ ] Phase 3: Visibility & metrics cards (VisibilityTimeline, SnapshotPanel chips, MetricsTable color-coded, IntervalBands hatch)
- [ ] Phase 4: Comparison & decision pages (ComparisonPage delta chips, DecisionDashboard pass/warn/fail)
- [ ] Phase 5: Accessibility & motion polish + final typecheck/tests

### Backend (small, tested)

- [x] Add `GET /api/version` (app name, version, API contract, supported window, git SHA).
- [x] CORS `max_age=86400` + `X-Response-Time` middleware.
- [x] ETag/304 for immutable GETs (`/api/config`, `/api/sites`, `/api/craters`, `/api/psrs`, `/api/science/psrs`).
- [x] Extended ETag/304 to `/api/series`, `/api/terrain-horizon`, `/api/phase3`, `/api/phase3/windows`, `/api/feasibility`, `/api/readiness`, `/api/engineering`, `/api/science/site-context`, `/api/science/nearest-psr`.
- [x] `GET /api/ready` (+ top-level `/ready`) readiness probe checking committed data files.

### Frontend (UX)

- [x] Data-saver mode: localStorage preference + auto-detect slow link; 512 px imagery when on.
- [x] TopNav toggle for data-saver mode.
- [x] Shareable scenario links: "Copy scenario link" button + URL-param prefill on load.
- [~] Keyboard accessibility for site markers — superseded: site selection already goes through the keyboard-accessible Landing-site `<select>` in ScenarioEditor; global `:focus-visible` ring is in place. Map markers remain click-to-inspect.
- [x] Methodology page now lists the committed dataset catalogue (availability, records, sources).

### UI overhaul (in progress)

- [x] Phase 0: motion tokens + utility classes (fade-in, slide-up, press, lift, skeleton) in index.css; reduced-motion guard already present.
- [x] Phase 0: Button press feedback; Card interactive lift prop.
- [x] Phase 1/2: skip-to-main link, view-change fade-in, main landmark + tabIndex.
- [x] Phase 1: progressive disclosure (Collapsible) for "What results do not mean".
- [ ] Phase 1: further progressive disclosure for dense panels.
- [x] Phase 2: mobile bottom tab bar.
- [ ] Phase 3: loading skeletons for imagery/PSR.
- [x] Phase 4: 3D terrain enhancement (lighting, scale bar, wireframe toggle).
- [ ] Phase 5: accessibility audit (aria-labels, color-blind safe status) — partial: focus-visible, skip link, semantic landmarks done; status cells already use text words.
- [ ] Phase 6: micro-interactions (count-up, marker pulse, panel collapse).
- [ ] Phase 7: verification + docs.
