# Handoff — pdomain-ocr-simple-gui reconciliation (2026-05-26)

Resume point for the multi-milestone reconciliation work that started
this session with `/superpowers:brainstorming` → spec → plan → autonomous
implementation loop.

## TL;DR

- **Spec:** `docs/specs/2026-05-26-pdomain-ocr-simple-gui-reconciliation-design.md`
- **Plan:** `docs/plans/2026-05-26-pdomain-ocr-simple-gui-reconciliation.md`
- **Shipped through main HEAD `91b021c` (pdomain-ocr-simple-gui):** A0–A9 + B1.
- **Stopped before:** B2 (auth & access). Dispatch text for B2 is staged
  in this doc — paste and dispatch when resuming.
- **CI disabled** on `pdomain/pdomain-ocr-simple-gui` (workflow
  `ci.yml` `disabled_manually`). `make ci AI=1` in worktrees was the
  real gate during the loop.

## What's shipped (all on `main`, pushed to origin)

| Milestone | Merge SHA | What |
|---|---|---|
| A0 | `1f2ade0` | container detect + `Mode` enum + `GET /api/config` |
| A1 | `8cdf804` | `Source` Protocol + `LocalPathSource` (folder/image/zip + bomb/traversal guards) |
| A2 | `63428cf` | `UploadedFilesSource` + `POST /api/uploads` multipart streaming |
| A3 | `78401fb` | `OutputConfig` resolver + jobs route accepts `upload_id`/`output` |
| A4 | `abfb04b` | `GET /api/jobs/{id}/download` (zip stream) |
| A5 | `ab87f83` | `GET /api/pages/{id}/{idx}/words` (sources DocTR sidecar) |
| A6 | `21c10ae` (3 commits direct to main) | frontend `ConfigContext` + `SourcePicker` + `HomePage` matrix; legacy `DropZone` deleted |
| A7 | `472484d` | `OutputConfigPanel` in `JobConfigDialog` + download button on `ResultsPage` |
| A8 | `4faa600` | word overlays on `PageImageCanvas` (pixel-coord conversion + wrapper-div testid) + `output_mode` round-trip via jobs-meta sidecar |
| A9 | `607f95f` | testids consumed; prefs `persistApp` wired to `PUT /api/prefs`; **A9.2 Worklist + A9.3 PageWorkbench deferred** with TODOs |
| B1 | `91b021c` | 13 swallowed-exception sites → `logger.exception(...)` with structured context |

## Deferred / TODO inside the codebase

These were flagged by subagents during the run; preserved as TODOs in
source rather than forced into bad fits.

1. **A9.2 — pdomain-ui Worklist swap.** Skipped because pdomain-ui's
   `@concavetrillion/pdomain-ui/worklist` exports OCR-domain-specific
   widgets (`WordList`, `LineList`, `PageList`) keyed to OCR data
   shapes, not a generic tabular Worklist. `RecentProject` and
   `PageRow` shapes don't fit. TODOs in
   `frontend/src/components/RecentProjectsList.tsx` and
   `frontend/src/pages/ResultsPage.tsx`. Either a generic Worklist
   lands in pdomain-ui later, or we leave the hand-rolled tables.

2. **A9.3 — pdomain-ui PageWorkbench swap.** Skipped because pdomain-ui's
   `stages/PageWorkbench` is a collection of annotation sub-components
   (`ArtifactViewer`, `PWHeader`, `OcrTextPanel`, `WordBboxOverlay`,
   `LabelerCanvas`, …), not a single `<PageWorkbench>` layout wrapper.
   `PageViewPage` already uses pdomain-ui's `PageSplitView` +
   `PageImageCanvas` from A6–A8. TODO in `PageViewPage.tsx`.

3. **A9.4 — pdomain-ui polling hook (`useLongJob`) swap.** Wired
   `persistApp → PUT /api/prefs` (prefs side) but deferred the polling
   side. Backend returns full `JobStatus` (`pages`, `page_count`,
   `output_dir`, statuses `queued|running|succeeded|failed|cancelled`)
   while pdomain-ui `useLongJob` expects `{status, progress, events}` with
   `idle|pending|running|done|error|cancelled`. Clean swap needs an
   SSE/WebSocket adapter on the backend or a shape adapter. TODO in
   `App.tsx`.

