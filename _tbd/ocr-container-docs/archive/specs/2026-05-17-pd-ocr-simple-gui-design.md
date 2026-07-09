# pdomain-ocr-simple-gui — design spec

**Date:** 2026-05-17
**Session:** `simple-ocr-gui`
**Scope:** Minimal local-only OCR app. Phase 3 consumer of `pdomain-ui` + `pdomain-ops`.
Serves as the reference implementation for "smallest pdomain-ui consumer."

---

## 1. Goals & non-goals

### Goals

1. Let a user drop a single image or a folder of images, run OCR, and get plain-text output — with no labeler, no PGDP pipeline, no trainer.
2. Show OCR results in-app per page: image with toggleable word bboxes + editable text area.
3. Persist projects so the user can reopen past jobs and re-run OCR at the project or page level.
4. Be independently installable: `uv tool install pdomain-ocr-simple-gui` — no suite required.

### Non-goals

1. No URL / web-archive fetching (that's pd-prep's domain).
2. No word-level selection, rebox, erase, char-fixer, or confidence display.
3. No ground-truth matching or review workflow.
4. No multi-user or hosted mode in Phase 1.
5. No hOCR or JSON as user-facing output formats (JSON is internal project state).
6. Manual text edits are **not** preserved across a re-run — re-run replaces page content.

### Hard design principle

Each pd-* app is independently installable. `pdomain-ocr-simple-gui` must work without
`pdomain-ocr-labeler-spa`, `pdomain-prep-for-pgdp`, `pd-ocr-trainer`, or any other suite app
present at runtime. `pdomain-ui` and `pdomain-ops` are wheel dependencies of the app itself.

---

## 2. Architecture overview

```
pdomain-ocr-simple-gui wheel
  pd_ocr_simple_gui/
    __main__.py            CLI entry: pdomain-ocr-simple-gui --port 8004
    app.py                 FastAPI app + pd_ocr_ops.suite.mount_routes()
    routes/
      jobs.py              POST /api/jobs  GET /api/jobs/{id}
      pages.py             GET /api/pages/{job_id}/{page_idx}
                           PUT /api/pages/{job_id}/{page_idx}/text
                           POST /api/pages/{job_id}/{page_idx}/rerun
      prefs.py             thin wrapper; suite prefs mounted by pdomain-ops
    pipeline.py            orchestrates pdomain-ops StageDispatcher per page
    models.py              Pydantic: ProjectSpec, ProjectStatus, PageResult
    frontend/              React SPA (bundled into wheel as package data)
  icons/                   PNG sizes 16/24/32/48/64/128/256 + simple-gui.ico + .icns
                           (per cross-cut §3; served by pdomain-ops `/api/icons/<size>`)
```

**Port:** 8004

**Install / launch:**

```
uv tool install pdomain-ocr-simple-gui
pdomain-ocr-simple-gui            # starts on http://localhost:8004
pdomain-ocr-simple-gui --port 9000
```

**Dependency graph:**

```
pdomain-ocr-simple-gui
  ├── pdomain-book-tools   (data models, OCR primitives — Python types come from here)
  ├── pdomain-ops      (suite plumbing, GPU dispatch adapters)
  └── @concavetrillion/pdomain-ui  (PageImageCanvas, AppShell, primitives, theme)
```

TS types for `Word`/`Block`/`Page` resolve via `@concavetrillion/pdomain-ui/types`
(codegen from pdomain-book-tools schemas per pdomain-ui plan M4) — the SPA never imports
TS shapes from a pdomain-book-tools npm package, because there isn't one.

---

## 3. Screens & UX flow

### Screen 1 — Home

Default view on launch. Two sections:

**Source entry** — three entry points that all resolve to an absolute local path:
- Drop zone (drag and drop a single image file or a folder of images)
- "Browse…" button (native OS file/folder picker)
- Path text field — type or paste a filesystem path; validated on blur with inline error if the path does not exist

**Recent projects list** — below the drop zone; max 10 entries (persisted in app prefs).
Each row shows: source name, page count, last-opened date, engine used, status.
Clicking a row reopens the project (navigates to Screen 3 with existing data loaded).

