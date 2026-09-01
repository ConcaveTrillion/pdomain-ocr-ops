# pdomain-book-tools structural analysis

Repo: `/workspaces/pdomain/pdomain-book-tools`, package `pdomain_book_tools/`.
Measured 2026-09-01. Excludes `.venv*`, `.worktrees`, `dist`, `htmlcov`,
`migration`, `typings`, `__pycache__`. `tests/` and `docs/` consulted for
context only, not counted.

Total source: 39,093 lines across 132 `.py` files (includes `_version.py`,
generated at build time, 24 lines).

## 0. Ground truth: what `import pdomain_book_tools` actually loads

Measured directly (not inferred) by importing the package and diffing
`sys.modules`:

```
torch: no        doctr: no        transformers: no    pandas: no
matplotlib: no    IPython: no      ipywidgets: no      pytesseract: no
PIL: no           cv2: YES         shapely: YES        numpy: YES
```

The root `pdomain_book_tools/__init__.py` docstring says this outright:
"Importing this package eagerly imports the OCR / layout / geometry stack
(`cv2`, `numpy`, DocTR, transformers)." That's now half wrong — DocTR and
transformers are behind lazy imports and don't load eagerly — but cv2,
numpy and shapely do, unconditionally, because the root `__init__.py`
re-exports `Page`, `Word`, `Block` (from `ocr.page`/`ocr.word`/`ocr.block`,
all cv2 at module level) and `PGDPResults` (from `pgdp.pgdp_results`, which
is itself dependency-free).

**This is the mechanism behind the stated pain.** Python always executes a
package's `__init__.py` chain on any submodule import. So
`from pdomain_book_tools.pgdp.pgdp_results import PGDPResults` — despite
`pgdp_results.py` itself importing only `json`, `pathlib`, `logging`,
`typing`, `regex` — forces `pdomain_book_tools/__init__.py` to run first,
which drags in cv2/numpy/shapely (and would drag in the full ocr engine)
before `pgdp_results` is even reached. That's exactly why
`pdomain-pgdp-api-client` reads the file by filesystem path instead of
importing it. Extracting a lightweight package only fixes this if
`pgdp_results.py` *physically moves* to a package whose `__init__.py`
chain is itself light — re-exporting it from the current root without
moving it fixes nothing.

## 1–2. Module map: line counts, ownership, heavy imports

Format: `path` (lines) — ownership. Heavy imports: `E` = module-level
(eager), `L` = lazy (inside a function/method body, executes at runtime),
`T` = TYPE_CHECKING-only (no runtime cost). Unlisted heavy libs = absent.

### `geometry/` — 1,465 lines total

| module | lines | owns | heavy imports |
|---|---|---|---|
| `point.py` | 257 | `Point` value type | shapely `E` |
| `bounding_box.py` | 879 | `BoundingBox` value type + geometry ops | shapely `E`; numpy `T`; cv2 `L` (3 call sites, drawing/crop convenience methods only, deferred to `geometry.image_ops`) |
| `image_ops.py` | 312 | cv2-backed drawing/crop free functions | cv2 `E` |
| `__init__.py` | 17 | facade re-exporting Point/BoundingBox | — |

`bounding_box.py`'s cv2 dependency is already fully lazy and optional —
it's extraction-ready as written.

### `geometry_correction/` — 1,301 lines total

Owns: pluggable page-geometry-correction pipeline (deskew, dewarp,
curvature, page-side/gutter detection) with a `registry.py` backend
selector. Not imported by any other subpackage in this repo (see §3) —
it's a leaf, self-contained feature area.

