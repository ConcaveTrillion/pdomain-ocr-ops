# Cross-cut design — shared UI library, ops library, and suite plumbing

**Date:** 2026-05-16
**Session:** `cross-cut`
**Scope:** Establish two new foundation libraries (one TypeScript, one Python),
two new release indexes, and the suite-level plumbing that lets every pd-*
end-user app share frontend components, backend operations, prefs, and
sibling-app discovery — without coupling deployments or forcing users into
a full suite install.

---

## 1. Goals & non-goals

### Goals

1. Eliminate duplicate canvas + word-panel code between `pdomain-prep-for-pgdp` and
   `pdomain-ocr-labeler-spa`.
2. Give the upcoming `pdomain-ocr-trainer-spa`, `pdomain-ocr-simple-gui`, and future
   `pd-proofreader` a turn-key starting kit of shared frontend components and
   backend operations.
3. Establish the seed (`<AppShell launcherSlot>` + `pd-suite.json` +
   `installed.toml` registry) that grows into optional unified-shell features in
   a later phase, without ever requiring a unified host process.
4. Standardize the suite on one state library (Zustand), one canvas pattern
   (slot-based Konva), one structural type contract (mirrors `pdomain-book-tools`),
   and one visual language (the existing workspace-level
   `docs/design-system/` — tokens.css + primitives.css + DESIGN_LANGUAGE.md —
   becomes the runtime CSS source-of-truth, owned by pdomain-ui).

### Non-goals (Phase 1)

1. No unified shell process — every app continues to ship and deploy
   independently.
2. No cross-app auth or session unification — each app keeps whatever it has
   (typically none, for local-only use).
3. No migration of the legacy NiceGUI `pd-ocr-labeler` — superseded by
   `pdomain-ocr-labeler-spa`.
4. No multi-pass review model — captured as a future extension on
   `pdomain-book-tools`'s `Word.review`.
5. The future "unified shell" is a launcher *feature* inside any app, never a
   host process; sibling apps are always optional.

### Hard design principle (constrains all phases)

**Each pd-* app is independently installable.** A user who wants only the
simple drag-and-drop OCR installs `pdomain-ocr-simple-gui` (one wheel + bundled
React SPA, single binary on PATH via `uv tool install`) and never has to
know labeler, pgdp, trainer, or proofreader exist. Shared libraries
(`pdomain-ui`, `pdomain-ops`) are dependencies *of the app*, not of the suite.
Sibling apps are never required at runtime.

---

## 2. Architecture overview

Three foundation libraries (each its own pd-* repo), one new release index,
and a renamed existing index:

```
END-USER APPS  (each independently installable; no required suite)
+-----------------+------------------+--------------------+
|  pdomain-ocr-cli     |  pd-ocr-simple-  |  pdomain-prep-for-pgdp  |
|  (CLI, no UI)   |  gui (NEW)       |                    |
+-----------------+------------------+--------------------+
|  pd-ocr-        |  pd-ocr-trainer- |  pd-proofreader    |
|  labeler-spa    |  spa (NEW)       |  (FUTURE)          |
+-----------------+------------------+--------------------+
        | npm install                  | pip install (uv tool)
        v                              v
  +-------------------------+   +------------------------------+
  | pdomain-ui (TS/React)  NEW   |   | pdomain-ops (Python)  NEW     |
  | - PageImageCanvas (slot)|   | - Word/Line/Block mutations  |
  | - WordList (slot)       |   | - OCR pipeline orchestration |
  | - AppShell+launcherSlot |   | - Sidecar JSON IO            |
  | - Primitives (CSS + Radix-scoped) | - Suite registry + prefs |
  | - Icons (lucide+bespoke)|   | - GPU dispatch adapters      |
  | - Theme (design-system) |   | - Sibling-spawn util         |
  | - Zustand stores        |   | - Desktop launcher (stub)    |
  | - Types (mirror books)  |   +------------------------------+
  +-------------------------+               |
                                            | pip install
                                            v
                                +------------------------------+
                                | pdomain-book-tools (Python)       |
                                | - data models (Word/Line/    |
                                |   Block/Page + chars/review/ |
                                |   matching sub-objects)      |
                                | - OCR primitives             |
                                | - schemas.emit CLI           |
                                +------------------------------+

RELEASE INDEXES (self-hosted, GitHub Pages backed)
  pdomain-index-pip  - Python wheels (PEP 503)            [RENAME from pd-index]
  pdomain-index-npm  - npm packages (Verdaccio-style)     [NEW]
```

**Cross-app launcher** lives in pdomain-ui's `<AppShell>`:

- Each pd-* app ships its own `pd_<app>/pd-suite.json` fragment in its wheel
  (name, icon, default port, package). `register_self()` reads the calling
  app's fragment via `importlib.resources` and writes to
  `~/.local/share/pd-suite/installed.toml`. No baseline catalog exists in
  pdomain-ui — `installed.toml` IS the catalog. Decided #180 (2026-05-17).
- Each app's user config has an opt-in "siblings" section: enabled sibling
  URLs.
- If no siblings are configured or installed, the launcher hides itself.
  Single-app users never see it.
- Optional convenience: if a sibling app's binary is detected locally and not
  yet running, the current app's backend spawns it (uvicorn subprocess) and
  links once `/healthz` returns 200. Opt-in per sibling.

**What we deliberately do not introduce:**

- No host-process model.
- No cross-app auth.
- No shared database.
- Apps remain fully independent products that happen to share libraries.

---

## 3. Repo & release layout, install + discovery model

### New repos

| Repo | Lang | Role | Released to |
|------|------|------|-------------|
| `pdomain-ui` | TS/React | Shared frontend lib | `pdomain-index-npm` |
| `pdomain-ops` | Python | Standardized ops, suite plumbing, GPU adapters | `pdomain-index-pip` |
| `pdomain-index-npm` | meta | Self-hosted Verdaccio-style npm index on GitHub Pages | self-hosted |

### Existing repo rename (chore, not blocked by this design)

`pd-index` → `pdomain-index-pip`. Asymmetry with `pdomain-index-npm` will be confusing
otherwise. Update CLAUDE.md, agent prompts, `.gitignore` workspace anchors,
and every pd-* `Makefile` / `pyproject.toml` index URL.

### Install model

Every end-user app ships as a single wheel that bundles its React SPA assets
inside the package data. Users run:

```
uv tool install pdomain-ocr-simple-gui
uv tool install pdomain-ocr-labeler-spa
uv tool install pdomain-prep-for-pgdp
```

Each shim is a real CLI binary: `pdomain-ocr-simple-gui --port 8004` starts the
FastAPI server, which serves the bundled SPA at `/`.

### Workspace dev loop

Optional `pnpm-workspace.yaml` at `/workspaces/ocr-container/` symlinks
`pdomain-ui/` into each app's `frontend/` when present. CI and standalone clones
install from `pdomain-index-npm` normally.

### Sibling discovery (solves "browser can't launch apps")

Shared on-disk registry at `~/.local/share/pd-suite/installed.toml`
(cross-platform via `platformdirs`):

