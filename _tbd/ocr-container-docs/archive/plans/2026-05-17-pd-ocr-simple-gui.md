---
milestone: 12
repo: ConcaveTrillion/ocr-container-meta
status: complete
synced: 2026-05-17
---

# pdomain-ocr-simple-gui — drag-and-drop OCR app (Phase 3 reference consumer)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up `pdomain-ocr-simple-gui` — a minimal FastAPI + React app that lets a user drop images, run OCR, and get plain-text output. Phase 1 ships locally; no labeler, no PGDP pipeline, no trainer required. Also serves as the **reference consumer** that validates `pdomain-ocr-ops`' `LocalStageDispatcher` and lands the `register_default_stages()` helper before `pdomain-prep-for-pgdp` migrates (Phase 1.7).

**Spec reference:** [`docs/superpowers/specs/2026-05-17-pdomain-ocr-simple-gui-design.md`](../specs/2026-05-17-pdomain-ocr-simple-gui-design.md)

**Architecture:**
- Backend: FastAPI + pdomain-ocr-ops suite plumbing (port 8004)
- Frontend: React/Vite SPA using `@concavetrillion/pdomain-ui`
- Deps: `pdomain-book-tools`, `pdomain-ocr-ops`, `@concavetrillion/pdomain-ui`
- Install: `uv tool install pdomain-ocr-simple-gui`

---

## Milestone M0: Repo scaffold

Stand up the empty repo skeleton — Python package, Makefile, CI, CLAUDE.md, agent defs — before any feature work.

### Task M0.1: Create directory + git init + .gitignore + LICENSE + README {#m0-scaffold-files}

model: haiku  effort: S  area: scaffold

**Why:** Establishes the repo identity before any code.

**What:**
- Create `/workspaces/ocr-container/pdomain-ocr-simple-gui/`
- `.gitignore` — copy from `pdomain-prep-for-pgdp/.gitignore` (Python + dist + node_modules + `.venv`)
- `LICENSE` — MIT, ConcaveTrillion (copy from peer repo)
- `README.md` — title, one-paragraph mission, install + launch command
- `git init && git add -A && git commit -m "chore(scaffold): initial repo skeleton"`

**Verification:** `git log --oneline | head -1`
**Acceptance:**
- [ ] Directory exists, git repo initialized
- [ ] `.gitignore`, `LICENSE`, `README.md` present
- [ ] First commit clean

### Task M0.2: pyproject.toml + uv lock {#m0-pyproject}

model: haiku  effort: S  area: scaffold

**Why:** Python package identity, entry point, deps.

