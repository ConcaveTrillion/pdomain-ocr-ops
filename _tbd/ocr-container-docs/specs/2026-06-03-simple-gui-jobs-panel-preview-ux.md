---
title: simple-gui jobs panel + preview UX fixes
date: 2026-06-03
status: shipped
repos: [pdomain-ui, pdomain-ocr-simple-gui]
type: spec
---

# simple-gui jobs panel + preview UX fixes

## Update — 2026-06-04 (as-shipped; supersedes the filter approach)

All six issues shipped, but the **E2E-leak fix (B1) changed materially** from
the original plan. Recording the as-shipped reality here; the B1 section below
is kept for history but its "filter" half is **superseded**.

- **Leak premise was wrong.** The leaked runs were **not** `e2etestjob-*`
  prefixed. They were UUID-named jobs whose display name was `e2e-smoke` (118)
  / `e2e-playwright-test` (34), written into the real projects root by
  `tests/smoke/test_e2e.py`, which booted uvicorn with **no root isolation**
  and ran on every `make ci`. The prefix filter never matched them.
- **Root cause fixed at the producer**, not by filtering: the smoke test now
  passes isolated tmp roots into its subprocess `env=`, and an autouse
  session fixture in `tests/conftest.py` fails closed if any data root
  resolves outside the pytest tmp tree.
- **No UI-side filtering** (per CT). The earlier `e2etestjob-`/source-path
  runtime filter in `list_projects` / `routes/jobs.py` was **removed** — the
  UI must not guess test-ness. Separation is purely by **location**.
- **One-time purge** cleaned the 169 already-leaked dirs (kept 16 real jobs).
  `scripts/purge_test_jobs.py` + `_testjobs.py` remain a standalone
  maintenance tool, no longer imported by the runtime listing path.
