# Phase 3 agent coordination (Task 2 ↔ Task 3)

Two agents are implementing Phase 3 in parallel. This file is the contract that
keeps them from overlapping. **Update the status log at the bottom every time you
push, and re-read this file before you start working.** If a rule here conflicts
with what you were about to do, stop and renegotiate here first.

## Division of labour

| Phase 3 task | Owner | Status |
| --- | --- | --- |
| Task 1 — geometric Sun visibility | teammate (already merged, `62a16ce`) | done |
| **Task 2 — geometric Earth visibility** | **agent A (this file's primary editor)** | in progress |
| **Task 3 — terrain horizon obstructions** | **agent B** | not started |
| Tasks 4–11 | unassigned; claimed in the log below, first come first served | — |

## File ownership (hard boundaries)

Agent A (Task 2) owns and edits only:

- `backend/app/services/geometric.py` — **only the Earth parts**. Task 1's Sun
  code in that file is frozen: refactor nothing in the Sun section. Earth code
  goes below the Sun section, clearly delimited by a comment banner.
- `backend/app/api/routes.py` — **only by appending** the `/api/geometric-earth`
  route directly after the existing `/api/geometric-sun` route, and adding its
  import on a separate line. Never reformat or reorder existing lines.
- `backend/tests/test_geometric_earth.py` (new file, fully owned).
- `tasks.md` — **only the Task 2 section** (checkboxes + deliverable paragraph).

Agent B (Task 3) owns and edits only:

- `backend/app/services/terrain` modules and `backend/app/services/phase3.py`
  (terrain-adjusted visibility already lives there) — extend, never rewrite
  Task 1/2 endpoints or shared helpers inside `site_data.py`.
- `backend/tests/test_phase3.py`, `test_wide_terrain.py`, `test_site_terrain.py`
  and any new `test_geometric_terrain*.py`.
- `backend/app/api/routes.py` — only by appending its own route(s) **after**
  Agent A's `/api/geometric-earth` route (or wherever the current file ends the
  Phase 3 block). Never move or edit another route.
- `tasks.md` — only the Task 3 section.

Shared / no-go without explicit agreement in the log:

- `backend/app/services/site_data.py`, `intervals.py`, `horizon.py`,
  `settings.py`, `config/lunanav.config.json` — read freely; changes need a
  log entry stating why, and must not break the other agent's tests.
- `frontend/` — Phase 3 backend tasks stay backend-only for now (Phase 4 wires
  the UI; the wire-up is coordinated in the Phase 4 section below).
- `docs/METHODOLOGY.md` — both agents may add a subsection under the Phase 3
  heading; keep them side by side, do not renumber sections.

## Workflow rules

1. **Branch per task.** `phase3/task2-earth-visibility` (agent A),
   `phase3/task3-terrain-obstructions` (agent B). Branch from current `main`.
2. **Before merging to `main`:** `git fetch && git rebase origin/main`, run the
   full `cd backend && source .venv/bin/activate && python -m pytest -q` and
   `cd frontend && npm run build && npx vitest run`. Merge only when green, and
   merge with a normal merge commit (`--no-ff --no-edit`) so task boundaries stay
   visible.
3. **Push after every work session**, even if the task is not finished, and log
   it here. The other agent re-reads this file at the start of every session.
4. **Never force-push** `main`. Never rewrite the other agent's commits.
5. If both agents must touch the same file in the same region (e.g. both add a
   route): the later rebaser resolves mechanically (keep both, append order =
   task number) and says so in the log.
6. Check off your task's own boxes in `tasks.md` only when the code, tests and
   doc note are actually merged on `main`.

## Definition of done (per task)

- Function(s) implemented per the task's "Calculation" section, exactly.
- Endpoint served and documented in its docstring.
- Own test file with: rule-unit tests (positive/negative/zero), end-to-end test
  against the committed Phase 2 series, API contract test via the `client`
  fixture.
- `tasks.md` deliverable paragraph written like Task 1's (where it lives, what
  it serves, what it deliberately does not do).
- Full suite green (baseline at file creation: 211 backend tests).

## Phase 4 plan (after Phase 3 tasks are done)

tasks.md's Phase 4 asks for the interactive navigator, but most of it already
exists (planner, compare, reschedule, viewer). The real Phase 4 work is wiring
the Phase 3 outputs into the UI and creating the remaining pieces:

1. **agent A:** add a Phase 3 results surface in the frontend — fetch
   `/api/geometric-sun`, `/api/geometric-earth` and `/api/phase3` for the
   selected site/window; show the geometric vs terrain-adjusted distinction
   explicitly (the task list demands the two are never conflated). Claimed.
2. **agent B:** comparison dashboard over the three candidates using
   `/api/phase3` + `/api/geometric-*` (Task 7/8 outputs once implemented), plus
   the delayed-date comparison view (Task 9). Claimed conditionally — both
   claims activate only after Tasks 2/3 are merged.
3. **anyone:** a Phase 4 checklist section in `tasks.md` mirroring the existing
   style, so the new work is trackable.

The task numbering after Task 3 (4–11: sunlight availability, communication
windows, simultaneous visibility, site comparison, requirements, delayed dates,
validation, Phase 4 prep) is claimed in the log below as agents get to them.

---

## Status log (newest entry first)

- **2026-11-14, agent A** — File created. Claimed Task 2
  (`phase3/task2-earth-visibility`). Baseline: `main` at `62a16ce`, 211 backend
  tests green. Plan: mirror Task 1's pattern for Earth
  (`earth_visibility_response` in `geometric.py`, `GET /api/geometric-earth`,
  grazing band = `earth_angular_radius_deg` = 0.95° from the config, same
  `> 0` point-source rule, terrain excluded). Agent B: you are unblocked on
  Task 3 from the current `main`.