**What:** Create `pyproject.toml`:
- `name = "pdomain-ocr-simple-gui"`, `version = "0.1.0a0"`, `requires-python = ">=3.10"`
- `dependencies`: `pdomain-book-tools`, `pdomain-ocr-ops`, `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `aiofiles`
- `[project.scripts] pdomain-ocr-simple-gui = "pd_ocr_simple_gui.__main__:main"`
- `[tool.hatch.build] packages = ["src/pd_ocr_simple_gui"]`
- `author/repo/homepage` copied from `pdomain-prep-for-pgdp/pyproject.toml` (CT / ConcaveTrillion)
- Run `uv lock` to generate lockfile

**Verification:** `uv run python -c "import pd_ocr_simple_gui"`
**Acceptance:**
- [ ] `pyproject.toml` valid; `uv lock` succeeds
- [ ] Entry point resolves

### Task M0.3: Makefile + CI workflow {#m0-makefile-ci}

model: haiku  effort: S  area: scaffold

**Why:** Consistent `make ci AI=1` gate across all pd-* repos.

**What:**
- `Makefile` targets: `install`, `lint`, `typecheck`, `test`, `frontend-build`, `ci`
- `ci` chains: lint → typecheck → test → frontend-build
- `.github/workflows/ci.yml` — runs `make ci AI=1` on push/PR, Python 3.11
- Copy structure from `pdomain-prep-for-pgdp/Makefile` and `.github/workflows/`

**Verification:** `make install && make ci AI=1` (stub passes before any real code)
**Acceptance:**
- [ ] `make ci AI=1` exits 0 on the empty scaffold
- [ ] CI workflow present

### Task M0.4: CLAUDE.md + agent definition {#m0-claude-agent}

model: haiku  effort: S  area: scaffold
Blocked-by: #m0-scaffold-files

**Why:** Agent routing and per-repo guidelines needed before any feature agent runs.

**What:**
- `CLAUDE.md` — repo purpose, stack (FastAPI, React/Vite, pdomain-ui, pdomain-ocr-ops), TDD discipline, memory path
- `.claude/agents/pdomain-ocr-simple-gui.md` in workspace `.claude/agents/` — full-power agent with pre-flight identity check, trigger words, memory path at `/workspaces/ocr-container/.claude/agent-memory/pdomain-ocr-simple-gui/`
- Commit both files

**Verification:** `cat /workspaces/ocr-container/.claude/agents/pdomain-ocr-simple-gui.md | head -5`
**Acceptance:**
- [ ] CLAUDE.md present in repo
- [ ] Agent definition file present in workspace `.claude/agents/`

---

## Milestone M1: FastAPI backend — project CRUD + sidecar IO + prefs

Wire the full backend API surface (jobs, pages, prefs) with stub OCR (returns placeholder text). Frontend work comes later; this milestone validates the Python layer in isolation.

### Task M1.1: Pydantic models (ProjectSpec, PageResult, ProjectStatus) {#m1-models}

model: haiku  effort: S  area: backend
Blocked-by: #m0-pyproject

**Why:** All routes and pipeline share these shapes; define them first so tests compile.

**What:** Create `src/pd_ocr_simple_gui/models.py` with:
- `ProjectSpec`, `PageResult`, `ProjectStatus` exactly as in spec §4
- `AppPrefs` for the prefs payload
- Unit tests in `tests/test_models.py` — round-trip JSON, field validation

**Verification:** `uv run pytest tests/test_models.py -v`
**Acceptance:**
- [ ] All model tests pass
- [ ] `ProjectSpec` round-trips cleanly

### Task M1.2: Project storage (sidecar IO helpers) {#m1-storage}

model: sonnet  effort: M  area: backend
Blocked-by: #m1-models

**Why:** All routes read/write project state via these helpers.

**What:** Create `src/pd_ocr_simple_gui/storage.py`:
- `get_project_dir(project_id) -> Path` — `~/.local/share/pd-suite/simple-gui/projects/{id}/`
- `write_project(spec, status)` / `read_project(id) -> tuple[ProjectSpec, ProjectStatus]`
- `write_page_sidecar(spec, idx, page_dict)` / `read_page_sidecar(spec, idx)`
- `write_txt(spec, idx, text)` / `write_combined_txt(spec)`
- `list_projects() -> list[tuple[ProjectSpec, ProjectStatus]]`
- `delete_project(project_id)`
- Tests in `tests/test_storage.py` using `tmp_path` fixture

**Verification:** `uv run pytest tests/test_storage.py -v`
**Acceptance:**
- [ ] All storage tests pass; no real fs side-effects outside `tmp_path`

### Task M1.3: FastAPI app + jobs routes {#m1-jobs-routes}

model: sonnet  effort: M  area: backend
Blocked-by: #m1-storage

**Why:** Core job lifecycle: create, read, list, delete.

**What:**
- `src/pd_ocr_simple_gui/app.py` — FastAPI app, lifespan, CORS
- `src/pd_ocr_simple_gui/routes/jobs.py`:
  - `POST /api/jobs` — creates project, enqueues background task (stub: immediate done), returns `{project_id}`
  - `GET /api/jobs/{project_id}` — returns `ProjectStatus`
  - `GET /api/jobs` — returns recent project list
  - `DELETE /api/jobs/{project_id}` — deletes project dir
- Tests in `tests/test_routes_jobs.py` using `httpx.AsyncClient`

**Verification:** `uv run pytest tests/test_routes_jobs.py -v`
**Acceptance:**
- [ ] POST → GET roundtrip passes; DELETE removes state

### Task M1.4: Pages routes {#m1-pages-routes}

model: sonnet  effort: M  area: backend
Blocked-by: #m1-jobs-routes

**Why:** Per-page read, text save, image serve.

**What:** `src/pd_ocr_simple_gui/routes/pages.py`:
- `GET /api/pages/{project_id}/{page_idx}` — returns page sidecar JSON
- `GET /api/pages/{project_id}/{page_idx}/image` — streams source image file
- `PUT /api/pages/{project_id}/{page_idx}/text` — body `{text: str}`; writes `.txt` + `page.edited_text`
- `POST /api/pages/{project_id}/{page_idx}/rerun` — stub (returns 501 until M2)
- Tests in `tests/test_routes_pages.py`

**Verification:** `uv run pytest tests/test_routes_pages.py -v`
**Acceptance:**
- [ ] GET/PUT pass; image route streams bytes; rerun returns 501

### Task M1.5: Prefs routes + pdomain-ocr-ops PrefsAdapter wiring {#m1-prefs}

model: sonnet  effort: M  area: backend
Blocked-by: #m1-jobs-routes

**Why:** App prefs (recent projects, default engine/language/output dir) persisted via pdomain-ocr-ops.

**What:**
- `src/pd_ocr_simple_gui/routes/prefs.py`:
  - `GET /api/prefs` — reads `AppPrefs` via `prefs_adapter.read_app("pdomain-ocr-simple-gui")`
  - `PUT /api/prefs` — writes via `prefs_adapter.write_app("pdomain-ocr-simple-gui", payload)`
- Wire `PrefsAdapter` (LocalFilePrefs) into FastAPI app state at startup
- Tests in `tests/test_routes_prefs.py` — mock prefs adapter

**Verification:** `uv run pytest tests/test_routes_prefs.py -v`
**Acceptance:**
- [ ] GET/PUT prefs pass; adapter is injected, not hardcoded

### Task M1.6: `__main__.py` CLI entry point {#m1-entrypoint}

model: haiku  effort: S  area: backend
Blocked-by: #m1-jobs-routes

**Why:** `pdomain-ocr-simple-gui --port N` must start uvicorn.

**What:**
- `src/pd_ocr_simple_gui/__main__.py` — `argparse` with `--port` (default 8004), `--host`, starts `uvicorn`
- Smoke test: `uv run pdomain-ocr-simple-gui --help` exits 0

**Verification:** `uv run pdomain-ocr-simple-gui --help`
**Acceptance:**
- [ ] `--help` exits 0 and prints port/host args

---

## Milestone M2: OCR pipeline + register_default_stages() in pdomain-ocr-ops

Wire real OCR through `pdomain-ocr-ops.gpu.LocalStageDispatcher`. The cross-repo piece (adding `register_default_stages()` to pdomain-ocr-ops) is the critical path item that unblocks Phase 1.7.

### Task M2.1: Add register_default_stages() to pdomain-ocr-ops {#m2-register-default-stages}

model: sonnet  effort: M  area: pdomain-ocr-ops
Blocked-by: #m1-entrypoint

**Why:** `LocalStageDispatcher.register_stage()` exists but nothing registers DocTR/Tesseract runners yet. This is the cross-repo task decided in #181.

**What:** In `pdomain-ocr-ops/pd_ocr_ops/gpu/`:
- `default_stages.py` — `register_default_stages(dispatcher: LocalStageDispatcher) -> None` wires:
  - `"ocr"` / `"cpu"` → `pd_book_tools` DocTR CPU runner callable
  - `"ocr"` / `"tesseract"` → `pd_book_tools` Tesseract CPU runner callable (if available)
- Re-export `register_default_stages` from `pd_ocr_ops.gpu.__init__`
- Tests in `pdomain-ocr-ops/tests/gpu/test_default_stages.py`
- Commit to pdomain-ocr-ops repo

**Verification:** `cd pdomain-ocr-ops && uv run pytest tests/gpu/test_default_stages.py -v`
**Acceptance:**
- [ ] `register_default_stages` importable from `pd_ocr_ops.gpu`
- [ ] Tests pass; DocTR stage registered and callable

### Task M2.2: pipeline.py — OCR orchestration {#m2-pipeline}

model: sonnet  effort: M  area: backend
Blocked-by: #m2-register-default-stages

**Why:** Implements `run_project()` that drives the dispatcher per page and writes sidecars.

**What:** `src/pd_ocr_simple_gui/pipeline.py`:
- `collect_images(source_path) -> list[Path]` — accepts file or dir, sorts, filters `.png/.jpg/.tiff`
- `run_project(spec, dispatcher, status_callback)` — async; iterates pages, calls `dispatcher.run_stage("ocr", ...)`, writes sidecar + txt via storage helpers, calls `status_callback` per page
- Tests in `tests/test_pipeline.py` — mock dispatcher returning stub `StageResult`

**Verification:** `uv run pytest tests/test_pipeline.py -v`
**Acceptance:**
- [ ] Pipeline test passes with mock dispatcher
- [ ] `collect_images` correctly filters non-image files

### Task M2.3: Wire pipeline into jobs route background task {#m2-wire-pipeline}

model: sonnet  effort: M  area: backend
Blocked-by: #m2-pipeline

**Why:** `POST /api/jobs` must run real OCR asynchronously and update project status.

**What:**
- Replace the stub background task in `routes/jobs.py` with real `run_project()` call
- Wire `LocalStageDispatcher` + `register_default_stages()` at app startup (lifespan)
- `POST /api/pages/{project_id}/{page_idx}/rerun` now calls pipeline for single page
- Tests verify status transitions: queued → running → done/error

**Verification:** `uv run pytest tests/test_routes_jobs.py tests/test_routes_pages.py -v`
**Acceptance:**
- [ ] Job transitions queued→running→done in tests
- [ ] Rerun route returns updated `PageResult`

---

## Milestone M3: React frontend — Home screen

Scaffold the Vite SPA and ship Screen 1 (drop zone + recent projects list).

### Task M3.1: Vite + React scaffold + pdomain-ui wiring {#m3-scaffold}

model: sonnet  effort: M  area: frontend
Blocked-by: #m0-makefile-ci

**Why:** Frontend needs build tooling and pdomain-ui installed before any components.

**What:**
- `frontend/` directory with `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`
- Install `@concavetrillion/pdomain-ui` from pdomain-index-npm
  - `.npmrc`: `@concavetrillion:registry=https://concavetrillion.github.io/pdomain-index-npm/`
  - `store-dir=~/.local/share/pnpm/store`