Settings gear icon (top-right) opens the prefs panel:
- Engine (DocTR / Tesseract)
- Language
- Default output directory
- "Save JSON sidecars to output folder" (default off)
- "Write combined .txt file" (default on)

### Screen 2 — Job config dialog

Appears after the user drops a source or presses Enter in the path field.
Pre-filled from app prefs; all fields editable for this job.

Fields:
- Project name (default: inferred from source folder/file name)
- Engine (DocTR / Tesseract)
- Language
- Output directory + "Browse…" button
- "Save JSON sidecars to output folder" toggle
- "Write combined .txt file" toggle

Validation before allowing "Run OCR →":
- Source path exists and is a file or directory
- Output directory is writable (created if absent)

"Run OCR →" starts the job and navigates to Screen 3.

### Screen 3 — Results list

**While running:**
- "Processing N of M pages…" progress bar
- Pages appear in the list as they complete: page name, status (done / error), first ~60 chars of OCR text

**When complete:**
- "Complete — saved to `/path/to/output/`" banner + "Open folder" button
- "Re-run all" button (re-runs OCR on every page with current settings; replaces all content)

**Page list rows (always):**
- Page name / index
- Status chip: done / error / running / queued
- First line of OCR text (truncated)
- Click row → navigate to Screen 4 for that page

### Screen 4 — Per-page view

Two-panel layout (AppShell `main` slot):

**Left: image panel**
- `<PageImageCanvas>` — image only, no overlays
- Read-only — no selection, no bbox display, no editing tools
- (Decided #182, 2026-05-17: this is the simple OCR app; no bbox UI.
  Re-run/labeler workflows for box review live in `pdomain-ocr-labeler-spa`.)

**Right: text panel**
- `<textarea>` (or `contentEditable` block) containing the page's plain OCR text
- User can type directly; changes are not auto-saved
- "Save edits" button → `PUT /api/pages/{job_id}/{page_idx}/text`; overwrites
  the `.txt` file and stores the edited text as the new `page.edited_text`
  field in the JSON sidecar. `page.blocks` is left as the last-OCR'd snapshot
  (no merge attempted — coordinates are no longer meaningful for the edited
  text, but blocks are never displayed in this app). Re-run replaces both.

**Toolbar (above both panels):**
- `[← Prev]` / `[Next →]` page navigation
- `[Save edits]`
- `[Re-run page ▾]` — inline engine selector (DocTR / Tesseract); triggers
  `POST /api/pages/{job_id}/{page_idx}/rerun`; replaces text + JSON for that
  page only; manual edits are discarded

---

## 4. Data model & persistence

### Project storage

Each project is stored at:

```
~/.local/share/pd-suite/simple-gui/projects/{project_id}/
  project.json          ProjectSpec + ProjectStatus metadata
  pages/
    {page_name}.json    pdomain-book-tools Page sidecar for each page
```

Projects persist until the user deletes the project from the recent list (which removes the directory). They survive app restarts and version upgrades.

### Output files (written to user-chosen output directory)

| File | Always? | Notes |
|------|---------|-------|
| `{page_name}.txt` | Yes | Plain text, one file per page |
| `{book_name}.txt` | If "combined" toggle on | All pages joined in order |
| `{page_name}.json` | If "save JSON" toggle on | Copies the project sidecar alongside the .txt |

### Pydantic models

```python
class ProjectSpec(BaseModel):
    project_id: str           # uuid4
    name: str
    source_path: str          # absolute path to file or folder
    output_dir: str
    engine: Literal["doctr", "tesseract"]
    language: str             # e.g. "en"
    save_json: bool = False
    combined_txt: bool = True
    created_at: datetime
    last_opened_at: datetime

class PageResult(BaseModel):
    page_idx: int
    page_name: str
    state: Literal["queued", "running", "done", "error"]
    text_preview: str = ""    # first 80 chars for results list
    error: str | None = None

class ProjectStatus(BaseModel):
    project_id: str
    state: Literal["queued", "running", "done", "error"]
    page_count: int
    pages_done: int
    pages: list[PageResult]
```

