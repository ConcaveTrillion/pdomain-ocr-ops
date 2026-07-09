# Behavior-Driven E2E — Gotchas & Lessons

> **Living doc.** Cross-cutting findings collected while standing up the
> behavior-E2E methodology (`behavior-e2e-capture.md`). Captured continuously
> (each per-unit subagent appends a "Gotchas encountered" list to its report);
> consolidated here once, cleanly, at the end of each pilot. Methodology-
> general lessons live here; repo-specific quirks live in that repo's agent
> memory. First pilot: `pdomain-ocr-simple-gui` (Web/GUI).

## Coverage gate

- **The ID scanner self-poisons from its own test fixtures.** A `scan_cited`
  that `rglob`s all of `tests/` picks up the example IDs inside the coverage
  script's *own* unit-test string fixtures (e.g. `Covers: B-HOME-001` in a
  `tmp_path` fixture), producing phantom "unlinked citations" that fail the
  gate. Fix: skip the scanner's own test file by name (mirroring how the
  declared-scan skips `coverage.md`/`README.md`).
- **Strip template worked-examples on scaffold.** Copied behavior-spec
  templates carry HTML-comment worked examples like `### B-PAGEVIEW-012`
  (tagged `Regression: yes`). The `^### B-…` heading regex matches them even
  inside `<!-- -->` comments → phantom regression records that fail the gate.
  Delete the worked-examples block when scaffolding each unit doc.
