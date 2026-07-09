---
title: pdomain-ocr-simple-gui reconciliation with pdomain-ui + security hardening
status: draft
date: 2026-05-26
repo: pdomain/pdomain-ocr-simple-gui
related:
  - 2026-05-17-pdomain-ocr-simple-gui-design.md
---

# pdomain-ocr-simple-gui reconciliation with pdomain-ui + security hardening

## 1. Problem

`pdomain-ocr-simple-gui` is shipped but broken in two ways:

1. **Functional gaps.** The "drop zone" on the home page is a text input
   for a server-local folder path — there is no real drag-and-drop and no
   real upload. `PageImageCanvas` is mounted with `words={[]}`, so OCR
   output never renders visually. Multiple UI surfaces are hand-rolled
   despite pdomain-ui shipping equivalents (page tables, page workbench shell,
   testid constants, store factories).
2. **Security/privacy/deps debt.** Thirteen open `status:backlog` issues
   (#17–#34) cover unauth endpoints, caller-controlled `source_path`
   (image disclosure / path traversal), unauth resource exhaustion on OCR
   endpoints, missing `noopener` on suite launcher, swallowed-exception
   logging across `app.py`, Vite/esbuild advisories, an editable
   pdomain-ops sibling pin, unpinned GitHub Actions, and non-self-hosted
   Google Fonts.

This spec defines a two-phase plan: **Phase A — functional repair** that
makes the app usable end-to-end and aligns it with pdomain-ui's shipped
components; **Phase B — hardening** that closes the open security and
deps issues.

## 2. Goals & non-goals

### Goals

- Replace the fake drop zone with real input affordances that work for
  every deployment mode (local-host, local-container, managed).
- Render OCR word overlays on `PageImageCanvas` read-only.
- Swap four hand-rolled UI surfaces for their pdomain-ui equivalents:
  `./testids`, `./worklist`, `./stages/PageWorkbench`, `./stores`.
- Close all 13 open security/privacy/deps issues (#17–#34) in Phase B.
- Preserve the existing `run_project` OCR pipeline behavior unchanged.

### Non-goals

- Word editing or labeler-style correction (this is the *simple* OCR app;
  the labeler-spa owns that surface).
- Postgres / managed-adapter persistence (already deferred workspace-wide).
- New OCR engines or pipeline stages.
- A pd-ocr-trainer-style training loop.

## 3. Modes & runtime detection

The app exposes a `mode` setting at startup, read from
`PD_OCR_SIMPLE_GUI_MODE` (default `local`) or pd-suite registration.
Valid values: `local`, `managed`.

Container detection runs once at startup and is cached. Signals checked
in order:

1. `/.dockerenv` exists (Docker).
2. `/run/.containerenv` exists (Podman).
3. `container` environment variable set (systemd-nspawn, podman).
4. `/proc/1/cgroup` contains `docker`, `containerd`, or `kubepods`.

The result is exposed via a new `GET /api/config` route as
`{mode, is_containerized}`. The frontend reads it once on mount and
uses it to decide which input affordances to render.

### UI affordance matrix

| Mode    | Containerized? | Home-page UI                                                                                                          |
|---------|---------------|-----------------------------------------------------------------------------------------------------------------------|
| local   | yes           | Two tabs: **Upload** (drop/pick: single image, multiple images, or zip) + **Existing folder/zip** (text input, bind-mount hint) |
| local   | no            | Single screen: drop zone (single image, multiple images, folder, or zip) + file/zip picker + folder-path text input    |
| managed | n/a           | Upload only (drop/pick: single image, multiple images, or zip)                                                         |

Every upload affordance accepts **one or more image files**, **a folder
of images**, or **a single `.zip`**. A single image is the smallest
valid input.

Functionally the multipart endpoint is identical across all
configurations; the frontend only varies presentation and which
affordances are visible.

## 4. Backend architecture

### 4.1 `Source` adapter Protocol

New module `src/pd_ocr_simple_gui/sources/`.

```python
class Source(Protocol):
    def materialize(self) -> Path: ...
```

`materialize()` returns a directory of image files ready for
`run_project`. Implementations:

- **`LocalPathSource(path: Path)`** — accepts a folder path, a single
  image file path, or a `.zip` path. For a folder, validates it exists,
  is readable, and is not a symlink-escape; returns the path as-is. For
  a single image, materializes a one-image dir. For a zip, extracts
  into a workspace dir under
  `~/.local/share/pdomain-ocr-simple-gui/extracted/<id>/` with a
  max-uncompressed-size guard (zip-bomb prevention). Only constructible
  in `local` mode — managed mode rejects.
- **`UploadedFilesSource(upload_id: str)`** — points at a staging dir
  under `~/.local/share/pdomain-ocr-simple-gui/uploads/<upload_id>/`,
  populated by the upload route. Accepts a single image, multiple
  images, or a single zip (extracted into the staging dir on upload).

Both adapters raise typed errors (`SourceNotFound`, `SourceInvalid`,
`SourceTooLarge`) that the route layer maps to structured 4xx responses.

### 4.2 New / changed routes

- `GET /api/config` → `{mode, is_containerized}`. New.
- `POST /api/uploads` → multipart streaming endpoint. Streams each part
  to a temp file then atomic-renames into the staging dir. Returns
  `{upload_id}`. Available in both modes. Enforces a max-total-size and
  per-file count cap (closes #18 partially).
- `POST /api/jobs` (existing) → accepts either `{source_path: ...}`
  (local mode only) or `{upload_id: ...}` (both modes) and constructs
  the appropriate `Source`. Other fields unchanged.
- `GET /api/pages/{id}/{idx}/words` → `{words: [{text, bbox: {x,y,w,h},
  confidence}]}`. New, sourced from the existing `PageResult` produced
  by `run_project`. Read-only.
- `GET /api/jobs/{id}/download` → streams a zip of the job's output
  `.txt` files (plus the `combined.txt` if `combined_txt` was set).
  Available in every mode. New.

### 4.3 Output location

`POST /api/jobs` accepts an `output` field on the request body:

```python
class OutputConfig(BaseModel):
    mode: Literal["next_to_source", "specified", "managed"]
    path: Optional[Path] = None  # required when mode="specified"
```

Resolution rules:

- **`next_to_source`** — `.txt` files land in the same directory as
  each source image. Only valid when the source is a
  `LocalPathSource` folder (where "next to" is meaningful). Rejected
  for zip / single-image / upload sources.
- **`specified`** — caller provides an explicit `path`. Validated for
  existence and writability. Available in local mode only (managed
  mode has no shell access to the path).
- **`managed`** — output lands under a server-managed dir
  (`~/.local/share/pdomain-ocr-simple-gui/outputs/<job_id>/`). The caller
  retrieves results via `GET /api/jobs/{id}/download`. This is the
  only valid mode for `managed` deployments and for any source that
  isn't a `LocalPathSource` folder.

The default mode is `next_to_source` when valid, otherwise `managed`.

### 4.4 Pipeline impact

None. `run_project` continues to receive a directory and produce the
same `PageResult` shape it does today. The `Source` adapter is purely
about *how* that directory comes into existence.

## 5. Frontend architecture

### 5.1 Config context

`App.tsx` fetches `/api/config` on mount and exposes `{mode,
is_containerized}` via a React context. All home-page input affordances
read from this context.

### 5.2 Home-page input affordances

`HomePage` renders one of three layouts driven by the matrix in §3.
Each layout converges on the existing `JobConfigDialog`, which branches
its `POST /api/jobs` body on whether the source was a path or an
`upload_id`.

A new shared component, `SourcePicker`, owns:

- A drop zone (uses native browser drag-drop) that accepts: a single
  image, multiple images, a folder, or a `.zip`. Dropped items are
  POSTed to `/api/uploads`.
- A `<input type="file" multiple accept="image/*,.zip">` picker for
  explicit selection (one or more images, or a zip).
- A text input for an existing folder, image, or zip path, with help
  text that varies by `is_containerized`.

`HomePage` shows/hides which `SourcePicker` affordances appear based on
context.

### 5.3 Output config panel

A new `OutputConfigPanel` component is rendered inside
`JobConfigDialog`. It surfaces three radio options matching the
backend `OutputConfig.mode`:

- **Next to source image** — only enabled when the chosen source is a
  `LocalPathSource` folder. Disabled with explanatory help text
  otherwise.
- **Specified folder** — text input for the path. Only enabled in
  local mode. Disabled with help text in managed mode.
- **Managed (download when done)** — always available. In managed
  mode this is the default and only enabled option.

The default selection is `next_to_source` when valid, otherwise
`managed`.

### 5.4 Download affordance

`ResultsPage` shows a **Download results (.zip)** button when the job
finished in `managed` output mode (or when the user explicitly asks for
the zip). Hooks to `GET /api/jobs/{id}/download`.

### 5.5 pdomain-ui swaps

- **`@concavetrillion/pdomain-ui/testids`** — replace every hardcoded
  `data-testid="..."` string in this repo with the imported constant.
  Mechanical.
- **`@concavetrillion/pdomain-ui/worklist`** — replace the hand-rolled tables
  in `RecentProjectsList` and `ResultsPage` with the shipped widget.
  Pulls in pdomain-ui's pagination/sort behavior.
- **`@concavetrillion/pdomain-ui/stages/PageWorkbench`** — wrap
  `PageViewPage` content. Canvas + word overlay become the workbench
  body.
- **`@concavetrillion/pdomain-ui/stores`** — replace hand-rolled fetch in
  `App.tsx:16–64` (prefs) and polling logic in `RecentProjectsList` /
  `ResultsPage` with the store factories. Removes the `App.tsx:62`
  TODO stub.

### 5.6 Word overlays

`PageViewPage` fetches `/api/pages/{id}/{idx}/words` alongside `/image`
and passes the array to `PageImageCanvas` via the existing `words` prop.
No edit handlers — this app is read-only by spec. Removes the
`words={[]}` line at `PageViewPage.tsx:251`.

## 6. Error handling

- Source materialization errors map to 4xx with `{error_code,
  message}` body. Frontend surfaces these inline in the SourcePicker.
- Upload failures (partial write, size cap exceeded) leave no staging
  dir behind (cleanup via try/finally).
- Zip extraction enforces a configurable
  `PD_OCR_SIMPLE_GUI_MAX_UNCOMPRESSED_BYTES` ceiling (default 2 GiB).
  Exceeding raises `SourceTooLarge`.
- Container detector is a pure function; failures fall through to
  `is_containerized=False`.
- All `except Exception: pass` blocks in `app.py` (lines 46, 56, 65,
  105) are replaced with `logger.exception(...)` plus structured
  context in Phase B (#29–#34).

## 7. Testing

Per the workspace FastAPI+SPA contract, `test_routes_root.py` already
covers SPA serving and must remain green.

New backend tests (pure-Python, no skipif):

- `test_sources.py` — both `Source` impls. Cases: happy path folder,
  happy path zip, missing folder, unreadable folder, symlink escape,
  zip-bomb (synthetic), invalid zip, oversized zip.
- `test_config_route.py` — `/api/config` returns the right `mode` for
  each env-var value; `is_containerized` toggles based on a
  monkeypatched detector.
- `test_uploads.py` — happy path, size cap, file count cap, partial
  write cleanup.
- `test_words_route.py` — overlay payload shape, missing page,
  out-of-range index.
- `test_output_config.py` — each `OutputConfig.mode` resolves the
  expected target directory; rejection cases (`next_to_source` with
  a non-folder source, `specified` in managed mode).
- `test_download_route.py` — happy-path zip stream, 404 on missing
  job, content-disposition header.

New frontend Vitest cases:

- `HomePage.test.tsx` — three layouts (local+containerized,
  local+not, managed), each driven by a mocked `/api/config`.
- `SourcePicker.test.tsx` — drop, file-pick, path-input variants
  covering single image, multiple images, folder, and zip cases.
- `OutputConfigPanel.test.tsx` — enabled/disabled state per source
  type and per mode.
- `ResultsPage.test.tsx` — download button visible when output mode
  is `managed`, hidden otherwise.
- `PageViewPage.test.tsx` — overlay fetch + canvas `words` prop wiring.

## 8. Phase B — security/privacy/deps hardening

Groups, in execution order:

### B1 — Logging hygiene first (mechanical, unblocks observability)

Issues #29–#34. Replace the 4× `except Exception: pass` in `app.py:46,
56, 65, 105` and the other swallowed-exception sites with
`logger.exception(...)` plus structured fields. No behavior change;
only observability.

### B2 — Auth & access

- #23 unauthenticated endpoints — introduce an auth middleware.
  Mechanism per pd-* convention (token or session) — decision deferred
  to the writing-plans skill but a single mechanism applies to all
  protected routes.
- #17 caller-controlled `source_path` — finished off here after
  `LocalPathSource`'s initial validation in Phase A. Audit any
  remaining caller-controlled paths in the route layer.
- #18 unauth resource exhaustion on OCR endpoints — rate limit + a
  max-pages-per-job cap.
- #19 unauth suite-launch process spawn — gated behind the new auth
  middleware.

### B3 — Frontend / browser

- #26 missing `noopener` on suite launcher links — one-line attribute
  fix.
- #24 self-host Google Fonts — vendor woff2 files into
  `frontend/public/fonts/`, replace the `<link>` to
  `fonts.googleapis.com`.
- #25 already shipped (Copy path button) — verify and close if not
  already closed.

### B4 — Supply chain

- #20–#22 Vite / esbuild advisories — `make update-pd-deps` cycle,
  regenerate lockfile, verify `make ci` green.
- #27 editable pdomain-ops sibling pin — replace with `pdomain-ops==X.Y.Z`
  from pdomain-index-pip.
- #28 unpinned GitHub Actions — pin to commit SHAs.

## 9. Open questions

- **Auth mechanism for B2.** Token-in-header vs session cookie vs
  pd-suite-issued credential. The writing-plans pass should pick one,
  citing whichever sibling pd-* repo already established the
  convention.
- **Max upload / extracted-zip sizes.** Defaults proposed: 2 GiB
  uncompressed, 5000 files. Confirm during plan-writing or first
  ship-slice.
- **Whether `LocalPathSource` should be available at all in containerized
  local mode.** Spec says yes (bind-mount workflow); this should be
  verified with a real container test in Phase A acceptance.