### App prefs (per-app file via pdomain-ops PrefsAdapter.write_app)

Per-app prefs and domain data go through `prefs_adapter.write_app("pdomain-ocr-simple-gui", payload)`
and `prefs_adapter.read_app("pdomain-ocr-simple-gui")`. The Phase 1 LocalFilePrefs
implementation stores them at:

```
~/.local/share/pd-suite/pdomain-ocr-simple-gui/app_prefs.json
```

Hosted Phase 4 swaps the adapter implementation (e.g., `PerUserDBPrefs`) without
touching simple-gui — the `read_app/write_app` interface is the abstraction
boundary. (Decided #184, 2026-05-17. Per-app file avoids shared-filelock
contention on every project-open; UIPrefs `common.*` file stays for genuinely
cross-app UI tokens like theme/density/layer_colors.)

Payload shape:

```json
{
  "default_engine": "doctr",
  "default_language": "en",
  "default_output_dir": "/home/user/ocr-output",
  "save_json_default": false,
  "combined_txt_default": true,
  "recent_projects": [
    { "project_id": "...", "name": "belloc-survivals", "last_opened_at": "..." }
  ]
}
```

---

## 5. Backend API

All routes are mounted under the FastAPI app. Suite routes (`/api/suite/*`) are
mounted by `pd_ocr_ops.suite.mount_routes(app)`.

### Jobs

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/jobs` | Create + start a project. Body: `ProjectSpec`. Returns `{ project_id }`. Starts background task. |
| `GET`  | `/api/jobs/{project_id}` | Returns `ProjectStatus`. |
| `GET`  | `/api/jobs` | Returns list of recent `ProjectStatus` entries (from prefs). |
| `DELETE` | `/api/jobs/{project_id}` | Deletes project directory + removes from prefs. |

### Pages

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/pages/{project_id}/{page_idx}` | Returns the full `Page` sidecar JSON for this page. |
| `GET`  | `/api/pages/{project_id}/{page_idx}/image` | Streams the source image file. Backend populates `page.image_url` (read by `<PageImageCanvas>` per pdomain-ui M5.3) with this path. |
| `PUT`  | `/api/pages/{project_id}/{page_idx}/text` | Body: `{ text: str }`. Overwrites `.txt` file and writes `page.edited_text` in the JSON sidecar. `page.blocks` is left as the last-OCR'd snapshot (not merged; not displayed). |
| `POST` | `/api/pages/{project_id}/{page_idx}/rerun` | Body: `{ engine: str }`. Re-runs OCR on this page; replaces JSON sidecar + `.txt`. Returns updated `PageResult`. |

### OCR pipeline (`pipeline.py`)

```python
async def run_project(spec: ProjectSpec, dispatcher: StageDispatcher) -> None:
    images = collect_images(spec.source_path)  # sorts by filename
    for idx, img_path in enumerate(images):
        stage_result = await dispatcher.run_stage(
            "ocr", f"{spec.project_id}/{idx}",
            image_path=img_path,
            engine=spec.engine,
            language=spec.language,
        )
        page = stage_result.metadata["page"]  # pdomain-book-tools Page, see note below
        write_sidecar(spec, idx, page)
        write_txt(spec, idx, page)
        if spec.save_json:
            copy_sidecar_to_output(spec, idx)
    if spec.combined_txt:
        write_combined_txt(spec)  # pages joined with "\n-----\n" separator
```

`collect_images` accepts a single image file or a directory; returns a sorted list
of `.png` / `.jpg` / `.tiff` paths. Unknown file types are skipped with a warning.

**StageResult shape (pdomain-ops M7.1).** `dispatcher.run_stage(...)` returns
`StageResult{stage_id, page_id, device, duration_ms, output_key, metadata}` —
**not** a `Page`. Phase 1 simple-gui carries the page payload inline via
`metadata["page"]` (Python dict serializable to `pd_book_tools.Page`). The
`output_key`/storage-adapter route is reserved for Phase 4 hosted mode.

