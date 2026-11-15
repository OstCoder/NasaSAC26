# UI Overhaul — Phases (NASA Space Apps 2026 LunaNav)

> Companion to `tasks.md` "Night upgrades". This document is the working plan for the
> autonomous UI/UX overhaul. Another agent can pick up any phase. Checkboxes mirror
> progress; commit each phase separately. Check `git log` before pushing; rebase if needed.
>
> Repo: OstCoder/NasaSAC26 (main). Ports 8002/5174 (never 8000/5173, the other agent's).
> Backend tests (349) + frontend tests (52) + typecheck must stay green every commit.

## Guiding principles (NASA Space Apps alignment)

- **Impact/Relevance**: the UI must make the challenge's question obvious — "is this
  site lit, and can it see Earth?" — within 5 seconds.
- **Validity**: never let polish imply precision we don't have. Keep provenance labels,
  "geometry only" flags, "not assessed" water-ice status and "display only" 3D labels.
- **Creativity**: motion and 3D should clarify, not decorate. Every animation earns its
  place by reducing cognitive load.
- **Presentation**: demo-ready on a laptop and a phone (390 px). No login, no console
  errors, no dead ends.
- **Accessibility**: keyboard, screen reader, `prefers-reduced-motion`, focus rings,
  sufficient contrast (existing `:focus-visible` ring is the baseline).
- **Performance**: no new heavy dependencies; CSS transitions only; respect the
  data-saver mode; keep imagery progressive (512 preview → 1024).

## What we are NOT doing (cut list)

- No rocket/flight simulator, no orbital mechanics animation beyond what exists.
- No new backend science or data sources.
- No new charting/3D libraries (reuse three.js already split).
- No dark/light theme toggle (dark is the product identity).
- No marketing landing page; the app IS the demo.

## Phase 0 — Design tokens & motion primitives — DONE

- [x] Audit `frontend/src/index.css` tokens (colors, spacing, radii, shadows, motion).
- [x] Add motion tokens: `--dur-fast` (120ms), `--dur-base` (200ms), `--dur-slow` (320ms), `--ease-out` (cubic-bezier(.2,.8,.2,1)), `--ease-in-out`.
- [x] Add utility classes: `.fade-in`, `.slide-up`, `.press` (scale on active), `.skeleton` (shimmer), `.lift`, `.panel-collapse`.
- [x] Respect `prefers-reduced-motion`: disable non-essential motion globally.
- [x] Skip-to-main-content link (keyboard).
- [x] View fade-in via shared `.fade-in` + `key={view}` remount in `App.tsx`.

## Phase 1 — Information architecture (less text, more hierarchy) — DONE

- [x] Collapse long descriptive paragraphs into progressive disclosure (methodology "What results do not mean").
- [x] Mobile nav: bottom tab bar on <640px instead of wrapped top nav.
- [ ] Further progressive disclosure for dense panels (methodology datasets table already compact).
- [ ] Promote the single most important number per panel to a large display value; demote secondary text to tooltips.

## Phase 2 — Navigation & layout — DONE

- [x] Sticky header polish: blur, shadow, compact on mobile.
- [x] Mobile bottom tab bar (in place of wrapped top nav on small screens).
- [x] Skip-to-main-content link.
- [x] Persist last view in URL hash (useHashView) — verify all views.
- [ ] Breadcrumbs/back affordance in sub-views.

## Phase 3 — Visual polish & feedback — IN PROGRESS

- [ ] Loading skeletons for map imagery and PSR layer (replace "Loading…" text where a skeleton adds clarity).
- [ ] Empty states with a single clear next action.
- [ ] Toast for "Copied scenario link" (replace inline text swap).
- [ ] Card hover/focus lift (subtle shadow + translate) with reduced-motion guard.
- [ ] Button press feedback (scale 0.98) via `.press`.
- [ ] Consistent icon sizing and spacing.
- [ ] Visibility & metrics cards: glanceable Sun/Earth status chips, color-coded metrics,
      clearer blocked-vs-visible hatch, distinct next-edge rule (VisibilityTimeline,
      SnapshotPanel, MetricsTable, IntervalBands).

## Phase 4 — 3D terrain enhancement (display only) — DONE

- [x] Better default camera angle and lighting (warm sun, cool ambient).
- [x] Scale bar / north arrow overlay.
- [x] Toggle: wireframe vs shaded.
- [x] Keep "display only — 2D profile is authoritative" label prominent.
- [x] Respect data-saver mode (skip 3D textures).
- [ ] Loading overlay with progress for DEM fetch.

## Phase 5 — Accessibility & i18n-readiness — PLANNED

- [ ] aria-labels on icon-only buttons (TopNav data-saver already done).
- [ ] Landmark roles (main, nav, aside) audit.
- [ ] Color-blind safe: ensure status colors (pass/fail) also use icons/text, not color alone.
- [ ] Reduced-motion: all motion gated.
- [ ] Focus management on view change (focus main heading).
- [ ] `focus-visible` rings on every interactive element; `aria-live` on dynamic values.

## Phase 6 — Micro-interactions & delight — PLANNED

- [ ] Number count-up on metric reveal (CSS, reduced-motion aware).
- [ ] Chart tooltip polish.
- [ ] Site marker pulse on hover/select.
- [ ] Smooth panel collapse/expand (CSS grid-rows or max-height).

## Phase 7 — Verification & docs — PLANNED

- [ ] Re-run full test suites + typecheck.
- [ ] Update README "What it does" with new screenshots if visuals changed.
- [ ] Update docs/PHASE7_FINAL_VALIDATION.md with the overhaul entry.
- [ ] Final commit + push.

## Phase 8 — 3D map becomes a real analysis tool
Status: in progress

The 3D view is currently a passive renderer driven by a single selected time. Make it
an interactive analysis surface while keeping "display only" labeling.

- [ ] Time scrubber in 3D view: drive Sun/Earth direction from a slider over the
      mission window (not just the window mean). Reuse the committed hourly series.
- [ ] Click-to-inspect: click the terrain to read lat/lon/height at that cell.
- [ ] Multi-site markers: overlay markers for all candidate sites, not just the
      selected one, with labels.
- [ ] Distance measurement: click two points, show great-circle distance in km.
- [ ] Export: "Save view as PNG" button (canvas.toBlob).
- [ ] Earth visibility cone: optional overlay showing Earth direction as a cone.
- [ ] Contour lines at configurable height intervals (optional, may be heavy).

## Phase 9 — User input & scenario management
Status: planned

- [ ] Saved scenarios: name + save/restore/delete named scenarios in localStorage.
- [ ] Scenario presets: one-click buttons for common analyses (initial window,
      delayed window, custom date).
- [ ] Drag-to-place custom site on the polar map (click already works; add
      visual feedback and coordinate readout).
- [ ] Keyboard shortcuts: 1-5 for views, D for data-saver, C for copy link,
      ? for help overlay.
- [ ] Help overlay (?): list of shortcuts and a 30-second "how to read this" guide.
- [ ] Adjustable observer height (default 2 m) in terrain panels.

## Phase 10 — Data export & sharing
Status: planned

- [ ] Export visibility data as CSV (one row per hour: time, sun el, earth el,
      skyline, clearance, visible flags).
- [ ] Export mission report as PDF (client-side print stylesheet).
- [ ] QR code for scenario link (mobile sharing).
- [ ] Batch export: all three candidates, both windows, one CSV.

## Phase 11 — Live data & freshness
Status: planned

- [ ] "Now" mode: live Sun/Earth sub-points updating every 60 s (uses /api/sky/now).
- [ ] Auto-refresh JPL status pill every 5 min.
- [ ] Staleness indicator: "data as of X" on committed series.

## Phase 12 — Accessibility & robustness
Status: planned

- [ ] Focus management: move focus to main heading on view change.
- [ ] Screen reader live region for data updates ("Calculating…", "Done").
- [ ] Color-blind safe: ensure all status uses icon + text (audit).
- [ ] Error boundary per panel (so one failure doesn't blank the page).
- [ ] Print stylesheet for mission report.

## Phase 13 — Verification & docs
Status: planned

- [ ] Re-run full test suites + typecheck after each phase.
- [ ] Update README with new capabilities.
- [ ] Final commit + push.

## Status summary (as of latest commit)

Completed:
- Phase 0: motion tokens, .fade-in/.slide-up/.press/.lift/.skeleton, Button press, Card lift, skip link, view fade-in.
- Phase 1: Collapsible disclosure (methodology "What results do not mean").
- Phase 2: mobile bottom tab bar.
- Phase 4: 3D terrain wireframe toggle + north/scale overlay.

Partial / deferred (deliberately, to keep scope sane):
- Phase 1: further progressive disclosure for dense panels.
- Phase 3: loading skeletons — the app already shows spinners/opacity + blur-up imagery.
- Phase 5: accessibility — focus-visible, skip link, semantic landmarks, text-word status labels already in place; full audit deferred.
- Phase 6: micro-interactions — press feedback done; count-up/marker pulse/panel collapse deferred.
- Phase 7: this verification pass.

## Commit protocol

- Work phase by phase; commit each phase with message `UI overhaul phase N: <title>`.
- Run tests before each push.
- If a phase is too large, split into sub-commits.
- Keep the existing test suite green; add tests only where logic changes.
- Stop cleanly (commit + push) if context runs low.