```toml
[apps.pdomain-ocr-labeler-spa]
package = "pdomain-ocr-labeler-spa"
version = "0.4.2"
binary  = "/home/user/.local/bin/pdomain-ocr-labeler-spa"
default_port = 8001
icon = "labeler"
display_name = "OCR Labeler"
```

Lifecycle:

1. **Self-registration on first run.** Each pd-* SPA writes its own block via
   `pd_ocr_ops.suite.register_self()`. Refreshes version when entry already
   exists at the same path. User is never prompted.
2. **Manual deregister.** `uv tool uninstall` does not trigger Python hooks,
   so each app ships a `--unregister-suite` subcommand. Stale entries are
   pruned at launcher-read time if the binary path no longer exists.
3. **Launcher reads + decides.** AppShell calls `GET /api/suite/installed`
   on its own backend; the response renders tiles for installed siblings.
4. **Spawn on click.** User clicks "Open Labeler". Frontend POSTs
   `/api/suite/launch?app=pdomain-ocr-labeler-spa` to its own backend. Backend
   looks up the sibling's `binary` and `default_port`, checks if anything is
   listening, otherwise spawns `binary --port N`, polls `/healthz`, returns
   `{ url, spawned }`. Frontend opens the URL in a new tab.

This keeps the browser out of process-launch — the user's own backend is the
trusted local agent that exec's siblings.

### App icons and desktop launchers

Every pd-* SPA ships `<repo>/icons/` (1024/512/256/128/64/32/16 PNG +
`icon.ico` + `icon.icns`). Stub artwork is acceptable for first releases.

`pdomain-ops` ships `pd_ocr_ops.suite.desktop.install_shortcut(app_meta)`.
First release raises `NotImplementedError` with a clear "not yet on this
platform" message; each app already wires `--install-desktop-shortcut` and
`--remove-desktop-shortcut` CLI flags so the surface is ready when the
platform code lands. Real implementations (`.desktop` for Linux, `.app` for
macOS, `.lnk` for Windows) are deferred.