4. **A3 — Legacy `source_path` path in jobs route.** A3 preserved the
   pre-A6 request shape so existing tests would keep passing. The new
   shape (`upload_id` | `source_path` + `output: OutputConfig`) is the
   real path; the legacy branch is dead code once the frontend always
   sends `output` (which is now the case after A7). Worth a cleanup
   pass alongside B2.

## Open GH issues (status snapshot)

Closed by B1: **#29, #30, #31, #32, #33, #34** (logging hygiene).

Still open — to be addressed in remaining Phase B milestones:

- **#17, #18, #19, #23** — auth & access (B2).
- **#24, #25, #26** — frontend hardening (B3). #25 may already be
  shipped; verify on resume.
- **#20, #21, #22, #27, #28** — supply chain (B4).

## Operational gotchas the subagents flagged

These are now relevant for any future agent dispatched against this
repo:

1. **`Edit` tool resolves to the main checkout, not the worktree.**
   Several subagent dispatches had to copy edited files from the main
   repo checkout into their assigned worktree before committing.
   Workaround: after each `Edit` in a worktree dispatch, verify
   `git -C <worktree> status` shows the change; if not, copy explicitly.
   This was logged inside agent memory.

2. **Some agents committed directly to `main` in the harness worktree.**
   A6 ended up with three commits straight to main because the harness
   gave the agent a worktree sharing main rather than a fresh branch.
   Future dispatches should explicitly instruct the agent to create
   and use a `feat/<slug>` branch.

3. **DocTR word bboxes are normalized 0–1 page-relative.** The
   `/api/pages/{id}/{idx}/words` route returns them that way. The
   frontend `PageViewPage` converts to pixel coords using
   `apiWordToCanvasWord` before passing to `PageImageCanvas` (which
   wants pixel `{top_left, bottom_right}`).

4. **`PageImageCanvas` does NOT forward arbitrary `data-*` props.**
   `PageViewPage` uses a wrapper `<div data-testid="page-image-canvas"
   data-word-count="N">` so tests can assert overlay count.

5. **gitlint requires non-empty commit bodies.** Plan's one-line
   commit subjects all needed a body to pass. Standard pattern this
   session was a 1–3 line body explaining the change.

## CI state

- `pdomain/pdomain-ocr-simple-gui` `ci.yml` is `disabled_manually`.
  Re-enable and trigger when ready:
  ```sh
  gh workflow enable ci.yml --repo pdomain/pdomain-ocr-simple-gui
  gh workflow run ci.yml --repo pdomain/pdomain-ocr-simple-gui --ref main
  ```

## What's next, in order