| module | lines | owns | heavy imports |
|---|---|---|---|
| `protocols.py` | 127 | backend Protocol definitions | numpy `T` |
| `regime.py` | 102 | correction-regime dataclass/logic | cv2, numpy `E` |
| `registry.py` | 108 | backend lookup/selection | (backends lazy `L`) |
| `pipeline.py` | 102 | orchestration | numpy `T` |
| `transforms.py` | 167 | coordinate transform math | cv2, numpy `E` |
| `defaults.py` | 58 | default pipeline wiring | — |
| `detectors/textline.py` | 80 | textline detection algorithm | image_processing `E` |
| `backends/deskew/{projection,sbrunner}.py` | 74+47 | deskew backends | cv2 `E`, numpy `E`/`T` |
| `backends/dewarp/{uvdoc,_uvdoc_model,textline}.py` | 63+68+102 | UVDoc ONNX dewarp | cv2 `E`, numpy `E`/`T` |
| `backends/curvature/image_based.py` | 75 | curvature estimation | cv2, numpy `E` |
| `backends/page_side/{gutter_shadow,supplied}.py` | 52+35 | page-side detection | cv2 `E` |
| `backends/__init__.py` x5 | 5 | package stubs | — |

All algorithm/runtime code; cv2+numpy throughout; no torch/doctr.

### `hf/` — 319 lines total

Owns: Hugging Face Hub download + model-path resolution. Not imported
by any other subpackage (leaf).

| module | lines | owns | heavy imports |
|---|---|---|---|
| `download.py` | 135 | `hf_hub_download` wrapper | `huggingface_hub` (not in the tracked-heavy list, but a real network/IO dep) |
| `models.py` | 137 | model registry → cache path | transformers `L` (line 118, `transformers.utils.logging`); `layout.adapters.pp_doclayout` `L` (line 92) |
| `__init__.py` | 47 | facade | — |

Runtime/IO module, not a value type.

### `image_processing/` — 5,714 lines total

Owns: all raster image algorithms (grayscale, denoise, deskew, edge
detection, morphology, threshold, rescale, rotate, crop, canvas, contours,
textline dewarp) in **two parallel backends** — `cv2_processing/` (CPU,
2,061 lines) and `cupy_processing/` (GPU, 3,153 lines, optional `gpu`
extra) — plus `grayscale_pipeline/` (698 lines, CPU/GPU dispatcher) and
top-level `formats.py`, `page_attributes.py`, `external_tools.py`,
`types.py`, `textline_types.py`.

- `types.py` (19) and `textline_types.py` (56): pure value types, **zero**
  heavy imports (numpy is `T`-only in the latter).
- `formats.py` (281): image-format sniffing + Pillow HEIF/AVIF plugin
  registration; `pillow_heif`/`pillow_avif_plugin` `E` (both guarded by
  try/except so a partial install degrades gracefully). This is the
  module that registers Pillow decoders as an import side effect — cited
  by its own docstring as "the single, documented place where that
  effect lives."
- `external_tools.py` (39): subprocess wrapper around external CLI image
  tools. Runtime/IO, no heavy imports.
- `page_attributes.py` (153): cv2, numpy `E`.
- Every `cv2_processing/*.py` and `cupy_processing/*.py` file: cv2 (or
  cupy, via `_cupy_compat.py`) + numpy, essentially all `E` at module
  level (a handful of `numpy.typing` imports are `T`-only).
- `grayscale_pipeline/*.py`: numpy `E`; `ops_gpu.py` depends on
  `cupy_processing._cupy_compat`.

All algorithm code; no torch/doctr/transformers/pandas anywhere in this
subpackage.

### `layout/` — 1,575 lines total

Owns: page-region layout detection + a pluggable detector registry.

| module | lines | owns | heavy imports |
|---|---|---|---|
| `types.py` | 234 | `LayoutRegion`, `RegionType`, region value types | **none** (stdlib: math, dataclasses, enum) |
| `geometry.py` | 223 | pure-Python region geometry math | **none** (imports only `layout.types`) |
| `ndarray_detection.py` | 100 | array-shape based layout detector | numpy `E` |
| `detector.py` | 158 | detector Protocol + dispatch | cv2, numpy `E` |
| `_mappings.py` | 47 | label-name mapping tables | — |
| `visualize.py` | 106 | overlay rendering for debugging | cv2, numpy `L` (both lazily imported inside the one function, explicitly commented "visualization is optional") |
| `registry.py` | 325 | backend registry/selection | `pp_doclayout` adapter `L` (line 129) |
| `adapters/pp_doclayout.py` | 305 | RT-DETR layout model adapter | torch, transformers, PIL `E` |
| `adapters/__init__.py` | 7 | facade | — |
| `__init__.py` | 70 | facade (imports detector/geometry/ndarray_detection/registry/types/visualize — all eager) | — (cv2/numpy transitively eager via the above) |

