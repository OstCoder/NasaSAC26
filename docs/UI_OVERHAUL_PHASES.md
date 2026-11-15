# UI Overhaul — Phases (NASA Space Apps 2026 LunaNav)

> Companion to `tasks.md` "Night upgrades". This document is the working plan for the
> autonomous UI/UX overhaul. Another agent can pick up any phase. Checkboxes mirror
> progress; commit each phase separately.

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

## Phase 0 — Design tokens & motion primitives
Status: in progress

- [ ] Audit `frontend/src/index.css` tokens (colors, spacing, radii, shadows, motion).
- [ ] Add motion tokens: `--dur-fast` (120ms), `--dur-base` (200ms), `--dur-slow` (320ms), `--ease-out` (cubic-bezier(.2,.8,.2,1)), `--ease-in-out`.
- [ ] Add utility classes: `.fade-in`, `.slide-up`, `.press` (scale on active), `.skeleton` (shimmer).
- [ ] Respect `prefers-reduced-motion`: disable non-essential motion globally.
- [ ] Add a single `motion-safe:` discipline: every animation gated by `prefers-reduced-motion: no-preference`.

Deliverable: a small, documented token set; no visual change yet beyond smoother focus.

## Phase 1 — Information architecture (less text, more hierarchy)
Status: planned

- [ ] Collapse long descriptive paragraphs into progressive disclosure (details/summary or "Show more").
- [ ] Promote the single most important number per panel to a large display value; demote secondary text to tooltips.
- [ ] Replace dense tables with compact cards on mobile (already partially done in CandidateComparison).
- [ ] Add a "What am I looking at?" one-line subtitle under each view title (already present in some).
- [ ] Trim the README-style prose inside the app (Methodology page is the place for depth).

## Phase 2 — Navigation & layout
Status: planned

- [ ] Sticky header polish: blur, shadow on scroll, compact on mobile.
- [ ] Mobile nav: bottom tab bar on <640px instead of wrapped top nav.
- [ ] Skip-to-main-content link (keyboard).
- [ ] Breadcrumbs/back affordance in sub-views.
- [ ] Persist last view in URL hash (already does via useHashView) — verify all views.

## Phase 3 — Visual polish & feedback
Status: planned

- [ ] Card hover/focus lift (subtle shadow + translate) with reduced-motion guard.
- [ ] Button press feedback (scale 0.98).
- [ ] Loading skeletons for map imagery and PSR layer (replace "Loading…" text).
- [ ] Empty states with a single clear next action.
- [ ] Toast for "Copied scenario link" (replace inline text swap).
- [ ] Consistent icon sizing and spacing.

## Phase 4 — 3D terrain enhancement (display only)
Status: planned

- [ ] Better default camera angle and lighting (warm sun, cool ambient).
- [ ] Scale bar / north arrow overlay.
- [ ] Toggle: wireframe vs shaded.
- [ ] Loading overlay with progress for DEM fetch.
- [ ] Keep "display only — 2D profile is authoritative" label prominent.
- [ ] Respect data-saver mode (skip 3D textures).

## Phase 5 — Accessibility & i18n-readiness
Status: planned

- [ ] aria-labels on icon-only buttons (TopNav data-saver already done).
- [ ] Landmark roles (main, nav, aside) audit.
- [ ] Color-blind safe: ensure status colors (pass/fail) also use icons/text, not color alone.
- [ ] Reduced-motion: all motion gated.
- [ ] Focus management on view change (focus main heading).

## Phase 6 — Micro-interactions & delight
Status: planned

- [ ] Number count-up on metric reveal (CSS, reduced-motion aware).
- [ ] Chart tooltip polish.
- [ ] Site marker pulse on hover/select.
- [ ] Smooth panel collapse/expand (CSS grid-rows or max-height).

## Phase 7 — Verification & docs
Status: planned

- [ ] Re-run full test suites + typecheck.
- [ ] Update README "What it does" with new screenshots if visuals changed.
- [ ] Update docs/PHASE7_FINAL_VALIDATION.md with the overhaul entry.
- [ ] Final commit + push.

## Status summary (as of latest commit)

Completed:
- Phase 0: motion tokens, .fade-in/.slide-up/.press/.lift/.skeleton, Button press, Card lift, skip link, view fade-in.
- Phase 1: Collapsible disclosure (methodology "What results do not mean").
- Phase 2: mobile bottom tab bar.
- Phase 4: 3D terrain wireframe toggle + north/scale overlay.

Partial / deferred (deliberately, to keep scope sane):
- Phase 1: further progressive disclosure for dense panels (methodology datasets table is already compact).
- Phase 3: loading skeletons — the app already shows spinners/opacity + blur-up imagery; skeletons remain a polish item.
- Phase 5: accessibility — focus-visible, skip link, semantic landmarks, text-word status labels already in place; full audit deferred.
- Phase 6: micro-interactions — press feedback done; count-up/marker pulse/panel collapse deferred.
- Phase 7: this verification pass.
- Work phase by phase; commit each phase with message `UI overhaul phase N: <title>`.
- Run tests before each push.
- If a phase is too large, split into sub-commits.
- Keep the existing test suite green; add tests only where logic changes.
- Stop cleanly (commit + push) if context runs low.