- **The ID regex must match the IDs you actually write — a too-narrow one
  drops citations silently, not loudly.** The scanner's `ID_RE` matched only
  single-token IDs (`[BF]-[A-Z0-9]+-\d+`), so a multi-segment flow ID like
  `F-UPLOAD-OCR-DOWNLOAD-01` (used verbatim in a Tier-B `Covers:` line and in
  the plan's own examples) matched *nothing*. It wasn't flagged as unlinked —
  unlinked means "cited but not declared", and an unmatched string is never
  even seen as a citation. The gate stayed green for the wrong reason (zero
  `F-*` declared, zero `F-*` cited). Decide the ID grammar up front and unit-
  test the regex against a real multi-segment ID; if you allow descriptive
  flow IDs, widen both `ID_RE` and the heading regex to
  `[BF]-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d+` (still matches single-segment records).

## Two-tier execution (real-dependency Tier B)

- **Tier B is not `uv run`-safe in local-dev mode.** When the real dependency
  is an *editable local sibling* (registry lags an unreleased commit), a plain
  `uv run` auto-syncs the venv mid-recipe and reverts the editable sibling back
  to the registry pin — reintroducing the very error Tier B exists to catch.
  Run Tier B with `UV_NO_SYNC=1` until the sibling is released and the pin
  bumped. (Pilot instance: `pdomain-book-tools` `det_bs`/`reco_bs`, issue #226.)
- **Tier B needs a deterministic known-good fixture, not a brittle string
  match.** Generate a clean high-contrast text image (committed generator +
  PNG + `.gt.txt`); assert tolerant word-overlap (≥60%), never exact text.

## Running verification in a local-dev worktree

When the registry siblings lag local sources, the pilot runs in local-dev mode
— and the stock `make` verification targets don't run verbatim:

- **`make e2e-fast` / `make ci` depend on the registry `frontend-build`,** which
  fails while the registry frontend lib is broken. In a local-dev worktree,
  build with `make local-frontend-build` first, then run the e2e pytest portion
  directly (`uv run --group e2e pytest tests/e2e/ -m "(slow or e2e) and not
  real_ocr"`). M8's CI wiring must account for this until the registry lib ships.
- **Every `uv run` auto-syncs and reverts the editable sibling to the registry
  pin.** This is *harmless* for Tier A / unit tests / the coverage gate (they
  use the fake dispatcher and never call the real dependency), but it silently
  un-does local-dev mode for the next Tier-B run. Prefix with `UV_NO_SYNC=1` to
  keep the env stable; it's *required* for `make e2e-real-ocr`. Re-running
  `make local-setup-py` restores the editable sibling afterward.
- **Symptom when the env has silently drifted: Tier-B hangs the full
  `wait_for_function` timeout (e.g. 180s) and "fails."** If a prior `uv run`
  reverted the editable sibling to the registry pin, every real job fails at
  the predictor call, the job never reaches `done`, and the Playwright wait
  times out — looking like a test bug but it's dep drift. Fix: `make
  local-setup-py`, then run the Tier-B pytest target directly with
  `UV_NO_SYNC=1` (the `frontend-build` prereq is already satisfied locally).

## Test isolation under xdist (flaky-suite trap)

- **`-n auto` isolates *workers*, not *tests within a worker*.** Each xdist
  worker gets its own session-scoped live-server subprocess + data root — but
  every test assigned to that worker shares them. So any test that mutates
  **persisted shared state** (the prefs file, the recent-projects list) pollutes
  the next test in that worker. Symptom: the full-dir suite fails ~1 test per
  run and the *failing test moves between runs* (e.g. `prefs_persist_across_reload`
  expecting `tesseract` but seeing `doctr`; `recent_project_row_navigates` not
  finding a row) while each file passes in isolation. This is a real harness
  defect, not noise — a flaky gate is a worthless gate.
- **Fix (two layers, both needed):** (1) Redirect the persisted store to a
  per-worker temp path — `tmp_path_factory` gives each xdist worker its own
  basetemp, so pointing the store's data-dir env var at `e2e_data_root/...` in
  the server-boot env isolates *across* workers. (2) Add a **function-scoped
  autouse** fixture that resets the store to defaults before each test (e.g.
  `httpx.put(f"{url}/api/prefs", json={})`) to kill *within-worker*
  test-order pollution. Layer 1 alone is insufficient — tests sharing a worker
  still pollute each other in order. Running serially is NOT a fix (it just
  hides it and is far slower); `-n auto` stays required and is the standard.
- **The leaked store may not be one you redirected.** The conftest can
  redirect every *app-specific* root (projects/output/jobs/upload) yet still
  miss a *suite-level* singleton the app writes through a shared library. If a
  prefs/registry helper falls back to a platformdirs user-home path when its
  env var is unset, every worker shares the real on-disk file. Grep the prefs/
  suite library for the data-dir env var it honors and set it in the boot env.

## Worktrees + venv (uv repos)

- **Worktrees get a stray project-local `.venv`.** `uv run` creates a per-dir
  `.venv`, so the repo's `make local-*` targets (which manage the *canonical*
  venv via the git common dir) edit a different environment than the worktree's
  `make test`/`make e2e-*` actually use. Symlink the worktree `.venv` to the
  canonical one so local-dev editables and the test runner agree.

## Web/GUI profile selectors

- **Not every `data-testid` is DOM-addressable.** Some component libraries drop
  unknown `data-*` props (e.g. Radix `Switch` for the normalization toggles).
  The testid can exist in the constants file yet never reach the DOM — tests
  must select via `get_by_label(...)` / role instead. Confirm each selector is
  actually present in a rendered page, not just declared.
- **Local-dev `pnpm link` state must never be committed.** `frontend/
  pnpm-workspace.yaml` + `pnpm-lock.yaml` get rewritten with a `link:` overlay
  while local-linking a sibling; cleanup is `git checkout -- <those files>`.
- **Drive transient/loading states deterministically with `page.route(...)`.**
  To exercise a transient-error→recover or a held-"running" poll without racing
  the real pipeline, intercept the status endpoint and `route.fulfill(...)` a
  503 then a 200 (and `page.unroute()` to release). Far more reliable than
  timing the fake dispatcher.
- **A toast container is in the DOM even with zero toasts.** Sonner renders its
  `<ol data-sonner-toaster>` unconditionally; only individual `<li
  data-sonner-toast>` elements appear per toast. Wait for/assert the `-toast`
  child, never the `-toaster` wrapper, or every "did a toast appear?" check
  passes vacuously.
- **The interview surfaces missing UI, not just buggy behavior.** A behavior can
  be fully wired in the backend (prefs persist + apply-on-load) yet have NO
  user-facing control because a refactor dropped the affordance (here: a custom
  header slot bypassed the shared shell's built-in settings gear). Capturing the
  behavior forces you to find the trigger — and discover it doesn't exist.
  Treat "no trigger renders" as a finding for the maintainer (fix-now vs
  file-and-defer), not a reason to silently downgrade the test to API-only.
- **A non-2xx-throwing fetch hook collapses every backend status into one
  client error state.** When a polling hook throws on any non-ok response,
  distinct per-code UX (a 404 "Job not found" vs a retryable 5xx) is impossible
  — and a terminal *job* state (`failed`) can map to the same enum as a *fetch*
  failure, so the loaded failed-job UI gets shadowed by the fetch-error block.
  Fix the fetch layer to pass the status code through (re-throw only on the
  terminal codes) and guard renders on both the status enum AND `data===null`.

## Backend / side-effect assertions

- **Verify real on-disk artifact names against the storage code — don't
  assume.** The plan's assumed page-sidecar name (`page_0000.json`) was wrong;
  the real name is derived from the source image filename
  (`pages/<image-name>.json`, e.g. `scan.png.json`). A behavior record's
  backend assertion is only as good as the filename it inspects.

## Process

- **The interview surfaces real bugs, not just behavior.** Capturing intended
  behavior repeatedly exposed live bugs (silent prefs-default no-op, infinite
  "Loading…" on a failed config fetch, orphaned upload staging on clear). Treat
  these as first-class output: tag `Regression: yes`, and (per maintainer call)
  fix-now-with-a-green-test or file-and-defer — a regression-tagged record
  needs a green covering test or the gate stays red.

## TUI profile gotchas (se-llm-skills pilot)

### G-TUI-1: Coverage scanner regex requires strict pure-digit suffix

- **What.** ID regex is `[BF]-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d+`. Suffix
  MUST be pure digits (`-001`, `-01`). Do not add `-REG` or any
  alphabetic suffix to a record ID. A `-REG` suffix fails to match and
  is silently dropped by the scanner.
- **Bites.** Authors familiar with methodologies that use `-REG`
  suffixes write `B-ITEM-001-REG`. The scanner ignores the ID without
  warning.
- **Fix.** Use `**Regression:** yes — <what failed>` in the body.
  Keep the pure-digit suffix on the ID.

### G-TUI-2: F-UNIT-NNN placeholders show as INFO orphans

- **What.** Per-unit specs sometimes declare flow IDs in a `## Flows`
  section. The scanner detects these as declared but uncited → INFO
  orphans in gate output. Gate passes (INFO only) but output is noisy.
- **Bites.** The home agent declared 10 F-HOME-NNN IDs in
  `view-home.md` before `flows.md` existed. Post-M3 scanner showed 11
  INFO orphans.
- **Fix.** Audit per-unit `## Flows` sections. Demote single-screen
  sub-sequences (no cross-unit transition) by clearing the ID. Move real
  cross-unit flows to `flows.md` with full schema + Tier A+B marker.
  Once flows have test citations, orphan warnings disappear.

### G-TUI-3: mise trust required in fresh worktrees

- **What.** `mise.toml` in the repo root is not auto-trusted in a fresh
  worktree. Any `make` target that calls `mise exec` (trivy, gitleaks,
  zizmor, actionlint) fails with `mise ERROR Config files in .../mise.toml are not trusted.`
- **Bites.** Every new worktree. `make ci` fails at `security-scan` or
  `workflow-lint` until mise is trusted.
- **Fix.** `mise trust` in the worktree root before first `make ci`.
  One-time step per worktree.

### G-TUI-4: Strikethrough-rendered keys not matchable as exact "(X)"

- **What.** Disabled keybar actions render with terminal strikethrough
  (`\x1b[9m`). The pyte emulator stores combining strikethrough chars,
  so a literal `"(C)"` is NOT in `pty.screen_text()` for a disabled C
  key. `wait_for("(C)")` times out.
- **Bites.** Tier B PTY tests that wait for a disabled key to confirm
  keybar rendered.
- **Fix.** Wait for a marker always visible (e.g. `(N)` when tree
  clean, or `se-llm ·` in header). For disabled-key assertions, use the
  text of an enabled peer key as wait condition, then check via the
  behaviour record's `(unavailable)` marker in plain-mode (or accept that
  strikethrough checking needs pyte-specific cell inspection).

## CLI profile gotchas (se-llm-skills wave)

### G-CLI-1: console_main dispatch via direct_handlers can bypass subparsers

- **What.** The CLI `console_main` routes some subcommands via a
  `direct_handlers` dict (keyed on argv token) before the argparse
  subparser runs. A handler in `direct_handlers` with a different
  signature than the subparser produces silent arg-drift.
- **Bites.** A Tier A test imports a handler from `cli/main.py` and
  passes an `argparse.Namespace`. If the handler is reached via
  `direct_handlers` in production but via subparser in the test, the
  test exercises a different code path than the user's CLI.
- **Fix.** For every CLI subcommand test, confirm whether the handler
  is reached via subparser or `direct_handlers`. If `direct_handlers`,
  call it with raw argv, not a `Namespace`. Document the dispatch path
  in the behavior record's `Trigger` field.

### G-CLI-2: Real source-code bugs surfaced by behavior interviews are common

- **What.** Behavior interviews on CLI units regularly surface real
  pre-existing source bugs. These appear as gaps between SKILL.md
  description and actual Python behavior. Wave examples: status
  registry corruption guard missing; plugin `OSError` from
  `shutil.copytree` not caught.
- **Bites.** Agent writes records matching desired behavior, writes
  tests to match, tests fail. Failure is not a test bug — it's a real
  implementation gap.
- **Fix.** Tag the record `Regression: yes` and ship a paired code
  fix in the same commit. Do NOT mark `Regression: no` and leave the
  test xfailed without a tracking issue. The behavior record is ground
  truth; code must match it.

### G-CLI-3: Attribute and file name assumptions are frequent agent errors

- **What.** Multiple agents tripped on wrong attribute / file names
  for core infrastructure. Canonical values:
  - `RunStatus.RUNNING` (not `RunStatus.ACTIVE`)
  - `RunRegistry._path` / `RunRegistry._records` (not `_root` / `_workdir`)
  - State file is `registry.json` inside
    `<data_dir>/projects/<slug>/registry.json`
- **Bites.** Any agent that infers names from general patterns instead
  of reading the source. Surfaces as `AttributeError` in test runs.
- **Fix.** Always grep for class definitions before referencing
  attributes. For infrastructure types (`RunStatus`, `RunRegistry`,
  `RunRecord`, `StoragePaths`), read `se_llm_skills/state/` first.

### G-CLI-4: Coverage floor (89%) applies only to full-suite runs

- **What.** `make test` runs all tests with coverage, enforcing the
  89% floor. Individual test files in isolation fall below the floor
  and fail with `FAIL Required test coverage of 89.0% not reached`.
- **Bites.** Running `uv run pytest tests/e2e/cli/test_foo.py`
  directly. Coverage failure looks like a test failure; confuses
  diagnosis.
- **Fix.** Use `make test` for coverage-gated runs. For isolated debug
  runs, pass `--no-cov`:
  `uv run pytest tests/e2e/cli/test_foo.py --no-cov`.