- Import `theme/tokens.css` + `theme/primitives.css` at root layout
- `make frontend-build` calls `vite build`; output to `src/pd_ocr_simple_gui/frontend/`
- Vitest + `@testing-library/react` configured
- Smoke test: `make frontend-build` succeeds

**Verification:** `make frontend-build`
**Acceptance:**
- [ ] `vite build` succeeds; `dist/` produced
- [ ] pdomain-ui tokens.css imported at root

### Task M3.2: AppShell + routing skeleton {#m3-shell}

model: sonnet  effort: M  area: frontend
Blocked-by: #m3-scaffold

**Why:** All screens live inside `<AppShell>`; need routing before adding screens.

**What:**
- `<AppShell deployMode="local" launcherSlot="header">` wrapping the app
- React Router with routes: `/` (Home), `/jobs/:id` (Results), `/jobs/:id/pages/:idx` (PageView)
- `useSuiteSiblings` wired; launcher hides when no siblings
- Unit test: AppShell renders without crashing

**Verification:** `pnpm run test` in frontend/
**Acceptance:**
- [ ] AppShell renders; routing works between screens
- [ ] Launcher hidden when `useSuiteSiblings` returns empty list

### Task M3.3: DropZone + path input + Browse button {#m3-dropzone}

model: sonnet  effort: M  area: frontend
Blocked-by: #m3-shell