`types.py` + `geometry.py` (457 lines) are a clean, heavy-free seam inside
an otherwise cv2/torch-heavy subpackage. `pp_doclayout.py` is the one
torch/transformers-eager module in the whole repo outside `ocr/`; it's
only reached via `registry.py`'s lazy import, so `import
pdomain_book_tools.layout` alone does not load torch (confirmed).

### `matching/` — 3,732 lines total

Owns: the newer immutable, source-neutral OCR-to-text matching contracts
and algorithm (pydantic models + a bounded matching engine), plus a
compatibility shim back onto the legacy mutable `Page`/`Word` API.

| module | lines | owns | heavy imports |
|---|---|---|---|
| `models.py` | 975 | immutable match contracts (pydantic) | **none** — pydantic + `typography` only |
| `pgdp_continuations.py` | 1,091 | PGDP `*` continuation-marker decoding (pydantic) | **none** |
| `engine.py` | 1,136 | the matching algorithm itself | **none** |
| `legacy_projection.py` | 437 | projects immutable match graph onto mutable `ocr.Page`/`Word` | `ocr.block/page/word` are `T`-only; `ocr.ground_truth_matching_helpers.match_type` `E` (a 32-line stdlib-enum leaf) |
| `__init__.py` | 93 | facade | — |

Entirely value-type + pure-algorithm; zero cv2/numpy/torch anywhere.
`legacy_projection.py` is the sole file in the subpackage that names
`ocr.*` types, and only as type hints (never at runtime).

### `ocr/` — 17,904 lines total

Owns: the OCR domain model (`Word`, `Block`, `Page`, `Document`) and the
whole recognition/matching/reorganization pipeline. This is where nearly
all of the torch/doctr/pytesseract/pandas weight lives.

**Heavy-free value-type/contract cluster (941 lines)** — no cv2, no numpy,
no torch anywhere, module- or lazy-level:

| module | lines | owns |
|---|---|---|
| `blob_protocol.py` | 18 | `BlobStoreProtocol` — deliberately dependency-free to avoid a cycle with `pdomain-ops` |
| `character.py` | 132 | `Character` value type (uses `geometry.BoundingBox`, `schemas._helpers`) |
| `label_normalization.py` | 189 | label-string normalization rules |
| `glyph_annotations.py` | 307 | `GlyphAnnotations` side-channel value type (`ocr.word` is `T`-only) |
| `provenance.py` | 141 | provenance value type |
| `review.py` | 49 | review-state value type |
| `gt_orphans.py` | 21 | orphan-token bookkeeping type |
| `text_normalize.py` | 65 | text normalization helpers |
| `ground_truth_matching_helpers/{match_type,character_groups}.py` | 32+42 | enum + grouping tables |
| `__init__.py` | 19 | facade (imports the above + `typography.annotations`) |

**Heavy engine cluster (16,889 lines)**:

| module | lines | heavy imports |
|---|---|---|
| `page.py` | 3,906 | cv2 `E`; doctr referenced only in method **names** (`generate_doctr_*`), no actual doctr import in this file |
| `reorganize_page_utils.py` | 4,234 | cv2, numpy `E`. **Largest file in the repo.** |
| `block.py` | 1,416 | numpy `E` |
| `word.py` | 1,308 | cv2, numpy `E` |
| `document.py` | 1,154 | cv2, numpy `E`; doctr `E` (via `doctr_support`); pandas `T` + `L` (line 1083, `from_tesseract` classmethod); PIL `T` + `L` (line 308, guarded try/except); pytesseract `L` (line 814, guarded try/except) |
| `ground_truth_matching.py` | 1,297 | numpy `E`; `matching.legacy_projection`/`matching.models` `T`; `matching.legacy_projection` `L` (line 212, real runtime call) |
| `doctr_support.py` | 529 | doctr `L` (multiple call sites, all deferred); torch `L` |
| `_dropcap_lexicon.py` | 551 | data table, no imports of note |
| `dropcap.py` | 925 | cv2 `T` + `L` (line 379, guarded try/except) |
| `layout_aware_reorg.py` | 967 | `layout.types`/`layout.geometry` `E` (heavy-free deps) |
| `image_utilities.py` | 278 | `image_processing.cv2_processing` `E` → pulls cv2 transitively |
| `cv2_tesseract.py` | 114 | cv2, pytesseract `L` (both inside functions) |
| `rotation.py` | 210 | `ocr.document` `L`; doctr only in docstrings, no import |

`doctr_support.py` is the sole real doctr/torch entry point in `ocr/`,
and every doctr/torch reference in it is a lazy, function-scoped import —
so loading `ocr.doctr_support` as a module doesn't pull torch in either;
only *calling* its predictor-building functions does.

### `pgdp/` — 2,118 lines total

| module | lines | owns | heavy imports |
|---|---|---|---|
| `pgdp_results.py` | 317 | PGDP page-text cleanup/export | **none** — `json`, `pathlib`, `logging`, `regex` only |
| `f2/offsets.py` | 400 | F2 lexical offset indexing | **none** |
| `f2/tokens.py` | 708 | F2 JSON token model | **none**; `typography.records`/`.spans` `E` |
| `f2/parser.py` | 490 | F2 markup parser | **none** |
| `f2/project_rules.py` | 93 | per-project rule registry | **none** |
| `f2/warnings.py` | 47 | parse-warning types | **none** |
| `f2/__init__.py` | 54 | facade | — |
| `__init__.py` | 9 | facade — re-exports `pgdp_results` **only**, does not import `f2` | — |

Entirely heavy-free. Note: `pgdp/f2/` is real, tested code
(`tests/pgdp/f2/*`) but is not re-exported from `pgdp/__init__.py` — it's
reachable only via the explicit `pdomain_book_tools.pgdp.f2` path.

### `schemas/` — 231 lines total

| module | lines | owns | heavy imports |
|---|---|---|---|
| `_helpers.py` | 85 | shared `__get_pydantic_core_schema__` fragments | **none** — `pydantic_core` only |
| `emit.py` | 126 | JSON-Schema emitter CLI | imports `ocr.{word,block,page,character,review,provenance}` `E` → pulls the entire heavy ocr engine |
| `__main__.py` | 8 | `python -m` entry point | → `emit.py` |
| `__init__.py` | 12 | facade | — |

`_helpers.py` is a pure, tiny, heavily-reused leaf. `emit.py` is
effectively a CLI script bundled inside the package and is the one place
that deliberately touches everything (by design — it's introspecting all
public pydantic models to emit their JSON Schema).

### `typography/` — 4,301 lines total

Owns: the portable, source-neutral typography-label/review contract
layer (spans, records, alignment, normalization, exchange bundles,
review, book manifest). Entirely pydantic value types.

| module | lines | heavy imports |
|---|---|---|
| `spans.py` | 121 | `regex` `E` (third-party, pure-Python, not in the tracked-heavy set but worth noting) |
| `labels.py` | 47 | none |
| `annotations.py` | 76 | none |
| `normalization.py` | 277 | none |
| `records.py` | 922 | `geometry.bounding_box` `E` |
| `exchange.py` | 999 | none |
| `alignment.py` | 812 | `geometry.bounding_box` `E` |
| `book_manifest.py` | 249 | none |
| `review.py` | 633 | none |
| `__init__.py` | 165 | facade |

Zero cv2/numpy/torch/pandas anywhere. Only `records.py`/`alignment.py`
reach outside the subpackage, into `geometry.bounding_box` (shapely).

### `utility/` — 266 lines total

| module | lines | owns | heavy imports |
|---|---|---|---|
| `timing.py` | 111 | timing decorators | **none** — stdlib only |
| `ipynb_widgets.py` | 145 | Jupyter/ipywidgets display helpers | ipywidgets `E` (written as an `if TYPE_CHECKING: ... else: import` — always executes the real import at runtime); numpy `E`; transitively cv2 via `ocr.image_utilities` |
| `__init__.py` | 10 | facade | — |

### Root: `__init__.py` (66), `_version.py` (24), `licenses.py` (71), `data/` (6 + vendored JSON)

`licenses.py` + `data/` are a self-contained SPDX-allowlist value module,
zero heavy imports, used by nothing else in the package (a leaf utility
meant for downstream consumers). `_version.py` is generated. Root
`__init__.py` is the eager-import chokepoint described in §0.

## 3. Internal subpackage dependency graph

Measured by parsing every `from pdomain_book_tools.<pkg>...` /
`import pdomain_book_tools.<pkg>...` statement and bucketing by top-level
subpackage (module-level and lazy imports both counted; direction only):

```
geometry          -> schemas
geometry_correction -> image_processing
hf                -> layout
matching          -> ocr            (see cycle note below)
matching          -> typography
ocr               -> geometry
ocr               -> image_processing
ocr               -> layout
ocr               -> matching       (see cycle note below)
ocr               -> schemas
ocr               -> typography
pgdp              -> typography
root (__init__)   -> geometry, layout, ocr, pgdp, typography
schemas           -> geometry, layout, ocr, typography
typography        -> geometry
utility           -> geometry, ocr
```

**Leaves (nothing internal imports them):** `geometry_correction`, `hf`,
`data`. Both are consumed only by external sibling repos, per the
package's own framing, not by anything inside `pdomain_book_tools` itself.

**Apparent cycles, checked at module granularity — both are false
positives at the package level:**

- `geometry <-> schemas`: `geometry.bounding_box`/`geometry.point` import
  `schemas._helpers` (a leaf, `pydantic_core`-only, no back-imports).
  `schemas.emit` (a different module) imports `geometry.point`/
  `bounding_box`. `_helpers` and `emit` never import each other — no
  runtime cycle, just two unrelated modules sharing a package namespace.
- `ocr <-> matching`: `matching.legacy_projection` imports
  `ocr.ground_truth_matching_helpers.match_type` (a 32-line stdlib-enum
  leaf) at module level; all its other `ocr.*` references are
  `TYPE_CHECKING`-only. `ocr.ground_truth_matching` imports
  `matching.legacy_projection`/`matching.models` under `TYPE_CHECKING`,
  plus **one real runtime lazy import** inside
  `project_match_graph_onto_page`'s caller (line 212) — deferred
  specifically to avoid a real cycle. Net effect: `import
  pdomain_book_tools.matching` does not import `ocr.page`/`word`/`block`
  at all; only calling that one compatibility function does, and by then
  both packages are already loaded. Not a true cycle at import time.

No true circular imports exist between top-level subpackages.

## 4. Contract vs. algorithm vs. runtime/IO

- **Pure value types / contracts** (immutable data + validation, no I/O,
  no heavy compute): all of `typography/`, all of `matching/` except
  `legacy_projection.py`, `geometry/point.py`, `geometry/bounding_box.py`
  (core), `layout/types.py`, `pgdp/pgdp_results.py`, all of `pgdp/f2/`,
  the `ocr/` value-type cluster listed in §2 (`character.py`,
  `label_normalization.py`, `glyph_annotations.py`, `provenance.py`,
  `review.py`, `gt_orphans.py`, `text_normalize.py`, `blob_protocol.py`,
  `ground_truth_matching_helpers/*`), `schemas/_helpers.py`,
  `licenses.py`.
- **Pure algorithms** (compute over those types, no I/O, but may need
  heavy libs to run): `layout/geometry.py` (heavy-free), `matching/engine.py`
  (heavy-free), `matching/legacy_projection.py` (heavy-free at runtime),
  `ocr/layout_aware_reorg.py` (heavy-free deps, though large), the
  `image_processing/{cv2,cupy}_processing/*` op libraries (cv2/cupy-
  dependent), `geometry_correction/*` algorithm modules, `geometry/
  image_ops.py`.
- **Runtime / IO** (model loading, subprocess, file I/O, network, display
  widgets): `ocr/doctr_support.py`, `hf/download.py`, `hf/models.py`,
  `image_processing/external_tools.py`, `image_processing/formats.py`
  (Pillow plugin registration side effect), `layout/adapters/
  pp_doclayout.py`, `utility/ipynb_widgets.py`, `schemas/emit.py`
  (CLI entry point), and the big `ocr/page.py`/`document.py`/
  `reorganize_page_utils.py` trio, which mix domain model, algorithm, and
  I/O (image read/write, OCR engine invocation) together — this mixing is
  itself part of why they're 3,900–4,200 lines each.

## 5. Extraction seams (measured)

| seam | lines | external deps | modules |
|---|---|---|---|
| **A. Contracts core** | 9,328 | pydantic, pydantic-core, shapely | all `typography/*`, all `matching/*`, `schemas/_helpers.py`, `geometry/point.py`, `geometry/bounding_box.py`, `ocr/ground_truth_matching_helpers/*` |
| **B. OCR value types** | 941 | (needs seam A: geometry, schemas._helpers) | `ocr/{blob_protocol,character,label_normalization,glyph_annotations,provenance,review,gt_orphans,text_normalize,__init__}.py`, plus `typography.annotations` (already in A) |
| **C. Layout contracts** | 457 | none | `layout/types.py`, `layout/geometry.py` |
| **D. Licensing/data** | 77 | none | `licenses.py`, `data/__init__.py` + vendored JSON |
| **E. PGDP** | 2,118 | regex; needs seam A (typography) | `pgdp/pgdp_results.py`, all of `pgdp/f2/*` |
| **F. Misc heavy-free util** | 111 | none | `utility/timing.py` |

**A+B+C+D+E+F combined = 13,032 lines (33% of the repo), with a total
external dependency set of `{pydantic, pydantic-core, shapely, regex}` —
none of which are in the declared-heavy list.** This is a single
coherent, already-decoupled subgraph: nothing in it imports cv2, numpy,
torch, doctr, transformers, pandas, matplotlib, IPython, ipywidgets,
pytesseract, or PIL, at module level or lazily (TYPE_CHECKING doesn't
count).

Everything else — 26,061 lines (67%) — is genuinely cv2/numpy/torch/
doctr/transformers/pandas/pytesseract/PIL/ipywidgets-dependent and has
no clean way to shed those deps without rewriting the OCR/image
algorithms themselves.

## 6. Things in the wrong place / overlapping responsibility

- **`ocr/ground_truth_matching.py` (1,297 lines) vs. `matching/engine.py`
  (1,136) + `matching/legacy_projection.py` (437).** These are two
  generations of the same job — matching OCR output against ground
  truth. `matching/legacy_projection.py`'s own docstring calls itself
  "the sole compatibility boundary" back onto the older mutable API,
  which is a direct admission that `matching.engine` is the intended
  long-term home and `ocr.ground_truth_matching` is the legacy path being
  kept alive for existing callers. **Keep `matching.engine`/`models`** as
  canonical; `ocr.ground_truth_matching` is correctly positioned as a
  transitional shim in the heavy package (it operates on mutable
  `Page`/`Word`), not a design flaw, but it should not gain new
  functionality — new matching logic belongs in `matching/`.
- **`ocr/page.py` (3,906) and `ocr/reorganize_page_utils.py` (4,234)** are
  the two largest files in the repo — together 21% of all source — and
  each mixes domain model, algorithm, and I/O. This isn't an overlap
  between two modules so much as under-decomposition within one; it's
  out of scope for a light/heavy split (both stay in the heavy package
  either way) but is the single biggest structural risk in the repo if
  anyone later wants to extract *algorithm* seams out of the heavy
  package too.
- **`geometry_correction/` and `hf/` are both unused by the rest of the
  package.** Not wrong per se (they're presumably consumed by sibling
  repos directly), but worth flagging: neither is a `pgdp`-style trap —
  extracting the light package won't touch them, and they don't need to
  move for this exercise. I would leave both where they are; they're
  already cv2/torch-heavy internally, so folding them into a "light"
  package would defeat the purpose, and splitting them into their *own*
  packages isn't justified by anything in this analysis (no evidence of
  size or coupling pain distinct from the rest of the heavy package).
- **`pgdp/f2/` is real, tested code that `pgdp/__init__.py` doesn't
  re-export.** Not a defect, but worth a decision: if `pgdp/f2` moves
  into the new light package, decide whether `pgdp/__init__.py`'s
  facade should start exporting it, since right now it's reachable only
  by the explicit submodule path.

## Proposed package breakdown (judgement call — position taken, not a menu)

**Split two ways, not more.** Fragmenting `geometry_correction` or `hf`
into their own packages isn't supported by anything measured here — both
are cv2/torch-heavy leaves with no internal consumers to protect and no
evidence of independent release cadence. Two packages solves the actual
stated problem (pgdp/contracts dragged into torch) without over-engineering.

### 1. New package: `pdomain-book-contracts`

Contents: seams A–F above, physically moved (not just re-exported):
`typography/`, `matching/`, `schemas/_helpers.py` (rename its containing
module, e.g. `schemas/helpers.py`, since a full `schemas` package isn't
moving), `geometry/point.py` + `geometry/bounding_box.py`, `layout/
types.py` + `layout/geometry.py`, `pgdp/` (both `pgdp_results.py` and
`f2/`), `licenses.py` + `data/`, the `ocr/`-value-type cluster (probably
renamed out of an `ocr` namespace since there's no heavy `ocr` package
here — e.g. a `records`/`ocr_types` submodule), `utility/timing.py`.

Dependencies: `pydantic`, `pydantic-core`, `shapely`, `regex`. Nothing
else. A `__init__.py` for this package must **not** import anything from
the heavy side — that's the whole point, and it's cheap to enforce
because nothing in seams A–F currently does.

This is what `pdomain-pgdp-api-client` should depend on for real (no more
file-path loading), and what `pdomain-ocr-synth` can safely take a hard
dependency on for recipe/label/matching contracts without pulling torch.

### 2. `pdomain-book-tools` (existing package, slimmed)

Keeps everything else: the `ocr/` engine (`page.py`, `word.py`, `block.py`,
`document.py`, `doctr_support.py`, `dropcap.py`, `_dropcap_lexicon.py`,
`cv2_tesseract.py`, `rotation.py`, `layout_aware_reorg.py`,
`image_utilities.py`, `reorganize_page_utils.py`, `ground_truth_matching.py`),
all of `image_processing/`, all of `geometry_correction/`, `geometry/
image_ops.py`, the heavy half of `layout/` (`detector.py`,
`ndarray_detection.py`, `registry.py`, `visualize.py`, `adapters/`,
`_mappings.py`), all of `hf/`, `schemas/emit.py` + `__main__.py`,
`utility/ipynb_widgets.py`.

Takes `pdomain-book-contracts` as a normal dependency and re-exports the
moved names from its own `__init__.py`/subpackage shims for backward
compatibility (`from pdomain_book_contracts.typography import ...` inside
`pdomain_book_tools/typography/__init__.py`, etc.), so existing importers
of `pdomain_book_tools.typography.X` keep working during a migration
window. Dependency direction is one-way: heavy → light, never the
reverse — already true today except for the physical file locations.

**The root `pdomain_book_tools/__init__.py` re-export list must be
trimmed or made lazy** (e.g. `__getattr__`-based lazy re-export, or just
drop the convenience re-exports) — otherwise even `pdomain-book-tools`
itself keeps eagerly loading cv2/numpy/shapely on **any** submodule
import, contracts included, which reintroduces the original problem for
every consumer that imports through the umbrella package instead of the
new one directly.