- **New: user-facing "jobs location" setting.** A "Jobs" settings panel
  (injected via AppShell's `settingsPanels` slot — no pdomain-ui change) lets
  the user choose the projects root. Precedence is **env > pref > default**
  (env still wins, so tests/CI stay isolated); switch-not-migrate; invalid
  paths rejected with 400. Persisted in `AppPrefs.jobs_location`.
- **Bonus fix:** `PUT /api/prefs` was clobbering all app prefs with defaults
  on every save (wrapped-body + whole-record overwrite). Now a read-modify-
  **merge**; the frontend sends the correct flat shape.

See `docs/decisions/2026-06-04-jobs-location-setting.md` (in the simple-gui
repo) for the setting's design record.

## Problem

While using `pdomain-ocr-simple-gui`, CT observed several issues in the jobs
panel and the image/text preview:

1. **E2E test runs leak into the real jobs view.** `e2etestjob-*` runs appear
   in the live app's jobs panel. They should be isolated and never visible in
   normal use.
2. **No way to remove a run.** The jobs panel has no trash/delete affordance.
3. **Finished runs keep animating.** "Green" (succeeded) runs show a moving
   gradient even though they are done — confusing.
4. **Download checkboxes are bad UX.** Per-format "Include in download"
   checkboxes (Text/JSON) require pre-selection before downloading.
5. **Text box does not auto-expand.** The OCR text box in the image/text
   preview is a fixed-height area, unlike the image which fills the page
   height. It should fill the panel and scroll only when necessary.
6. **Toolbar does not reflow on pin.** Pinning the jobs panel does not cause
   the toolbar above the text box to reflow into the narrower content area.

## Ownership map

Several behaviors live in **pdomain-ui** (the shared frontend library), not in
simple-gui. The work lands upstream first, then simple-gui consumes a new
pdomain-ui release.

| Concern | Owner |
|---------|-------|
| Done-job shimmer animation (`JobRow`) | pdomain-ui |
| Trash affordance + `onJobDelete` callback | pdomain-ui (UI) + simple-gui (wiring) |
| Text box fill in `PageSplitView` editor panel | pdomain-ui |
| Pin reflow (AppShell grid / `min-width:0`) | pdomain-ui and/or simple-gui (diagnose) |
| E2E job leak (filter / purge / harden) | simple-gui |
| Download UX | simple-gui |

## Decisions (confirmed with CT)

- **Trash = permanent delete.** The trash icon calls the existing
  `DELETE /api/jobs/{id}`, removing the run and its output files from disk.
- **E2E leak = purge + filter + harden.** ⚠️ **Superseded** (see the
  2026-06-04 update above): shipped as purge + harden + **no runtime filter**.
  The backend filter was removed; isolation is by location, and a user-facing
  jobs-location setting was added.
- **Download = two explicit buttons**, no checkboxes (images always included
  server-side; most users will not want JSON):
  - `Download (images + text)` — primary
  - `Download (images + text + JSON)` — secondary
- **Done jobs are fully static** — no shimmer, no pulse.
- **Text-box fill is the default** in the `PageSplitView` editor panel (not an
  opt-in flag).

## Part A — pdomain-ui (ships first → minor version bump)

### A1. Stop the done-job shimmer

`JobRow.tsx` renders an infinite `pgd-shimmer` linear-gradient overlay on done
jobs. Remove the shimmer (and the dot pulse) for done/failed/cancelled rows so
finished runs are visually static — solid status color only. Running and queued
rows keep their progress bar and dot pulse.

### A2. Trash affordance + `onJobDelete`

- Add an optional `onJobDelete?: (id: string) => void` to `AppShellJobsProps`
  and thread it through `JobsPanelBody` → `JobRow`.
- Render a trash button on each `JobRow`, shown for done/failed/cancelled runs
  (on hover, consistent with the existing row-action buttons). When the run is
  still running/queued, the existing Discard/cancel path remains.
- The callback is optional and additive; existing consumers are unaffected.

### A3. Text box fill mode (default)

Make the `PageSplitView` editor-panel text area fill the panel height by
default (`flex: 1; min-height: 0; overflow: auto`) instead of a fixed
`rows={40}`. It then matches the image side and scrolls only when the text
overflows. No opt-in flag — this is the default behavior.

### A4. Pin-reflow root cause

AppShell already reflows `main` via the `--shell-right-w` grid column when the
dock is pinned, so the toolbar-not-reflowing symptom is almost certainly a
missing `min-width: 0` on a flex/grid child in the content path — a grid `1fr`
or flex item will not shrink below its content's intrinsic width without it.
Reproduce, identify whether the fix belongs in the pdomain-ui content wrapper
(`PageSplitView` / AppShell main) or in simple-gui's page, and fix the root
cause so the toolbar reflows when the panel is pinned.

→ pdomain-ui takes a minor bump (0.5.x → 0.6.0). simple-gui consumes it.

## Part B — simple-gui (consumes new pdomain-ui)

### B1. Kill the e2e leak (purge + filter + harden) — ⚠️ filter half SUPERSEDED

> **As-shipped (2026-06-04):** the **filter** below was removed — no UI-side
> filtering. The leak was fixed at the producer (smoke-test root isolation +
> autouse fail-closed guard), the 169 leaked dirs were purged, and a
> user-facing jobs-location setting (env > pref > default) replaced the idea of
> hiding test ids. The original text is retained for history.

- **Filter:** `/api/jobs`, the recent-projects list, and storage
  `list_projects()` exclude any id with the `e2etestjob-` prefix, so test runs
  can never surface in the real UI.
- **Purge:** a one-time cleanup removing already-leaked `e2etestjob-*` runs from
  the real projects root and from prefs `recent_projects`.
- **Harden:** a guard in the e2e fixtures asserting that the projects/output/
  meta roots resolve inside the session tmpdir; the fixture aborts rather than
  ever writing to the real root.

### B2. Wire trash → delete

Pass `onJobDelete` from simple-gui's `App.tsx` into AppShell. It calls
`DELETE /api/jobs/{id}` (permanent delete) and then refetches `/api/jobs`. Stop
hardcoding dock rows as non-actionable so the trash button renders.

### B3. Replace download checkboxes with two buttons

Remove the per-format "Include in download" checkboxes. Render two buttons that
hit `…/download?include=…` directly:

- `Download (images + text)` → `include=text`
- `Download (images + text + JSON)` → `include=text,json`

Apply to both `ResultsPage` and the `PageViewPage` download shortcuts. (Images
are always included server-side regardless of the `include` tokens.)

### B4. Text box auto-expand

Switch `PageViewPage`'s text area to the pdomain-ui fill default (drop
`rows={40}`) so it grows to page height and scrolls only when needed.

### B5. Toolbar reflow

Apply the A4 fix on simple-gui's side if the root cause is in its page wrapper.

## Testing

- **Backend:** test that the `e2etestjob-` filter excludes test ids from
  `/api/jobs`, recent projects, and `list_projects()`; test that delete +
  refetch removes a run.
- **Frontend:** test the two download buttons build the correct `include=`
  URLs; test trash → `DELETE /api/jobs/{id}` wiring; test done rows render
  static (no shimmer).
- **E2E:** assert a seeded `e2etestjob-*` id never appears in a fresh,
  non-test `/api/jobs`; assert the fixture guard aborts on a non-tmp root.
- **Layout:** repro + regression for pin-reflow (toolbar shrinks with the
  pinned dock).

## Out of scope

- No changes to job execution / OCR pipeline.
- No new job-history page; the trash operates on the existing panel + recent
  list.
- No Postgres / persistence-model changes (per the standing deferral).