**Why:** Primary entry point for Screen 1.

**What:**
- `<DropZone>` component: drag-and-drop single image or folder, "Browse…" button (calls `window.showDirectoryPicker` / `window.showOpenFilePicker`), path text field with inline error on invalid path
- On valid input → navigate to `/new-job` (job config dialog, M4)
- Unit tests: drag event, path validation

**Verification:** `pnpm run test -- DropZone`
**Acceptance:**
- [ ] Drop event captured; path validated; error shown for non-existent path

### Task M3.4: RecentProjectsList {#m3-recent}

model: haiku  effort: S  area: frontend
Blocked-by: #m3-shell

**Why:** Screen 1 shows max-10 recent projects.

**What:**
- `<RecentProjectsList>` — fetches `GET /api/prefs`, renders rows (name, page count, last opened, engine, status)
- Click row → navigate to `/jobs/:id`
- Unit test: renders rows from mock prefs data

**Verification:** `pnpm run test -- RecentProjectsList`
**Acceptance:**
- [ ] Renders mock project list; click navigates

---

## Milestone M4: Job config dialog + results list (Screens 2 + 3)

### Task M4.1: JobConfigDialog {#m4-job-config}

model: sonnet  effort: M  area: frontend
Blocked-by: #m3-dropzone

**Why:** Screen 2 — user configures project before running OCR.