The same icons feed: (a) each app's own `pd-suite.json` fragment (referenced
by `icon: <name>`), (b) the AppShell launcher tile (served by FastAPI at
`/api/icons/<size>` from the calling app's `icons/` directory), (c) the
future native desktop entry.

See also: [docs/runbooks/desktop-launcher-integration.md](../reminders/desktop-launcher-integration.md).

---

## 4. Component surface inside `pdomain-ui`

Single npm package `@concavetrillion/pdomain-ui`, ESM, tree-shakeable. Internal
module organization (each import path is stable; subpath imports work):

```
@concavetrillion/pdomain-ui
+- /canvas          PageImageCanvas (slot-based Konva stage)
|                   BBoxLayer, WordHitLayer, MarqueeSelectLayer,
|                   RotateTransformerLayer, EraseOverlayLayer,
|                   CharRangeLayer (slot helpers for common overlays)
|                   useCanvasCoords(), useViewport(), useCanvasSelection()
|
+- /worklist        WordList (virtualized, slot-based row renderer)
|                   LineList, PageList (same pattern, different shape)
|                   StatusPip, ConfidenceBar, MatchStatusChip
|                   useWorklistFilter(), useWorklistSort()
|
+- /shell           AppShell (header + rail + drawer + main + right panel grid)
|                   LauncherSlot, LauncherTile
|                   Breadcrumb, TopNav, Drawer, Rail, RightPanel
|                   useSuiteSiblings() reads /api/suite/installed
|
+- /primitives      Thin React wrappers that apply design-system CSS classes
|                   (.btn, .chip, .pip, .input, .key, .tab, .accordion).
|                   Radix is layered in ONLY for behavior-heavy components:
|                     Dialog, AlertDialog, Popover, Tooltip, DropdownMenu,
|                     Select, Tabs, ToggleGroup.
|                   Non-Radix primitives (just CSS + plain HTML):
|                     Button, Input, Textarea, Badge, Chip, StatusPip,
|                     KeyCap, Card, Separator, Progress, Accordion (native
|                     <details>/<summary>).
|                   No CVA — variants are CSS class modifiers (.btn.primary,
|                   .btn.sm, .chip.tristate, etc.).
|
+- /icons           Curated icon module. Re-exports a vetted subset of
|                   lucide-react (~30 icons: ChevronDown, Close, Search,
|                   Settings, Save, FolderOpen, Undo, Redo, Plus, Minus, Eye,
|                   EyeOff, Delete, Copy, Download, Upload, RotateCw, RotateCcw,
|                   ZoomIn, ZoomOut, Check, Info, AlertTriangle, PanelLeft,
|                   PanelRight, LayoutGrid, ...). Plus bespoke OCR-domain SVGs:
|                     LayerBlock, LayerPara, LayerLine, LayerWord,
|                     ModeSelect, ModeRebox, ModeErase, ModeCharFixer,
|                     MatchStatusExact, MatchStatusFuzzy, MatchStatusMismatch.
|                   Apps import ONLY from this module — never from lucide-react
|                   directly. Phase 1 ships placeholder stub SVGs for the
|                   bespoke glyphs; finished art lands later without API change.
|
+- /types           Word, Line, Page, BBox, CharBBox,
|                   ReviewMetadata, GTMatchMetadata,
|                   SuiteApp, InstalledApp, UIPrefs
|                   WordLike, LineLike, PageLike (Pick<> derivations)
|
+- /stores          createSelectionStore(), createViewportStore(),
|                   createWorklistStore(), createUIPrefsStore()
|                   (Zustand factory functions; apps instantiate per page/project)
|
+- /theme           tokens.css + primitives.css — canonical copies of the
|                   workspace docs/design-system/ files. pdomain-ui owns the runtime
|                   source-of-truth; a sync script in pdomain-ui's release updates
|                   docs/design-system/ snapshots. Apps import these two files
|                   at root layout. Includes the dual :root (dark default) and
|                   [data-theme="light"] token blocks.
|
+- /testids         data-testid catalog (constants object); versioned and
                    documented for Playwright drivers across the suite
```

### Key API conventions

1. **Slot-based, not prop-soup.** Anything that varies per-app is a
   render-prop slot (`overlay`, `tool`, `row`, `header`, `footer`). pdomain-ui owns
   layout, performance, hit-testing, virtualization — apps own what's drawn.
2. **Structural types.** All input types are `*Like` interfaces with only the
   fields pdomain-ui touches. Apps' OpenAPI types satisfy them by structural
   typing; app-specific fields ride along untouched.
3. **Stores are factories, not singletons.** `createSelectionStore()` returns
   a fresh Zustand store. Each AppShell instantiates its own; pdomain-ui never
   imports a top-level singleton (avoids HMR + multi-instance pain).
4. **Testids are constants.** `import { TESTIDS } from
   '@concavetrillion/pdomain-ui/testids'` -> `TESTIDS.canvas.bboxOverlay`. The
   Playwright drivers in the labeler-driver agent rely on this contract being
   stable and importable.
5. **CSS-var theming via the design-system tokens.** All colors, surfaces,
   borders, ink, spacing, radii, type come from `tokens.css` custom
   properties (`--bg-surface`, `--ink-1`, `--accent`, `--exact`, `--word`,
   etc.). pdomain-ui never hard-codes hex values. Tailwind is allowed *only* for
   layout utilities (`flex`, `gap-*`, `grid`, `px-*`, `min-h-*`) — never for
   color or theming. Component variants live as CSS class modifiers in
   `primitives.css`, not as CVA in JS.
6. **Standard contract callbacks (revised "no backend coupling").** pdomain-ui
   never imports any specific app's API client, but it ships standard
   contract callbacks (load, persist, suite-list, prefs) the app wires at
   root. The contract URLs (`/api/suite/prefs`, `/api/suite/installed`,
   `/api/suite/launch`, etc.) are conventions in pdomain-ops route helpers —
   every pd-* app mounts them by calling
   `pd_ocr_ops.suite.mount_routes(app)`.

### What pdomain-ui deliberately does not include

- Page-OCR mutation glue (that's `pdomain-ops` + each app's routes).
- Auth, session, routing — apps own these.
- Any single-app concept (labeler's char-fixer dialog, pgdp's package
  builder).

### Cross-cutting concern: shared UI prefs

UI prefs split into two storage scopes (decided #184, 2026-05-17):

**Shared cross-app prefs** at `~/.local/share/pd-suite/ui-prefs.json` —
genuinely cross-app UI tokens that should follow the user everywhere:

```json
{
  "common": {
    "theme": "dark",
    "density": "compact",
    "accent": "#d6925a",
    "font_size_base": 12,
    "layer_colors": {
      "word":  "#6e9cdf",
      "line":  "#d088a8",
      "para":  "#7fb56a",
      "block": "#a89074"
    }
  }
}
```

**Per-app prefs** at `~/.local/share/pd-suite/<app_id>/app_prefs.json` —
app-specific prefs and domain data. Examples:

```json
// ~/.local/share/pd-suite/pdomain-ocr-labeler-spa/app_prefs.json
{ "show_match_diff_default": "fuzzy-and-mismatch" }

// ~/.local/share/pd-suite/pdomain-ocr-simple-gui/app_prefs.json
{ "default_engine": "doctr",
  "recent_projects": [ ... ] }
```

Per-app isolation by default — no shared filelock contention on a
project-open in simple-gui, and one app's domain data doesn't pollute
another app's prefs read. Hosted-mode adapters (`PerUserDBPrefs`,
`RemoteHTTPPrefs`) swap the storage backend without changing the per-app
boundary.

`pdomain-ops.suite.prefs` mounts the routes
(`GET /api/suite/prefs`, `PUT /api/suite/prefs/common`,
`PUT /api/suite/prefs/apps/<app>`) and protects writes with `filelock`
advisory locks (one lock per file — per-app writes don't contend with
shared `common` writes or with sibling apps).

pdomain-ui's `createUIPrefsStore({ load, persistCommon, persistApp })` takes the
fetch callbacks at root; pdomain-ui ships `<UIPrefsProvider>` + hooks
(`useTheme`, `useDensity`, `useLayerColor`). Live cross-tab sync (SSE
channel) is deferred to Phase 2 — reload picks up sibling-app changes for
Phase 1.

---

## 5. Type contract & `pdomain-book-tools` alignment

**Source of truth: `pdomain-book-tools` Python data models.**

**Current state.** pdomain-book-tools' `Word` / `Block` / `Page` / `Character` are stdlib `@dataclass`es, not Pydantic models. The plan `2026-05-16-pdomain-book-tools-review-metadata-and-schemas-emit` adds `pydantic>=2.0` as a direct dep solely to use `pydantic.TypeAdapter` for JSON-Schema emission against the existing dataclasses — no model rewrite. A full migration to native Pydantic is **not in Phase 1** (see "Deferred type-system migration" below).

**Canonical model shape** (post-promotion target; this is what `pdomain-ui` codegen should produce TS for):

```python
class BBox(BaseModel):
    x: float; y: float; w: float; h: float

class CharBBox(BaseModel):  # already specced at commit f11924d
    bbox: BBox
    char: str
    is_split_glyph: bool = False

class ReviewMetadata(BaseModel):
    validated: bool = False
    reviewer_note: str | None = None
    flagged_for_attention: bool = False
    # Future: extends to list[ReviewPass] for multi-round DP-style review.

class GTMatchMetadata(BaseModel):
    """Per-Word ground-truth state. Replaces top-level Word.ground_truth_*
    fields on the post-promotion surface (see Deferred plan #1 below)."""
    gt_text: str | None = None
    gt_bounding_box: BBox | None = None
    match_status: Literal["exact","fuzzy","mismatch","none"] = "none"
    match_score: float | None = None
    align_offset: int | None = None
    match_keys: dict[str, Any] = {}

class OCRProvenance(BaseModel):
    """How this Page's OCR output came to be. Cluster of fields previously
    top-level on Page (see Deferred plan #2 below)."""
    original_ocr_tool_text: str | None = None
    source: str | None = None                # tool identifier (doctr/tesseract/...)
    ocr_failed: bool = False
    live_ocr:  dict[str, Any] | None = None  # last live-OCR run details
    saved_ocr: dict[str, Any] | None = None  # snapshot from sidecar load
    saved:     dict[str, Any] | None = None  # session-save details

class Word(BaseModel):
    bounding_box: BBox
    text: str
    ocr_confidence: float | None = None
    chars:    list[CharBBox]    | None = None
    review:   ReviewMetadata    | None = None
    matching: GTMatchMetadata   | None = None
    # Domain labels — kept top-level
    word_labels:     list[str] = []
    word_components: list[str] = []
    # Typography — kept top-level
    text_style_labels:       list[str] = []
    text_style_label_scopes: dict[str, str] = {}
    baseline: dict[str, float | str] | None = None

class BlockCategory(StrEnum):
    LINE        = "line"
    PARAGRAPH   = "paragraph"
    FIGURE      = "figure"
    CAPTION     = "caption"        # NEW — proofable text on plates / under figures
    PAGE_NUMBER = "page_number"
    HEADER      = "header"
    FOOTER      = "footer"
    FOOTNOTE    = "footnote"
    # (existing categories kept; only CAPTION is newly required)

class Block(BaseModel):
    """Polymorphic container. Lines, paragraphs, figures, captions, etc.
    are all Blocks distinguished by `category`. There is NO separate
    `Line` class — `Block(category=LINE)` is a line, same as
    `Block(category=PARAGRAPH)` is a paragraph."""
    category: BlockCategory
    bounding_box: BBox
    children: list["Block"] | list[Word] = []   # heterogeneous; type depends on category
    review: ReviewMetadata | None = None

class PageCategory(StrEnum):
    COVER        = "cover"
    TITLE        = "title"
    FRONTMATTER  = "frontmatter"
    TOC          = "toc"
    BODY         = "body"
    PLATE        = "plate"          # full-page illustration; captions are proofable Block(category=CAPTION) children
    FOOTNOTES    = "footnotes"
    INDEX        = "index"
    BACKMATTER   = "backmatter"
    BLANK        = "blank"
    OTHER        = "other"

class SubpagePosition(StrEnum):
    LEFT = "left"; RIGHT = "right"
    TOP  = "top";  BOTTOM = "bottom"
    CENTER = "center"
    PANEL  = "panel"   # ordinal panel, no geometric meaning
    NAMED  = "named"   # use subpage_subname

class Page(BaseModel):
    # Identity
    page_index: int                          # ordinal in volume; shared between parent and its subpages
    name: str | None = None                  # human/logical name ("Cover", "TOC1", "p042")
    image_url: str | None = None             # scan URL or sidecar reference (renamed from image_path)
    width: int                               # image intrinsic width in px
    height: int                              # image intrinsic height in px
    rotation_applied: int = 0                # active render rotation 0/90/180/270 (canonical, NOT provenance)

    # Categorization
    category:         PageCategory | None = None
    category_subtype: str | None = None      # free-text refinement (e.g., "half-title")

    # Structure
    bounding_box: BBox | None = None         # active text region within the image
    blocks:       list[Block] = []           # polymorphic; lines, paragraphs, figures, captions, ...
    page_labels:  list[str]   = []

    # Subpage relationship — None on top-level pages
    parent_page_index: int | None = None
    subpage_children:  list[int] | None = None      # bidirectional: parent lists its children's page_indexes
    subpage_position:  SubpagePosition | None = None
    subpage_subname:   str | None = None             # required when subpage_position=NAMED
    subpage_index:     int | None = None             # 0-based reading order within parent
    parent_bbox:       BBox | None = None            # this subpage's rect in parent's image coords (for recomposition)

    # Clustered metadata
    provenance: OCRProvenance | None = None
    review:     ReviewMetadata | None = None
```

Each app's FastAPI backend reuses these models. OpenAPI emission is automatic via Pydantic 2's `TypeAdapter` (which works on the current `@dataclass`-based models too); `make openapi-export` produces the same TS shape in every app.

### Deferred type-system migration

The canonical shape above is the **target**, not what `pdomain-book-tools` ships today. Each gap below is its own future plan, scheduled independently:

1. **`Word.matching: GTMatchMetadata`** — fold the existing top-level `Word.ground_truth_text` / `Word.ground_truth_bounding_box` / `Word.ground_truth_match_keys` into `matching`. ~155 call-site updates in `pdomain-ocr-labeler-spa`.
2. **`Page.provenance: OCRProvenance`** — fold the existing top-level `Page.original_ocr_tool_text` / `Page.source` / `Page.ocr_failed` / `Page.provenance_{live,saved,saved_ocr}_ocr` into `provenance`. ~49 call-site updates in `pdomain-ocr-labeler-spa`.
3. **`Page.image_path` → `Page.image_url` rename** — the only canonical *rename* (others rejected as taste-only; see "Rejected renames" below). Affects ~59 call sites across `pdomain-ocr-labeler-spa` + `pdomain-prep-for-pgdp`. Pydantic-alias migration once the dataclass→Pydantic conversion has happened.
4. **`rotation_applied` documented as canonical** (no code change; it's already a top-level Page field). Spec promotion only.
5. **`page_category` + `category_subtype` + subpage fields + `parent_bbox` + `subpage_children`** — new fields, all default `None`/`[]`, no migration impact on existing serialized data.
6. **`BlockCategory.CAPTION`** — new enum value; only producers (DocTR/Tesseract pipelines + pdomain-ocr-synth recipes) need to start emitting it for plate captions to be recognized.
7. **Native-Pydantic migration of Word/Block/Page/Character** — the largest item. `TypeAdapter` already gives codegen consumers what they need against the existing `@dataclass`es, so this migration is about Python-side ergonomics (field aliases, validators, `model_dump(by_alias=...)`, etc.), not about unblocking pdomain-ui. Treat as optional / lowest priority.

### Rejected renames

The following candidate renames from earlier drafts of this spec are **rejected** as taste-only changes that don't justify the call-site churn:

| Earlier draft | Current canonical | Why rejected |
|---|---|---|
| `Word.bbox` | `Word.bounding_box` | Just shorter; ~66 active call sites. |
| `Word.confidence` | `Word.ocr_confidence` | Just shorter; distinguishes from review_confidence later. |
| `Page.natural_width` / `natural_height` | `Page.width` / `Page.height` | Server-side model has no rendering distinction to clarify. pdomain-ui's canvas can use the HTMLImageElement's own `naturalWidth`/`naturalHeight` if needed. |
| `class Line(BaseModel)` | `Block(category=LINE)` | A line is a kind of Block (same as paragraph). Polymorphism via `category` is the existing pdomain-book-tools design. |
| `class CharBBox(BaseModel)` | (kept; replaces `Character`) | The one new type-name in this section; `Character` → `CharBBox` is a focused rename because the new class adds `is_split_glyph` and ties name to purpose (char + bbox). |
| `Page.id: str` | `Page.page_index: int` + `Page.name: str?` + `Page.image_url: str?` | A single synthetic `id` collapses three meaningful fields (volume ordinal / human name / scan source). PGDP round-trip needs all three. |

### Vestigial fields dropped

- `Page.unmatched_ground_truth_lines` — 0 references in any active consumer. Drop on a future cleanup plan; no migration plan needed.

### Codegen pipeline (zero hand-roll of foundation types)

**Phase 1 hard requirement:** `pdomain-book-tools` ships `python -m pd_book_tools.schemas.emit` — a CLI that dumps every public domain model as JSON Schema using `pydantic.TypeAdapter`. Same for `pd_ocr_ops.suite.types`. (Works on stdlib `@dataclass`es too; no native-Pydantic migration required.)

`pdomain-ui` package scripts:

```
"codegen:fetch":  install pinned pdomain-book-tools + pdomain-ops wheels into .codegen/venv
"codegen:emit":   run schema emitters -> .codegen/{book-tools,ocr-ops}.schema.json
"codegen:tsgen":  openapi-typescript -> src/types/generated/{book-tools,suite}.ts
"codegen":        runs all three; output is committed to git
"codegen:check":  re-runs codegen, fails if output differs (CI gate)
```

`src/types/generated/` is **committed** so diffs show up in PRs. PRs that bump pdomain-book-tools must include regenerated types or CI fails.

### `*Like` reductions become one-line derivations

```ts
// src/types/index.ts
export * from './generated/book-tools';
export * from './generated/suite';

import type { Word, Block, Page } from './generated/book-tools';

export type WordLike = Pick<Word,
    'bounding_box' | 'text' | 'ocr_confidence'
  | 'chars' | 'review' | 'matching'
  | 'word_labels' | 'text_style_labels'
>;

export type BlockLike = Pick<Block,
    'category' | 'bounding_box' | 'children' | 'review'
>;

// Lines are blocks: filter by `block.category === 'line'`.
// Same for paragraphs, captions, figures, etc. No separate LineLike.

export type PageLike = Pick<Page,
    'page_index' | 'name' | 'image_url' | 'width' | 'height'
  | 'category' | 'blocks' | 'review'
  | 'parent_page_index' | 'subpage_index' | 'subpage_position'
>;
```

If `pdomain-book-tools` renames `Word.text` -> `Word.value`, `WordLike`'s Pick fails at compile time — pdomain-ui won't release without addressing it.

### Naming convention

Types are `Word`, `Block`, `Page` everywhere — no app prefixes. **There is no separate `Line` class.** A line is `Block(category=LINE)`, a paragraph is `Block(category=PARAGRAPH)`, a plate caption is `Block(category=CAPTION)`. Each app's `frontend/src/api/types.gen.ts` is generated from its own `/openapi.json`; both apps' types are structurally identical because both serialize the same models. Assignment between app `Word` and pdomain-ui `Word` (or `WordLike`) is free.

---

## 6. Slot & render-prop API conventions

### `<PageImageCanvas>` — the shared canvas

```ts
type SlotRenderProps = {
  coords: CoordContext;
  selection: SelectionState;
  hover: WordLike | null;
  zoom: number;
  pan: { x: number; y: number };
};

type WordSlotProps = SlotRenderProps & { word: WordLike; isSelected: boolean };

type CanvasProps<TWord extends WordLike = WordLike, TPage extends PageLike = PageLike> = {
  page: TPage;
  words: TWord[];
  selection: SelectionState;
  onSelectionChange: (s: SelectionState) => void;
  initialZoom?: number;
  fitOnMount?: boolean;

  children?: {
    underlay?:  (p: SlotRenderProps) => ReactNode;
    overlay?:   (p: WordSlotProps)   => ReactNode;
    selection?: (p: SlotRenderProps) => ReactNode;
    tool?:      (p: SlotRenderProps) => ReactNode;
    hud?:       (p: SlotRenderProps) => ReactNode;
  };
};
```

Layer order is fixed by pdomain-ui:
`image -> underlay -> overlay -> selection -> tool -> hud`.

### `<WordList>` — the shared worklist

```ts
type WordRowProps<TWord> = {
  word: TWord;
  index: number;
  isActive: boolean;
  isSelected: boolean;
  setActive: () => void;
  toggleSelect: () => void;
};

type WordListProps<TWord extends WordLike = WordLike> = {
  words: TWord[];
  activeWordId: string | null;
  selectedWordIds: ReadonlySet<string>;
  onActiveChange: (id: string | null) => void;
  onSelectionChange: (ids: ReadonlySet<string>) => void;
  filter?: (w: TWord) => boolean;
  sortKey?: (w: TWord) => string | number;
  reverse?: boolean;
  renderRow: (props: WordRowProps<TWord>) => ReactNode;
  header?: ReactNode;
  footer?: ReactNode;
  emptyState?: ReactNode;
};
```

pdomain-ui handles virtualization, scroll-to-active, multi-select gestures
(shift-click range, ctrl/cmd-click toggle), keyboard navigation. The app's
`renderRow` decides whether to show diff, match status, confidence bar, etc.

### `<AppShell>` — the host frame

```ts
type AppShellProps = {
  appId: string;
  appDisplayName: string;
  appIconUrl: string;
  header?: ReactNode;
  rail?: ReactNode;
  drawer?: ReactNode;
  main: ReactNode;
  rightPanel?: ReactNode;
  launcherSlot?: 'header' | 'rail' | 'off';
  uiPrefsConfig: UIPrefsConfig;
  deployMode?: 'local' | 'hosted';    // default 'local'; gates local-only UX
};
```

### Hook surface

```ts
useCanvasCoords(): CoordContext

useSelection(): SelectionState
useViewport():  ViewportState
useWorklist():  WorklistState
useUIPrefs():   UIPrefs

useSuiteSiblings(): {
  siblings: InstalledApp[];
  launch: (id: string) => Promise<LaunchResult>;
  loading: boolean;
};

type LaunchResult =
  | { kind: 'opened'; url: string }
  | { kind: 'requires-host-config'; siblingId: string };

useLayerColor(layer: 'block'|'para'|'line'|'word'): string
useStatusColor(status: 'exact'|'fuzzy'|'mismatch'|'ocr'|'gt'): string
useAccentColor(): { fg: string; bg: string }  // var(--accent), var(--accent-ink)
useTheme(): 'light' | 'dark'
useDensity(): 'compact' | 'normal' | 'comfortable'

// GPU dispatch
useStageCall(stageId, pageId, params): {
  status, result, isWarming, retryAt
};   // handles 503 Retry-After backoff transparently

useLongJob(jobId): {
  status, progress, events, cancel
};   // SSE in hosted mode; polling fallback in local mode
```

---

## 7. Phase staging

### Phase 1 — foundation lift (parallel tracks)

| # | Track | Repo | Blocks |
|---|---|---|---|
| 1.1 | Add `ReviewMetadata`, `GTMatchMetadata` sub-objects; ship `python -m pd_book_tools.schemas.emit` CLI | `pdomain-book-tools` | pdomain-ui codegen, pdomain-ops |
| 1.2 | Rename `pd-index` -> `pdomain-index-pip`; update CLAUDE.md, agent prompts, every `pyproject.toml` index URL, workspace `.gitignore` | `pd-index`, all pd-* | independent chore |
| 1.3 | NEW repo `pdomain-ops`: suite types, `installed.toml` registry, `prefs.read/write`, `mount_routes()`, `desktop.install_shortcut()` stub, `sibling_spawn.launch()` helper, `schemas.emit` CLI, two GPU adapter protocols (`StageDispatcher`, `LongJobRunner`) with local-mode adapters + SQLite jobs table, `pick_device()` helper | `pdomain-ops` | apps' suite integration |
| 1.4 | NEW repo `pdomain-index-npm`: Verdaccio-style index hosted on GitHub Pages, publish script | `pdomain-index-npm` | pdomain-ui release |
| 1.5 | NEW repo `pdomain-ui`: scaffold, codegen, first components (`<PageImageCanvas>`, `<WordList>`, `<AppShell>`) extracted from labeler-spa as port-not-copy, primitives folder = thin React wrappers around the design-system CSS classes (Radix layered in only for behavior-heavy components per §4), copy `tokens.css` + `primitives.css` from workspace `docs/design-system/` into `pdomain-ui/theme/` as canonical runtime home + sync script back to docs/design-system/, ship `pdomain-ui/icons` (curated lucide-react re-exports + bespoke OCR-domain stub SVGs), Storybook for component dev loop, publish `0.1.0-alpha` to pdomain-index-npm | `pdomain-ui` | Phase 2 |
| 1.6 | NEW agent definitions: `.claude/agents/pdomain-ui.md`, `.claude/agents/pdomain-ui-docs.md`, `.claude/agents/pdomain-ops.md`, `.claude/agents/pdomain-ops-docs.md`. Update workspace CLAUDE.md routing table | `ocr-container` | agent routing for new repos |

Tracks 1.1 / 1.2 / 1.3 / 1.4 / 1.6 are mostly independent. Track 1.5 needs
1.1's schema emitter for codegen; scaffold/Storybook/component porting can
start immediately.

### Phase 1.7 — interim (between Phase 1 and Phase 2)

(Renumbered from a draft "Phase 1.5" that collided with the table row label.)

Migrate pgdp-prep's existing `STAGE_IMPL` registry + Modal/shared-container
GPU adapters into pdomain-ops as the canonical home. pgdp-prep imports them
from pdomain-ops afterward. Rename env var `PGDP_GPU_BACKEND` ->
`PD_GPU_BACKEND` (deprecation alias preserves backwards compat).

### Phase 2 — canary migration (labeler-spa first, pgdp-prep second)

| # | Task | Repo |
|---|---|---|
| 2.1 | `pdomain-ui@0.1.0-alpha` -> `^0.1.0` in `pdomain-ocr-labeler-spa/frontend/package.json` | `pdomain-ocr-labeler-spa` |
| 2.2 | Replace `PageImageCanvas.tsx` internals with pdomain-ui's; move labeler-specific layer code into slot fills | `pdomain-ocr-labeler-spa` |
| 2.3 | Replace `Worklist.tsx` internals with `<WordList>`; `LineCard` becomes the row renderer | `pdomain-ocr-labeler-spa` |
| 2.4 | Replace `StudioShell` with pdomain-ui `<AppShell>`; wire UIPrefs config; mount pdomain-ops routes | `pdomain-ocr-labeler-spa` |
| 2.5 | Retire labeler-spa's custom reactive stores; codemod call sites to Zustand factories | `pdomain-ocr-labeler-spa` |
| 2.5b | Styling normalization: remove `class-variance-authority` dep, convert remaining labeler-spa-local component variants from CVA to design-system CSS class modifiers; remove direct `lucide-react` imports, switch to `@concavetrillion/pdomain-ui/icons`; restrict Tailwind to layout utilities only (no color/theme utilities) | `pdomain-ocr-labeler-spa` |
| 2.6 | Full Playwright driver run via `pd-ocr-labeler-driver` agent — every test must pass without contract changes | `pdomain-ocr-labeler-spa` |
| 2.7 | Same migration on `pdomain-prep-for-pgdp` (canvas/worklist/shell/Zustand + styling normalization 2.5b + Playwright driver pass); pdomain-ui releases as `0.2.0` with any lessons baked in | `pdomain-prep-for-pgdp` |

Labeler-spa migrates first because its canvas is the most advanced — pdomain-ui's
`<PageImageCanvas>` is mostly its code restructured under slots, so the
migration is mostly re-import + restructure slot fills, not new design. The
existing Playwright driver contract gives a strong regression net.

### Phase 3 — greenfield new consumers

| # | New repo | Notes |
|---|---|---|
| 3.1 | `pdomain-ocr-trainer-spa` | Replaces NiceGUI trainer; structurally modeled on pgdp-prep + labeler-spa canonical pattern. Uses pdomain-ui from start. Already named in workspace `.gitignore` |
| 3.2 | `pdomain-ocr-simple-gui` | Smallest pdomain-ui consumer; reference implementation; spec in [docs/runbooks/spec-pdomain-ocr-simple-gui.md](../reminders/spec-pdomain-ocr-simple-gui.md) |
| 3.3 | `pd-proofreader` | Far future. Multi-pass review model lands here — `ReviewMetadata` evolves to `list[ReviewPass]` in pdomain-book-tools to support DP-style rounds (P1/P2/P3/F1/F2) |

### Phase 4 — optional shell features

| # | Feature | Where |
|---|---|---|
| 4.1 | Live cross-tab UI prefs sync via SSE channel | pdomain-ops + pdomain-ui store subscriber |
| 4.2 | Real desktop launcher platforms — Linux `.desktop`, macOS `.app`, Windows `.lnk` | pdomain-ops `pd_ocr_ops.suite.desktop` |
| 4.3 | Optional embedded-shell mode — one app iframes/route-mounts others into a single window | new `pd-shell` repo or pdomain-ui module; build only if demand justifies |

---

## 8. Hosted / web-mode considerations

**Principle:** pdomain-ui (frontend) is deploy-mode-agnostic — it always talks to
its own backend's `/api/suite/*` endpoints. The mode-switching happens
entirely inside `pdomain-ops` via **adapters**. Each app's startup picks an
adapter pack based on environment.

### Adapter seams pdomain-ops defines from day one

Even if Phase 1 only implements the local-mode adapter for each, the seam
exists so hosted-mode adapters drop in later without changing app code or
pdomain-ui.

| Concern | Local-mode adapter (Phase 1) | Hosted-mode adapter (later) |
|---|---|---|
| **Suite registry** | `LocalTomlSuiteRegistry` reads `~/.local/share/pd-suite/installed.toml` | `EnvSuiteRegistry` reads sibling URLs from env vars; `DBSuiteRegistry` for per-tenant SaaS |
| **UI prefs** | `LocalFilePrefs` (JSON on disk) | `PerUserDBPrefs` keyed by authenticated user id |
| **Sibling launch** | `LocalSpawnLauncher` spawns uvicorn subprocess | `StaticURLLauncher` returns configured URL; `K8sScaleLauncher` cold-starts a deployment from 0 -> 1 |
| **Auth** | `NoAuthAdapter` (single-user local) | `ApiKeyAuth`, `JWTAuth`, `OIDCAuth` (already designed in pgdp-prep) |
| **Storage** (sidecar JSON IO + project artifacts) | `LocalFsStorage` | `S3Storage`, `GCSStorage` (already designed in pgdp-prep) |
| **User identity** | `SingleUser` (constant identity) | resolved from `AuthAdapter` |
| **Desktop launcher CLI flags** | `--install-desktop-shortcut` works | hidden in hosted mode |

### Suite-adapter wiring

```python
# pd_ocr_ops.suite

class SuiteAdapters(BaseModel):
    registry: SuiteRegistryAdapter
    prefs:    PrefsAdapter
    launcher: SiblingLaunchAdapter
    auth:     AuthAdapter
    storage:  StorageAdapter

    @classmethod
    def local(cls) -> "SuiteAdapters": ...      # default — Phase 1
    @classmethod
    def from_env(cls) -> "SuiteAdapters": ...   # reads PD_SUITE_MODE etc.

def mount_routes(app: FastAPI, adapters: SuiteAdapters | None = None) -> None: ...
```

Apps pick their adapter at startup:

```python
adapters = SuiteAdapters.from_env() if os.getenv("PD_SUITE_MODE") == "hosted" \
           else SuiteAdapters.local()
pd_ocr_ops.suite.mount_routes(app, adapters)
```

### GPU dispatch (folds prior pgdp-prep + trainer design)

Two adapter protocols, because short stage calls and long training runs have
very different shapes:

| Concern | Phase-1 local-mode adapter | Hosted / managed adapters |
|---|---|---|
| **Short-task stage dispatch** (per-page OCR, char-bbox extraction, layout — seconds) | `LocalStageDispatcher` calls in-process; `pick_device()` picks `local` / `mps` / `cpu` | `ModalStageDispatcher` with 5-min flush-window batching (mirrors pgdp-prep `specs/04-gpu-acceleration.md:327`); `SharedContainerStageDispatcher` POSTing to a sibling GPU pod. Frontend handles `503 Retry-After` |
| **Long-task job dispatch** (training runs, large synth batches — minutes to hours) | `LocalLongJobRunner` spawns subprocess + writes status to `~/.local/share/pd-suite/jobs.db` SQLite the frontend polls | `ModalLongJobRunner` invokes dedicated long-timeout Modal app per trainer's `ROADMAP.md:363-376` design |

```python
# pd_ocr_ops.gpu

class StageDispatcher(Protocol):
    """Short, sync-ish GPU stage calls (OCR, layout, char-bbox).
       Mirrors pgdp-prep's existing STAGE_IMPL registry shape."""
    async def run_stage(self, stage_id: str, page_id: str, **kwargs) -> StageResult: ...

class LongJobRunner(Protocol):
    """Long-running GPU jobs (training, big synth runs).
       Jobs are persistent — survive process restarts."""
    async def submit(self, kind: str, spec: dict) -> str: ...  # returns job_id
    async def status(self, job_id: str) -> JobStatus: ...
    async def cancel(self, job_id: str) -> None: ...
    async def stream_events(self, job_id: str) -> AsyncIterator[JobEvent]: ...

def pick_device() -> Literal["local","mps","cpu","modal","shared_container"]: ...
```

**Job table — yes, but minimal:** pgdp-prep's design deliberately skipped
persistent storage; that works for stage calls (state lives in the page
artifact). It doesn't work for training runs (frontend reloads must see
"training run 3 of 5, epoch 42/100"). Phase 1 ships a tiny SQLite jobs table
inside pdomain-ops (`~/.local/share/pd-suite/jobs.db`) handled by the local
adapters. The interface is the same in hosted mode; the adapter swaps to a
real DB.

### Frontend impact (pdomain-ui)

- `<AppShell>` accepts a `deployMode: 'local' | 'hosted'` prop surfaced
  through context. Components that have local-only affordances (e.g.,
  "Install desktop shortcut" menu item, "Open sibling — will launch on your
  machine" wording) read from it and hide/rewrite as needed. Defaults to
  `'local'`.
- `useSuiteSiblings().launch(id)` returns a discriminated result:
  `{ kind: 'opened', url }` or `{ kind: 'requires-host-config', siblingId }`
  — the second variant covers hosted mode where sibling URLs are static and
  pre-configured (no spawn). `<LauncherTile>` renders both variants
  gracefully.
- `useStageCall` handles the 503/Retry-After backoff loop transparently.
- `useLongJob` subscribes to events (SSE in hosted mode; polling fallback in
  local mode).
- `<JobsDrawer>` — shared right-side drawer listing active long jobs across
  the suite. Reads from `useSuiteJobs()` which queries every installed
  sibling's `/api/jobs?status=active` and merges.

### What is explicitly NOT taken on

- Multi-tenancy / per-tenant project isolation. Each app stays
  single-user-single-process; multi-tenant adapters are a Phase 4+ separate
  redesign.
- Real-time collaboration. Hosted mode in Phase 4 is "shared deployment,
  but one user at a time per project."
- A unified hosted shell deployment. Phase 4.3 only if demand justifies.
- Persistent cross-machine queue (Redis/Celery). Local jobs table is
  single-machine; managed-mode jobs are tracked in the Modal app's own
  state. Multi-machine queue becomes a Phase 4 adapter if needed.
- Operator-style scheduling ("retry failed jobs nightly").

### Net cost of adapter seams in Phase 1

- pdomain-ops ships **interfaces** for 6 suite adapter concerns + 2 GPU
  dispatch protocols + the local-mode implementations of each. ~150 lines
  of plumbing total.
- pdomain-ui's `<AppShell>` gets a `deployMode` prop (default `'local'`) and
  `useSuiteSiblings().launch` returns a discriminated result.
- Wording and affordances that are local-only are gated on
  `deployMode === 'local'`.

If we skip these seams now, hosted mode is a real rewrite later. If we
include them, hosted mode becomes "write hosted adapter classes + deploy
script."

---

## 9. Open questions, deferred decisions, Phase-1-done criteria

### Deferred design items

| Item | Why deferred | Where it lands |
|---|---|---|
| Multi-pass review model | DP-style P1/P2/P3/F1/F2 rounds — only future proofreader needs it | proofreader spec; pdomain-book-tools schema bump |
| Backend OCR mutation primitive extraction | Labeler-spa's edit operations (rebox/charfixer/erase) -> `pd_ocr_ops.ops`; deserves its own design pass | pdomain-ops 0.2.x |
| Real desktop launcher platforms | `.desktop` / `.app` / `.lnk` writers | pdomain-ops 0.3.x |
| Cross-tab UI prefs sync | SSE channel; reload-only sync acceptable for Phase 1 | pdomain-ops 0.2.x |
| Automated TS-vs-Python schema drift CI gate | Hand-review during PRs sufficient for first months | pdomain-ui CI 0.2.x |
| Hosted-mode adapters | Phase 1 ships only interfaces + local implementations | Phase 4 |
| Unified hosted-shell deployment | Only if multiple users ask | new `pd-shell` repo, Phase 4.3 |
| Cross-app auth/session | Hosted mode brings its own adapter | Phase 4 |
| Multi-tenancy | Separate redesign | not scheduled |
| Bespoke OCR-domain icon art (LayerBlock/Para/Line/Word, ModeSelect/Rebox/Erase/CharFixer, MatchStatus*) | Phase 1 ships stub SVGs so types/exports exist; designer pass scheduled later | pdomain-ui icons review |
| Curated chrome-icon set review | Initial selection from lucide-react is provisional; later review pass may swap individual icons or expand the set | pdomain-ui icons review |

### Open questions provisionally answered

| Question | Phase-1 call | Why it might change |
|---|---|---|
| pdomain-ui packaging shape | Single package `@concavetrillion/pdomain-ui`, tree-shakeable subpath imports | Split into `@pd/canvas`, `@pd/shell`, `@pd/primitives` if bundle gets fat |
| `pd-suite.json` ownership | Per-app fragment in each wheel (#180, 2026-05-17); `installed.toml` is the catalog | Operator-managed deployment may want a central manifest URL |
| Phase 1 desktop launcher | Stub raising `NotImplementedError`, CLI flags exist | Could hide CLI flags until real impls land |
| Env var rename | `PGDP_GPU_BACKEND` -> `PD_GPU_BACKEND`, with deprecation alias | Could drop the alias and require an env change at upgrade |
| pdomain-ui state lib | Zustand | If labeler-spa migration shows Zustand is a bad fit, fallback is keeping the custom store pattern — but the suite-wide standardization argument is strong |

### Phase-1-done success criteria

Phase 1 is "ready for Phase 2 canary migration."

**`pdomain-book-tools`**
- [ ] `ReviewMetadata`, `GTMatchMetadata` Pydantic models on `Word`/`Line`/`Page` (optional, nullable, no breaking changes)
- [ ] `python -m pd_book_tools.schemas.emit` CLI dumps every public model as JSON Schema
- [ ] Released to `pdomain-index-pip` (post-rename)

**`pdomain-index-pip`** (renamed from `pd-index`)
- [ ] All 8 pd-* repos reference the new name in `pyproject.toml`, `Makefile`, CLAUDE.md, workspace `.gitignore` anchor
- [ ] Workspace CLAUDE.md routing table updated; agent prompts updated

**`pdomain-index-npm`** (new repo)
- [ ] Verdaccio-style index live on GitHub Pages
- [ ] First package (`@concavetrillion/pdomain-ui@0.1.0`) published and installable

**`pdomain-ops`** (new repo)
- [ ] Suite types (`SuiteApp`, `InstalledApp`, `UIPrefs`) with `schemas.emit` CLI
- [ ] `installed.toml` registry: register/deregister/read, with `filelock`
- [ ] `prefs.{read,write}` with `mount_routes(app)` exposing `/api/suite/prefs` + `/api/suite/installed` + `/api/suite/launch`
- [ ] `desktop.install_shortcut` stub raising `NotImplementedError`
- [ ] `sibling_spawn.launch(app_id)` works on Linux (Mac/Windows best-effort)
- [ ] Two GPU dispatch protocols (`StageDispatcher`, `LongJobRunner`) with local-mode adapters + SQLite jobs table
- [ ] `pick_device()` helper
- [ ] All adapter interfaces defined; hosted-mode adapters can be skipped
- [ ] Published to `pdomain-index-pip`

**`pdomain-ui`** (new repo)
- [ ] Codegen scripts working; `src/types/generated/` committed
- [ ] `<PageImageCanvas>` with slot map (`underlay` / `overlay` / `selection` / `tool` / `hud`)
- [ ] `<WordList>` with `renderRow` slot + virtualization + scroll-to-active + multi-select gestures
- [ ] `<AppShell>` with `launcherSlot` + `deployMode` prop + UIPrefs config wiring
- [ ] `<LauncherTile>` + `useSuiteSiblings()` hook
- [ ] Primitives folder: React wrappers around design-system CSS classes; Radix only for the behavior-heavy set listed in §4; no CVA
- [ ] `pdomain-ui/theme/` ships canonical `tokens.css` + `primitives.css` (copied from workspace `docs/design-system/`); sync script updates docs/design-system/ snapshots on release
- [ ] `pdomain-ui/icons` ships curated lucide-react re-export subset + bespoke stub SVGs (LayerBlock/Para/Line/Word, ModeSelect/Rebox/Erase/CharFixer, MatchStatusExact/Fuzzy/Mismatch)
- [ ] Zustand store factories (`createSelectionStore`, `createViewportStore`, `createWorklistStore`, `createUIPrefsStore`)
- [ ] `useStageCall` (handles 503 backoff) and `useLongJob` (SSE+polling fallback) hooks
- [ ] Storybook covers all components in both `:root` (dark) and `[data-theme="light"]` modes
- [ ] `/testids` constants exported
- [ ] `class-variance-authority` is NOT a dependency
- [ ] Tailwind config gates color/theme utilities (allowed: layout utilities only); enforced via a lint rule or Tailwind safelist
- [ ] Published to `pdomain-index-npm`

**Workspace**
- [ ] `.claude/agents/pdomain-ui.md`, `.claude/agents/pdomain-ui-docs.md`, `.claude/agents/pdomain-ops.md`, `.claude/agents/pdomain-ops-docs.md` exist
- [ ] Workspace CLAUDE.md routing table updated
- [ ] `.gitignore` anchors include `/pdomain-ui/`, `/pdomain-ops/`, `/pdomain-index-npm/`
- [ ] Optional `pnpm-workspace.yaml` at workspace root tested

**Smoke-test consumer**
- [ ] A tiny example app (initial scaffold of `pdomain-ocr-simple-gui` or a minimal Storybook+pdomain-ops integration test) renders a `<PageImageCanvas>` + `<WordList>` + launcher with one mock sibling, against pdomain-ops's local adapters. Proves the lib + ops integrate end-to-end before Phase 2 commits to migrating labeler-spa.

---

## Decision log (Q1–Q8)

For audit / future reference:

| Q | Question | Choice | Notes |
|---|---|---|---|
| 1 | End-state staging | **C — Hybrid (lib first, optional shell later)** | Each app remains independently installable in all phases |
| 2 | Where does the shared lib live | **C — Own repo + self-hosted npm registry + opt-in pnpm workspace overlay** | Mirrors pdomain-book-tools + pdomain-index-pip pattern |
| 3 | Canvas API shape | **C — Shared core + named slots / render-props** | Apps own only domain overlays; pdomain-ui owns Konva stage, pan/zoom, hit-test, perf |
| 4 | Types & data contract | **C — Minimal shared core + structural typing** (revised to: codegen from pdomain-book-tools' Pydantic, `*Like` derivations via `Pick<>`) | Zero hand-roll of foundation types |
| 5 | Review/validation field promotion | **B — Clustered sub-object** (`Word.review`, `Word.matching` parallel) | Multi-pass review deferred to proofreader |
| 6 | State management | **B — Built-in Zustand stores** | Standardizes the suite; labeler retires custom reactive stores |
| 7 | Component styling strategy | **Adopt existing `docs/design-system/`** — pdomain-ui owns `tokens.css` + `primitives.css` as runtime; drop CVA; Radix scoped to behavior-heavy components only; Tailwind for layout utilities only | Re-uses the dual-theme design language already committed to the workspace |
| 8 | Icon strategy | **Hybrid: curated lucide-react subset re-exported via `pdomain-ui/icons` + bespoke OCR-domain SVG stubs** | Apps never import lucide directly; bespoke art reviewed later |

---

## Related artifacts

- [docs/design-system/](../../design-system/) — the workspace-level visual language (tokens.css, primitives.css, ui-kit.html, DESIGN_LANGUAGE.md, README.md). Becomes pdomain-ui's runtime source-of-truth in Phase 1.5 with a sync script keeping these snapshots aligned with pdomain-ui's releases.
- [docs/runbooks/spec-pdomain-ocr-simple-gui.md](../reminders/spec-pdomain-ocr-simple-gui.md) — reminder to spec the simple OCR GUI
- [docs/runbooks/desktop-launcher-integration.md](../reminders/desktop-launcher-integration.md) — desktop launcher platform implementations (deferred from Phase 1)
- pgdp-prep `specs/04-gpu-acceleration.md` — source of the `STAGE_IMPL` + flush-window batching design we're moving into pdomain-ops
- pgdp-prep CLAUDE.md "adapter pattern (IStorage, IDatabase, IAuth, GPUBackend)" — pattern we're generalizing
- pd-ocr-trainer `docs/ROADMAP.md:363-376` — design separating training (long-timeout Modal app) from per-page stages
- pdomain-book-tools commit `f11924d` — per-character bbox extraction spec; provides `CharBBox` already