1. **B2 — Auth & access** (#17, #18, #19, #23). Dispatch text below.
2. **B3 — Frontend hardening** (#24, #25, #26).
3. **B4 — Supply chain** (#20, #21, #22, #27, #28).
4. **B5 — Playwright browser verification.** Mandatory final
   milestone per the FastAPI+SPA workspace rule. Tooling +
   app-loads + upload-single-image + existing-folder + word-overlays
   + download-managed + deep-link tests. Wire into `make ci`.
5. **Bonus — exhaustive Playwright path coverage** (CT-added scope).
   After B5 baseline, write a coverage plan enumerating every user
   path in the app, then add Playwright tests for each.
6. **Verify #25 (Copy path)** — may already be shipped; close with
   verification comment.
7. **Re-enable CI** on pdomain-ocr-simple-gui and trigger a fresh main
   build.
8. **Clean up A3 legacy `source_path` branch** in `routes/jobs.py`
   (no longer reachable from the current frontend).

## Ready-to-go dispatch for B2 (paste verbatim)

```
Repo: /workspaces/ocr-container/pdomain-ocr-simple-gui

Phase A + B1 shipped on main. You are implementing **Milestone B2 —
Auth & access**. Closes #17 (caller-controlled source_path / path
traversal), #18 (unauth resource exhaustion), #19 (unauth suite-launch
process spawn), #23 (unauth endpoints).

Spec: docs/specs/2026-05-26-pdomain-ocr-simple-gui-reconciliation-design.md
Plan: docs/plans/2026-05-26-pdomain-ocr-simple-gui-reconciliation.md

Hard rules:
- NEVER `gh pr create`.
- Do NOT merge to main. Use branch `feat/reconciliation-b2` inside a
  worktree under `.claude/worktrees/<slug>`.
- TDD per task. 5 commits (one per sub-task).
- `make ci AI=1` must pass.
- Watch for the `Edit`-tool-resolves-to-main gotcha; verify each edit
  landed in the worktree.

Sub-tasks in order:

B2.1 — Auth mechanism decision + ADR
  Inspect /workspaces/ocr-container/pdomain-prep-for-pgdp and
  /workspaces/ocr-container/pdomain-ocr-labeler-spa for an existing auth
  convention (grep for `auth`, `token`, `Bearer`, `Depends`).
  If a convention exists, adopt it verbatim. Else default to:
  shared-secret token from PD_OCR_SIMPLE_GUI_API_TOKEN env (or
  ~/.local/share/pdomain-ocr-simple-gui/api_token file, auto-generated
  with mode 0600 on first boot). `/api/config` exposes the token in
  LOCAL mode only.
  Write ADR: docs/decisions/2026-05-26-api-auth-mechanism.md.
  Commit: docs(adr): choose API auth mechanism.

B2.2 — Auth middleware + apply to all routes (closes #23)
  src/pd_ocr_simple_gui/runtime/auth.py FastAPI Depends-based token
  check. Apply to /api/jobs/*, /api/uploads, /api/pages/*, /api/prefs,
  /api/projects/*, suite-launch, downloads. Public: /api/config,
  /health (if present).
  Tests: tests/test_auth_middleware.py covers 401-missing, 401-wrong,
  200-correct, public-without-token.
  Frontend: add apiFetch wrapper in lib/api.ts; ConfigContext
  exposes the token; update fetch sites + their tests.
  Commit: feat(auth): protect API routes with token middleware (#23).

B2.3 — Path-traversal audit (closes #17)
  Confirm LocalPathSource rejects symlink-escape + absolute paths
  outside an allowed root. Audit routes/jobs.py, uploads.py,
  downloads.py, words.py, pages.py for other caller-controlled
  filesystem strings.
  New env PD_OCR_SIMPLE_GUI_ALLOWED_PATH_ROOTS (colon-separated)
  for production deployments; default unset = no restriction.
  Add ALLOWED_PATH_ROOTS enforcement test.
  Commit: fix(security): finalize path-traversal protection (#17).

B2.4 — Rate limit + max-pages cap (closes #18)
  In-memory per-IP per-route rate limiter (middleware, dict +
  time.monotonic). Configurable via PD_OCR_SIMPLE_GUI_RATE_LIMIT_PER_MIN
  (default 60).
  PD_OCR_SIMPLE_GUI_MAX_PAGES_PER_JOB default 5000; reject 413.
  Tests cover burst + cap.
  Commit: feat(security): rate limit + max pages per job (#18).

B2.5 — Gate suite-launch (closes #19)
  Confirm suite-launch routes behind B2.2 middleware. Add explicit
  401-without-auth test.
  Commit: fix(security): require auth for suite launch (#19).

After all: make ci AI=1.

Return value:
- Worktree path + branch
- 5 commit SHAs
- make ci AI=1 status
- ADR path
- Whether sibling repos had an existing auth convention (and the
  file:line you found it)
- List of frontend test files updated to send the token
```

## Tool / agent reminders for the next session

- Per workspace `CLAUDE.md`: subagents must NOT open PRs. Local
  merge → push pattern only.
- Use `isolation: "worktree"` on every full-power agent dispatch
  (i.e. not `-docs`, not `driver`).
- Use `model: "sonnet"` on implementers + reviewers.
- For Playwright work (B5 + bonus), the
  `pd-ocr-labeler-driver` agent should NOT be used here — it's the
  Playwright operator that drives a running labeler UI, not a
  scaffolder for e2e tests on this app.

## Open question for CT before resuming

For B2, default to **shared-secret token** if no sibling convention
exists? Or do you want session cookies / something else? The dispatch
above assumes shared-secret token.