**OCR dispatch surface (decided #181, 2026-05-17).** simple-gui drives the
work that lands the OCR dispatch surface in pdomain-ops. Concretely:
pdomain-ops M8.3 (`register_stage()` plumbing) is enough infrastructure;
simple-gui's plan adds the **`register_default_stages(dispatcher)`** helper
to pdomain-ops that wires DocTR + Tesseract local-CPU runners (the runners
themselves live in pdomain-book-tools). simple-gui's startup calls
`register_default_stages(dispatcher)` then `dispatcher.run_stage("ocr", ...)`.
**simple-gui is the reference consumer** that validates pdomain-ops's
dispatch design end-to-end before pgdp-prep migrates. Phase 1.7 reframes
from "lift pgdp-prep's GPU code into pdomain-ops" to "adopt the validated
surface + lift Modal/shared-container backends pgdp-prep specifically
needs" — but that reframe is a separate decision tracked against the
Phase 1.7 plan itself.

---

## 6. Frontend components

Uses `pdomain-ui` throughout. No app-specific canvas or worklist implementation.

| Component | Source | Notes |
|-----------|--------|-------|
| `<AppShell>` | `pdomain-ui/shell` | `deployMode="local"`, `launcherSlot="header"`, launcher hides when no siblings |
| `<PageImageCanvas>` | `pdomain-ui/canvas` | Image only; all overlay slots empty. No selection, no bbox layer, no editing tools (decided #182) |
| `Button`, `Progress`, `Chip`, `StatusPip` | `pdomain-ui/primitives` | Standard suite primitives |
| All icons | `pdomain-ui/icons` | Never import `lucide-react` directly |
| Theme | `pdomain-ui/theme/tokens.css` + `primitives.css` | Imported at root layout |
| `createUIPrefsStore` | `pdomain-ui/stores` | Wired via `<AppShell uiPrefsConfig>` |
| `useSuiteSiblings` | `pdomain-ui/shell` | Drives launcher tile visibility |

App-specific components (live in `frontend/src/components/`):
- `<DropZone>` — drop target + path input + browse button
- `<RecentProjectsList>` — renders recent projects from prefs
- `<JobConfigDialog>` — pre-filled form; validates before submit
- `<ResultsList>` — live-updating page list; polls `GET /api/jobs/{id}`
- `<PageView>` — two-panel layout: `<PageImageCanvas>` (image only) + `<textarea>`; toolbar with prev/next, save, re-run

**Test IDs.** No Playwright driver agent targets simple-gui in Phase 1, so the
app uses ad-hoc `data-testid` values rather than the shared
`@concavetrillion/pdomain-ui/testids` contract. Adopt the contract if a driver agent
is added later.

---

## 7. Error handling

| Scenario | Handling |
|----------|----------|
| Source path does not exist | Inline error on path field (before job starts) |
| Source path contains no images | Error shown in job config dialog |
| Output dir not writable | Error shown in job config dialog |
| Single page OCR fails | Page state set to `error`; error message in row; rest of job continues |
| All pages fail | Job state `error`; banner in Screen 3 |
| Re-run OCR fails | Page state reverts to previous; error shown in Screen 4 toolbar |
| Save edits fails (disk full, etc.) | Toast error in Screen 4 |

No automatic retry. Re-run (manual) is the recovery path for page errors.

---

## 8. Suite integration

- `pd_ocr_ops.suite.register_self()` called on first run; writes entry to
  `~/.local/share/pd-suite/installed.toml`
- `pd_ocr_ops.suite.mount_routes(app)` mounts `/api/suite/*`
- `--unregister-suite` CLI flag removes the `installed.toml` entry
- `--install-desktop-shortcut` / `--remove-desktop-shortcut` flags present;
  raise `NotImplementedError` (Phase 4 implementation per desktop-launcher-integration spec)
- Launcher tile in `<AppShell>` hides automatically when no other suite apps installed

**Icons** are served via pdomain-ops' `/api/icons/<size>` route (mounted by
`mount_routes(app)`), which resolves from this app's `icons/` directory. The
same endpoint feeds both the in-app launcher tile and the catalog entry below.

**`pd-suite.json` fragment** (shipped inside this wheel at
`pd_ocr_simple_gui/pd-suite.json`; read by `register_self()` via
`importlib.resources`. Per #180 decision, each app owns its own fragment;
`installed.toml` is the catalog.):

```json
{
  "app_id": "pdomain-ocr-simple-gui",
  "display_name": "Simple OCR",
  "package": "pdomain-ocr-simple-gui",
  "default_port": 8004,
  "icon": "simple-gui",
  "description": "Drag-and-drop OCR for scanned images."
}
```

---

## 9. Phase staging

### Phase 1 (this spec — bootstrapped after pdomain-ui + pdomain-ops exist)

**Ordering vs trainer-spa.** Cross-cut §7 lists trainer-spa as Phase 3.1 and
simple-gui as Phase 3.2, but simple-gui is the smaller of the two and serves as
the reference implementation for "smallest pdomain-ui consumer." Build simple-gui
first; trainer-spa can follow and inherit any patterns simple-gui surfaces.

**Reference-consumer role (decided #181).** simple-gui's plan owns building
the OCR dispatch surface (`register_default_stages()` helper) in pdomain-ops.
That milestone validates pdomain-ops's M8 LocalStageDispatcher with a real
consumer before pgdp-prep migrates (Phase 1.7 — which reframes accordingly).
simple-gui does **not** hard-depend on Phase 1.7; pgdp-prep adopts the same
surface in its own time.


- M0: Repo scaffold (pyproject, Makefile, git init, CI workflow, agent defs)
- M1: FastAPI backend — project CRUD, pipeline stub, sidecar IO, prefs wiring
- M2: OCR pipeline wired to `pdomain-ops.gpu.LocalStageDispatcher` — includes
  landing `register_default_stages()` helper in pdomain-ops (DocTR + Tesseract
  CPU runners from pdomain-book-tools); simple-gui calls it at startup. Cross-repo
  task; see #181 decision.
- M3: React frontend — Home screen (drop zone + path input + browse + recent list)
- M4: Job config dialog + results list (Screen 2 + Screen 3)
- M5: Per-page view (Screen 4) — canvas + bbox toggle + editable textarea + save
- M6: Page re-run + project re-run
- M7: Suite integration — `register_self`, launcher, desktop-shortcut stubs
- M8: End-to-end smoke test; `make ci AI=1` green; 0.1.0 release to pdomain-index-pip

### Deferred (future phases)

| Item | Notes |
|------|-------|
| Hosted-mode adapters | Phase 4 per cross-cut design |
| Desktop shortcut real implementations | Phase 4 per desktop-launcher-integration spec |
| Zip file as source | Not in Phase 1; add if requested |
| Batch export (multiple projects to one combined file) | Not in scope |
| Per-word text editing (inline click-to-edit) | Explicitly out of scope — use the labeler |

---

## 10. Open questions from review (2026-05-17)

Six design questions surfaced by the 2026-05-17 spec review. Each is filed as a
`kind:spec` issue in `ConcaveTrillion/ocr-container-meta`. The spec's downstream
plan decomposition is blocked on these decisions where noted.

| # | Question | Issue | Affects |
|---|---|---|---|
| 1 | ~~`register_self()` — pdomain-ops or per-app?~~ **Decided 2026-05-17** ([#179](https://github.com/ConcaveTrillion/ocr-container-meta/issues/179)): pdomain-ops ships the helper; auto-detects via `importlib.resources` on caller package's `pd-suite.json`. New task added: pdomain-ops M2.5. | [#179](https://github.com/ConcaveTrillion/ocr-container-meta/issues/179) | §8; pdomain-ops plan M2.5 — applied |
| 2 | ~~Who ships the baseline `pd-suite.json` catalog?~~ **Decided 2026-05-17** ([#180](https://github.com/ConcaveTrillion/ocr-container-meta/issues/180)): per-app fragment in each wheel; `installed.toml` is the catalog. | [#180](https://github.com/ConcaveTrillion/ocr-container-meta/issues/180) | §8; cross-cut §3 — applied |
| 3 | ~~OCR stage registration timing?~~ **Decided 2026-05-17** ([#181](https://github.com/ConcaveTrillion/ocr-container-meta/issues/181)): simple-gui's plan drives building `register_default_stages()` in pdomain-ops; simple-gui is the reference consumer. Phase 1.7 reframes from "lift pgdp-prep GPU code" to "adopt validated surface." | [#181](https://github.com/ConcaveTrillion/ocr-container-meta/issues/181) | §5, §9 — applied; Phase 1.7 plan reframe deferred |
| 4 | ~~Save-edits merge semantics?~~ **Decided 2026-05-17** ([#182](https://github.com/ConcaveTrillion/ocr-container-meta/issues/182)): no bbox UI at all in simple-gui. Save writes `page.edited_text`; `page.blocks` left as last-OCR'd snapshot (never displayed). Box review workflows belong in `pdomain-ocr-labeler-spa`. | [#182](https://github.com/ConcaveTrillion/ocr-container-meta/issues/182) | §3 Screen 4, §5, §6 — applied |
| 5 | ~~`/healthz` home?~~ **Decided 2026-05-17** ([#183](https://github.com/ConcaveTrillion/ocr-container-meta/issues/183)): centralized in pdomain-ops `mount_routes()`. New task: pdomain-ops M4.7. | [#183](https://github.com/ConcaveTrillion/ocr-container-meta/issues/183) | pdomain-ops plan M4.7 — applied |
| 6 | ~~`recent_projects` storage?~~ **Decided 2026-05-17** ([#184](https://github.com/ConcaveTrillion/ocr-container-meta/issues/184)): per-app file via `PrefsAdapter.write_app()`; LocalFilePrefs writes per-app at `~/.local/share/pd-suite/<app_id>/app_prefs.json`; UIPrefs `common.*` only for cross-app UI tokens. Hosted adapter swaps the impl without touching apps. pdomain-ops M3.2/M3.3 task updates applied. | [#184](https://github.com/ConcaveTrillion/ocr-container-meta/issues/184) | §4; cross-cut §4; pdomain-ops M3 — applied |

**Resolved by this review (not filed as issues):**

- **Port reconciliation.** simple-gui keeps `8004`; cross-cut §3 line 146 updated from `8003` to match. Trainer-spa free to pick `8003`/`8005`.
- **StageResult → page payload.** Phase 1 carries the page via `stage_result.metadata["page"]` (inline). `output_key`/storage-adapter route deferred to Phase 4 hosted mode. Documented in §5.
- **Canvas selection props.** pdomain-ui plan M5.1 description updated to mark selection props optional so read-only consumers don't thread no-op pairs.

---

## 11. Phase-1-done success criteria

- [ ] `uv tool install pdomain-ocr-simple-gui` installs cleanly with pdomain-ui + pdomain-ops as deps
- [ ] `pdomain-ocr-simple-gui` opens at `http://localhost:8004`
- [ ] Drop a folder of images → job runs → `.txt` files appear in output dir
- [ ] Reopen the project from recent list → all pages still visible
- [ ] Per-page view: image renders, text is editable + saveable (no bbox UI per #182)
- [ ] Page re-run: OCR re-runs, replaces text
- [ ] Project re-run: all pages re-run
- [ ] Suite launcher shows/hides correctly based on `installed.toml`
- [ ] `make ci AI=1` green

---

## Related artifacts

- Reminder: [`docs/runbooks/spec-pdomain-ocr-simple-gui.md`](../reminders/spec-pdomain-ocr-simple-gui.md)
- Cross-cut design: [`docs/specs/2026-05-16-cross-cut-design.md`](2026-05-16-cross-cut-design.md) — §3 (install model), §4 (pdomain-ui surface), §7 Phase 3
- pdomain-ops plan: [`docs/plans/2026-05-16-pdomain-ops-new-repo.md`](../plans/2026-05-16-pdomain-ops-new-repo.md)
- pdomain-ui plan: [`docs/plans/2026-05-16-pdomain-ui-new-repo.md`](../plans/2026-05-16-pdomain-ui-new-repo.md)
- Desktop launcher: [`docs/runbooks/desktop-launcher-integration.md`](../reminders/desktop-launcher-integration.md)