**What:**
- `<JobConfigDialog>` using Radix Dialog from pdomain-ui
- Fields: project name, engine, language, output directory, save-JSON toggle, combined-txt toggle
- Pre-filled from `GET /api/prefs`; editable per-job
- Validation before "Run OCR →": source exists, output dir writable
- On submit: `POST /api/jobs` → navigate to `/jobs/:id`
- Unit test: validation prevents submit with invalid output dir

**Verification:** `pnpm run test -- JobConfigDialog`
**Acceptance:**
- [ ] Invalid output dir prevents submit
- [ ] Successful submit calls `POST /api/jobs`

### Task M4.2: ResultsList with live polling {#m4-results}

model: sonnet  effort: M  area: frontend
Blocked-by: #m4-job-config

**Why:** Screen 3 — live progress while job runs; final list when done.

**What:**
- `<ResultsList>` — polls `GET /api/jobs/:id` every 1s while running, stops on done/error
- Progress bar (`<Progress>` from pdomain-ui) while running
- Page rows: name, `<StatusPip>` chip, first-60-chars preview
- "Re-run all" button (M6); "Open folder" button on completion
- Unit test: renders running state; renders done state; polling stops on done

**Verification:** `pnpm run test -- ResultsList`
**Acceptance:**
- [ ] Running state shows progress bar
- [ ] Polling interval stops when status is done/error

---

## Milestone M5: Per-page view (Screen 4)

### Task M5.1: PageView layout — canvas + textarea {#m5-page-view}

model: sonnet  effort: M  area: frontend
Blocked-by: #m4-results

**Why:** Screen 4 — image viewer + editable text panel.

**What:**
- `<PageView>` two-panel layout inside AppShell `main` slot
- Left: `<PageImageCanvas>` — `src` from `GET /api/pages/:id/:idx/image`, no overlays (all slot props empty per spec #182)
- Right: `<textarea>` with page OCR text fetched from `GET /api/pages/:id/:idx`
- Toolbar: prev/next page nav, Save edits, Re-run page (stub for M6)
- "Save edits" → `PUT /api/pages/:id/:idx/text`; shows toast on success/error
- Unit test: renders image URL; save button calls PUT

**Verification:** `pnpm run test -- PageView`
**Acceptance:**
- [ ] Canvas renders with image src
- [ ] Save edits calls PUT with textarea content

---

## Milestone M6: Page re-run + project re-run

### Task M6.1: Per-page re-run {#m6-page-rerun}

model: sonnet  effort: M  area: fullstack
Blocked-by: #m5-page-view

**Why:** User can re-run OCR on a single page with a different engine.

**What:**
- Frontend: "Re-run page ▾" dropdown in PageView toolbar (DocTR / Tesseract); triggers `POST /api/pages/:id/:idx/rerun`
- Backend: `POST /api/pages/:id/:idx/rerun` (M1.4 stub → real impl via pipeline)
- Page state transitions: running → done; textarea updates
- Tests: backend route test + frontend component test

**Verification:** `uv run pytest tests/test_routes_pages.py -v && pnpm run test -- PageView`
**Acceptance:**
- [ ] Backend rerun route returns updated PageResult
- [ ] Frontend textarea updates after rerun completes

### Task M6.2: Project re-run {#m6-project-rerun}

model: sonnet  effort: M  area: fullstack
Blocked-by: #m6-page-rerun

**Why:** "Re-run all" button reruns every page.

**What:**
- Backend: `POST /api/jobs/{project_id}/rerun` — resets all pages to queued, re-runs pipeline
- Frontend: "Re-run all" button in ResultsList triggers re-run, re-starts polling
- Tests: backend re-run route; frontend button interaction

**Verification:** `uv run pytest tests/ -k rerun -v`
**Acceptance:**
- [ ] Re-run resets pages to queued state
- [ ] Frontend polling restarts after re-run triggered

---

## Milestone M7: Suite integration

### Task M7.1: pd-suite.json + register_self() {#m7-suite-register}

model: sonnet  effort: M  area: suite
Blocked-by: #m1-entrypoint

**Why:** App must register itself in installed.toml for the launcher to discover it.

**What:**
- `src/pd_ocr_simple_gui/pd-suite.json` — fragment per spec §8 (app_id, display_name, package, default_port, icon, description)
- On startup: `pd_ocr_ops.suite.register_self()` via importlib.resources (M2.5 in pdomain-ocr-ops plan, already shipped)
- `mount_routes(app)` mounts `/api/suite/*`
- `--unregister-suite` CLI flag
- `--install-desktop-shortcut` / `--remove-desktop-shortcut` raise `NotImplementedError`
- Tests: suite routes respond; `register_self()` writes installed.toml entry

**Verification:** `uv run pytest tests/test_suite.py -v`
**Acceptance:**
- [ ] Suite routes respond 200
- [ ] installed.toml entry written on startup
- [ ] Desktop shortcut flags raise NotImplementedError

### Task M7.2: App icons {#m7-icons}

model: haiku  effort: S  area: suite
Blocked-by: #m7-suite-register

**Why:** `/api/icons/<size>` route (mounted by pdomain-ocr-ops) needs icon files present.

**What:**
- `src/pd_ocr_simple_gui/icons/` — PNG sizes 16/24/32/48/64/128/256 + simple-gui.ico
- Placeholder icons acceptable for Phase 1 (solid-color squares); real artwork deferred
- Smoke test: `/api/icons/32` returns a PNG

**Verification:** `uv run pytest tests/test_suite.py -k icons -v`
**Acceptance:**
- [ ] `/api/icons/32` returns bytes with content-type image/png

---

## Milestone M8: End-to-end smoke + 0.1.0 release

### Task M8.1: make ci AI=1 green {#m8-ci-green}

model: sonnet  effort: M  area: ci
Blocked-by: #m7-suite-register

**Why:** Full gate must pass before release.

**What:**
- Ensure `make ci AI=1` (lint → typecheck → test → frontend-build) exits 0
- Fix any lint/type errors surfaced by full run
- Minimum coverage thresholds (80%) configured and passing

**Verification:** `make ci AI=1`
**Acceptance:**
- [ ] `make ci AI=1` exits 0
- [ ] All test suites green

### Task M8.2: End-to-end smoke test {#m8-smoke}

model: sonnet  effort: M  area: ci
Blocked-by: #m8-ci-green

**Why:** Validate the full install → launch → OCR cycle works end-to-end.

**What:**
- `tests/smoke/test_e2e.py` — installs the wheel via `uv tool install`, starts the server, drops a test image, waits for job to complete, asserts `.txt` output exists
- Test image: small known PNG from `pdomain-book-tools` test fixtures
- Smoke test is marked `@pytest.mark.slow` and excluded from `make test` but included in `make ci AI=1`

**Verification:** `uv run pytest tests/smoke/ -v`
**Acceptance:**
- [ ] Smoke test installs, runs, produces `.txt` output
- [ ] Job completes with `state=done`

### Task M8.3: Version bump + publish 0.1.0a0 to pdomain-index-pip {#m8-publish}

model: haiku  effort: S  area: release
Blocked-by: #m8-smoke

**Why:** Make the release installable by downstream consumers.

**What:**
- Ensure version is `0.1.0a0` in pyproject.toml
- `CHANGELOG.md` entry for 0.1.0a0
- Tag `v0.1.0a0`; GitHub Actions publishes wheel to pdomain-index-pip
- Verify installable: `uv pip install --index-url <pdomain-index-pip-url> pdomain-ocr-simple-gui==0.1.0a0`

**Verification:** `pip index versions pdomain-ocr-simple-gui --index-url <pdomain-index-pip-url>`
**Acceptance:**
- [ ] Wheel published to pdomain-index-pip
- [ ] `uv tool install pdomain-ocr-simple-gui` installs from index
- [ ] `pdomain-ocr-simple-gui --help` works after install

---

## Success criteria (Phase 1 done)

- [ ] `uv tool install pdomain-ocr-simple-gui` installs cleanly
- [ ] `pdomain-ocr-simple-gui` opens at `http://localhost:8004`
- [ ] Drop a folder of images → job runs → `.txt` files appear in output dir
- [ ] Reopen the project from recent list → all pages visible
- [ ] Per-page view: image renders, text editable + saveable
- [ ] Page re-run and project re-run work
- [ ] Suite launcher shows/hides based on `installed.toml`
- [ ] `make ci AI=1` green
