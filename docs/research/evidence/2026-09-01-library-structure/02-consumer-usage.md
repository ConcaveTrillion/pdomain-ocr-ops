# pdomain_book_tools consumer usage — measured, 2026-09-01

Method: `git status`/`git log` per repo for activity; AST parse of every
`import`/`from ... import` statement referencing `pdomain_book_tools` (and, for
the legacy fork, `pd_book_tools`) across all 17 workspace repos, plus manual
grep for `importlib.import_module("pdomain_book_tools...")` dynamic imports
(the AST pass misses these). Read-only throughout; `pdomain-prep-for-pgdp`'s
working tree was read but not modified.

Repos with **zero** references anywhere: `ml-training`, `ml-validation`
(placeholder repos, contain only a stray `all` file, not real projects),
`pdomain-index-npm`, `pdomain-index-pip` (package-index/registry infra, not
consumers), `pdomain-ui` (JS/TS repo; its `pyproject.toml` covers only
maintenance scripts), `pdomain-ocr-synth` (this repo).

## 1. Per-repo table

| Repo | pyproject declaration | Locked version (uv.lock) | Symbols imported (file) |
|---|---|---|---|
| **pd-ocr-labeler** (legacy fork, package name `pd-book-tools`) | `pd-book-tools>=0.1.0`; `tool.uv.sources` pins `git` tag `v0.9.0` | n/a (git tag) | `Page`, `BoundingBox`, `Point`, `Word`, `Block`, `BlockCategory`, `BlockChildType`, `Document`, `OCR_MODEL_SIDECARS`, `hf_download`, `DEFAULT_DET_FILENAME`, `DEFAULT_HF_REPO`, `DEFAULT_RECO_FILENAME`, `prefetch_layout_files`, `resolve_layout_source`, `get_finetuned_torch_doctr_predictor`, `get_default_doctr_predictor`, `crop_image_to_bbox`, `update_line_with_best_matched_ground_truth_text`, `label_normalization.*` (5 names), `OCRModelProvenance`, `OCRProvenance`, `PGDPResults` — 102 import sites across `pd_ocr_labeler/**` and `tests/**` |
| **pd-ocr-trainer** | `pdomain-book-tools` (no specifier); `tool.uv.sources` = bare `git` URL, no tag/branch | git, locked to commit `42c2cc9`, resolves to `0.21.1.dev3` | `DEFAULT_VOCAB_EXTRA_CHARS`, `DEFAULT_VOCAB_LIBRARY` from `ocr.doctr_support` — 2 sites, `src/pd_ocr_trainer/ui.py` |
| **pdomain-ocr-cli** | `pdomain-book-tools>=0.21.0` (+ `pdomain-book-tools[gpu]` forwarding extra); index = `pdomain-index-pip` | `0.21.0` | Static: `image_processing.formats.SUPPORTED_IMAGE_SUFFIXES` (test only), bare `import pdomain_book_tools` (diagnostic script). **Dynamic** (`importlib.import_module`, misses static grep): `image_processing.formats.is_image_file`, `ocr.doctr_support.get_finetuned_torch_doctr_predictor`, `layout.get_detector`, `layout.types.RegionType`, `ocr.reorganize_page_utils.validate_word_preservation`, `ocr.document.Document`, `hf.{DEFAULT_DET_FILENAME,DEFAULT_HF_REPO,DEFAULT_RECO_FILENAME,LAYOUT_MODEL_FILES,OCR_MODEL_SIDECARS,hf_download,prefetch_layout_files,short_revision,silence_transformers_load_chatter,suppress_hf_unauth_warning,resolve_layout_source,resolve_ocr_models}` — `pdomain_ocr_cli/ocr_to_txt.py`, `pdomain_ocr_cli/_hf_models.py` |
| **pdomain-ocr-labeler-spa** | `pdomain-book-tools==0.26.1` (exact pin); index = `pdomain-index-pip` | `0.26.1` | `ocr.page.Page` (dominant symbol, ~40 sites), `typography.*` (24 distinct names: `LabelingBundle`, `TypographyPageRecord`, `WordTypography`, `ArtifactReference`, `LabelState`, `TypographyTaxonomy`, `CorrectionBundle`, `Evidence`, `TypographyTaxonomyLabel`, `TypographyCorrection`, `ReviewState`, `make_word_id`, `BookLabelingManifest`, `ReplacementArtifact`, `TextIdentity`, `ArtifactRef`, `ArtifactSource`, `BookLabelingPage`, `CoordinateTransform`, `CorrectionDecision`, `ModelRun`, `PageGeometry`, `WordGeometry`, `BookMatchRelationReference`, `TYPOGRAPHY_PAGE_RECORD_EXTERNAL_F2_SCHEMA_VERSION`, `split_graphemes`, `StyleLabel`, `AlignmentEvidence`, `ConfidenceTier`, `Grapheme`, `KnowledgeState`, `LabelSource`, `OcrTokenRef`, `SourceCoordinateSpace`, `SourceSlice`, `StyleSpan`, `TargetCoordinateSpace`, `TypographyReviewMetadata`, `TypographySpan`, `GRAPHEME_SEGMENTATION_VERSION`, `REVIEW_CONTRACT_VERSION`), `ocr.rotation.{rotate_image,detect_best_rotation}`, `ocr.label_normalization.{ALLOWED_COMPONENTS,ALLOWED_TEXT_STYLE_LABELS}`, `geometry.{BoundingBox,Point}`, `pgdp.pgdp_results.PGDPResults`. **Dynamic:** `ocr.document` (module, for `.Document`), `hf` (module, for `.hf_download`), `ocr.doctr_support` (module, for `.get_default_doctr_predictor`/`.get_finetuned_torch_doctr_predictor`). **Speculative** (try/except ImportError, module doesn't exist yet): `text.normalize.normalize_string` — `src/pdomain_ocr_labeler_spa/core/text_normalize.py` |
| **pdomain-ocr-simple-gui** | `pdomain-book-tools>=0.21.0`; index = `pdomain-index-pip` | `0.21.0` | `ocr.page.Page`, `ocr.apply_text_normalizations`, `hf.{DEFAULT_DET_FILENAME,DEFAULT_HF_REPO,DEFAULT_RECO_FILENAME,resolve_ocr_models}` — 7 sites in `routes/pages.py`, `routes/model_cache.py`, `pipeline.py`, tests |
| **pdomain-ocr-trainer-spa** | `pdomain-book-tools>=0.18.3`; index = `pdomain-index-pip` | `0.21.0` | `licenses.{SPDX_VALID_IDS,is_valid_spdx_id}` — `src/pdomain_ocr_trainer_spa/domain/publish.py`. Also plans to consume `GlyphAnnotations` (comment in `worker/evaluate.py`) but does **not import it yet** — future M13 work. |
| **pdomain-ocr-training** | `pdomain-book-tools>=0.14.1`; index = `pdomain-index-pip` | `0.21.0` | **None.** Declared but deliberately never imported — `pdomain_ocr_training/protocols.py` states it "never imports `GlyphAnnotations`... that would add a heavy foundation-lib dependency edge." Only non-import references are the `test_git_master_sources.py` fixture text (toml source flipping, not real usage). |
| **pdomain-ops** | `pdomain-book-tools>=0.21.0`; index = `pdomain-index-pip` | `0.21.0` | `ocr.document.Document` (10 sites, mostly `import ... as _doc_mod`), `hf` module / `hf.resolve_ocr_models`, `ocr.doctr_support` module / `.get_finetuned_torch_doctr_predictor`, `ocr.cv2_tesseract.tesseract_ocr_cv2_image`, `ocr.page.Page`, `ocr.BlobStoreProtocol` — `pdomain_ops/gpu/{default_stages,doctr_batch,local_stage}.py` + tests (36 sites total, mostly lazy imports inside functions) |
| **pdomain-pgdp-api-client** | **None** — no `pdomain-book-tools` dependency anywhere in `pyproject.toml` | n/a | **Filesystem-path load, not a package import.** `tests/test_booktools_compat.py` hardcodes `Path("/workspaces/pdomain/pdomain-book-tools/pdomain_book_tools/pgdp/pgdp_results.py")` and loads it via `importlib.util.spec_from_file_location` + `exec_module`, skipping the test if the path is absent. Quoted below. |
| **pdomain-prep-for-pgdp** | `pdomain-book-tools>=0.21.0`; index = `pdomain-index-pip` | `0.21.0` | Widest surface of any repo. `hf.*` (`resolve_layout_source`, `prefetch_layout_files`, `silence_transformers_load_chatter`), `ocr.doctr_support`, `layout.get_detector`, `ocr.document.Document`, `ocr.reorganize_page_utils.validate_word_preservation`, `ocr.word.{Word,BoundingBox,Point}`, `layout.types.{RegionType,LayoutRegion}`, `image_processing.grayscale_pipeline.{GrayscaleConfig,ClaheConfig,Converter,FlattenConfig}`, and a long tail of **private/internal** submodule imports: `image_processing.cupy_processing._cupy_compat.{cp,require_cupy,cupy_available}` (leading-underscore module — not public API) and `image_processing.cupy_processing.{invert,threshold,deskew,rotate,canvas,morph,rescale,denoise}.*` GPU kernels — `src/pdomain_prep_for_pgdp/core/{ocr.py,illustrations.py}`, `core/pipeline/{stage_registry.py,grayscale_autodetect.py,ocr_batch.py}` |
| **pdomain-source-data** | `pdomain-book-tools==0.26.1` (exact pin); index alias `pdomain` (same registry URL as `pdomain-index-pip`) | `0.26.1` | `typography.*` (same family as labeler-spa: `LabelingBundle`, `ArtifactReference`, `CorrectionBundle`, `WordTypography`, `TypographyTaxonomy`, etc.), `pgdp.f2.{F2Parser,DecodedF2Character,LexicalF2Page,read_lexical_f2_index,read_lexical_f2_page}` (undocumented submodule, not in the public-API doc), `matching.*` (`ArtifactRange`, `MatchDocument`, `MatchLine`, `MatchPage`, `MatchToken`, `PgdpContinuation`, `PgdpContinuationDecision`, `PgdpContinuationDecode`, `build_pgdp_surface_document`, `decode_pgdp_continuations`), `geometry.bounding_box.BoundingBox`, `hf.models.{DEFAULT_DET_FILENAME,DEFAULT_HF_REPO,DEFAULT_RECO_FILENAME,resolve_ocr_models}`, `ocr.doctr_support.get_finetuned_torch_doctr_predictor`, `typography.normalization.{build_comparison_view,ComparisonView}`, `typography.spans.GRAPHEME_SEGMENTATION_VERSION` — 26 sites across `pdomain_source_data/{geometry,corrections,manifests,cli.py,tasks/typography,matching}` |

## 2. Symbol frequency (real public surface, most-used first)

Counting only the two live-fork/current lineages separately (`pd_book_tools` is
a different, frozen package at v0.9.0; merging its counts with
`pdomain_book_tools` would conflate two libraries).

**`pdomain_book_tools` (current package), by number of *repos* using it, then sites:**

1. `ocr.page.Page` — 3 repos (labeler-spa, simple-gui, ops), ~50 sites — the single most shared type
2. `hf.resolve_ocr_models` — 3 repos (simple-gui, ops, prep-for-pgdp), 4 sites
3. `ocr.doctr_support.get_finetuned_torch_doctr_predictor` — 3 repos (ops, prep-for-pgdp, source-data), 4 sites
4. `typography.{LabelingBundle, WordTypography, ArtifactReference, LabelState, GRAPHEME_SEGMENTATION_VERSION, TypographyTaxonomy, REVIEW_CONTRACT_VERSION, CorrectionBundle, Evidence, TypographyPageRecord, TypographyTaxonomyLabel, TypographyCorrection, ReviewState, make_word_id, ...}` — 2 repos each (labeler-spa + source-data), 2–15 sites each. This whole family is shared **only** between these two repos, but intensively (it is their primary data-interchange contract).
5. `ocr.document.Document` — 2 repos (ops, prep-for-pgdp), 6 sites
6. `geometry.bounding_box.BoundingBox` — 2 repos (prep-for-pgdp, source-data), 5 sites
7. Everything else — used by exactly 1 repo: `hf.*` model-resolution constants (cli, simple-gui, source-data, prep-for-pgdp each import a subset), `ocr.rotation.*`, `ocr.label_normalization.*`, `licenses.{SPDX_VALID_IDS,is_valid_spdx_id}`, `layout.*`/`layout.types.RegionType`, `pgdp.f2.*`, `matching.*`, `image_processing.grayscale_pipeline.*`, `image_processing.cupy_processing.*` (private), `ocr.cv2_tesseract.tesseract_ocr_cv2_image`, `ocr.BlobStoreProtocol`, `ocr.reorganize_page_utils.validate_word_preservation`, `pgdp.pgdp_results.PGDPResults`.

**Cross-cutting observation:** of the 12 names in the documented public API
(`docs/usage/public-api.md`: `BoundingBox`, `Point`, `Page`, `Block`,
`BlockCategory`, `Word`, `RegionType`, `PGDPResults`, `PGDPExport`, plus the
layout/geometry re-exports), only `Page`, `BoundingBox`, `Point`, `RegionType`,
and `PGDPResults` are actually imported anywhere in the current-lineage repos.
`Block`, `BlockCategory`, `Word`, and `PGDPExport` have **zero** live importers
in `pdomain_book_tools`-based repos (they are used heavily in the legacy
`pd_book_tools` fork by `pd-ocr-labeler`, which is a different package).
Conversely, the busiest actual surface — `typography.*`, `hf.*`, `matching.*`,
`pgdp.f2.*`, `ocr.doctr_support.*`, `ocr.rotation.*`, `ocr.document.Document` —
is **entirely undocumented** as public API; every consumer reaches it through
internal submodule paths the docs explicitly say "may relocate without
notice."

## 3. Version pinning

| Pattern | Repos |
|---|---|
| Exact pin (`==`) | `pdomain-ocr-labeler-spa` (`==0.26.1`), `pdomain-source-data` (`==0.26.1`) |
| Open range (`>=`), resolved via package index | `pdomain-ocr-cli` (`>=0.21.0`), `pdomain-ocr-simple-gui` (`>=0.21.0`), `pdomain-ocr-trainer-spa` (`>=0.18.3`), `pdomain-ocr-training` (`>=0.14.1`), `pdomain-ops` (`>=0.21.0`), `pdomain-prep-for-pgdp` (`>=0.21.0`) |
| Git ref (tag) | `pd-ocr-labeler` → `pd-book-tools` git tag `v0.9.0` |
| Git ref (floating branch, lockfile-pinned commit) | `pd-ocr-trainer` → bare git URL, `uv.lock` resolves to commit `42c2cc9` / `0.21.1.dev3` |
| No dependency at all; filesystem-path source load | `pdomain-pgdp-api-client` |

**The open-range group is stale in practice.** All six open-range repos'
`uv.lock` files are frozen at `0.21.0` (current in-tree book-tools is
`0.26.2`-dev, last tagged `0.26.1`) — five months and roughly a dozen releases
behind, despite declaring unbounded ranges that should track latest. The cause
is documented in-repo: `pdomain-ops/docs/issues/2026-08-08-dep-refresh-cannot-auto-land.md`
records that the weekly automated `dep-refresh` workflow produces correct
version-bump PRs but two branch-protection/CI defects stop them from merging,
so bumps pile up unlanded across the workspace. Only the two repos with exact
pins (`pdomain-ocr-labeler-spa`, `pdomain-source-data`) were hand-updated to
`0.26.1` and are current.

**Filesystem-path load (flagged, per instructions).**
`pdomain-pgdp-api-client/tests/test_booktools_compat.py`:

```python
BOOK_TOOLS_PGDP = Path(
    "/workspaces/pdomain/pdomain-book-tools/pdomain_book_tools/pgdp/pgdp_results.py"
)
...
def _load_pgdp_export() -> Any:
    """Import ``PGDPExport`` from the book-tools source tree, or skip."""
    if not BOOK_TOOLS_PGDP.is_file():
        pytest.skip(f"pdomain-book-tools source not present at {BOOK_TOOLS_PGDP}")
    spec = importlib.util.spec_from_file_location("bt_pgdp_results", BOOK_TOOLS_PGDP)
    if spec is None or spec.loader is None:
        pytest.skip("could not load pdomain-book-tools pgdp_results module")
    module = importlib.util.module_from_spec(spec)
    sys.modules["bt_pgdp_results"] = module
    spec.loader.exec_module(module)
    return module.PGDPExport
```

The repo's own comment explains why: `pgdp_results.py` needs only stdlib +
`regex`, while installing the real package "would drag in torch, doctr, and
opencv for a single pure-Python class." This is a real signal for extraction —
one consumer already wants a torch-free slice of `pgdp_results` badly enough
to hand-roll a source-tree loader keyed to an absolute path that only works in
this exact workspace layout.

## 4. Reimplementation vs. import

No repo reimplements a book-tools domain type as a drop-in substitute. Three
adjacent cases, none of them true duplication:

- **`pdomain-source-data/pdomain_source_data/geometry/records.py`** defines
  `RecognizedWord`/`RecognizerInfo`, explicitly documented as *not* a
  reimplementation of `pdomain_book_tools.typography.records.OcrTokenRef` —
  it composes `pdomain_book_tools.geometry.bounding_box.BoundingBox` directly
  and is a deliberately narrower pre-alignment contract.
- **`pdomain-prep-for-pgdp/src/pdomain_prep_for_pgdp/core/models.py:742`** —
  `class BoundingBox(ApiModel)` with `left/top/width/height` fields. This is a
  parallel wire-format DTO (pydantic API response shape), not built on or
  convertible from book-tools' `BoundingBox` — same name, same conceptual
  shape, independent implementation. A shared package that exported a
  serialization-friendly `BoundingBox` DTO could plausibly replace this.
- **`pdomain-ocr-simple-gui/src/pdomain_ocr_simple_gui/routes/words.py`** —
  `class Word(BaseModel)` with `text/bbox/confidence`, a flattened
  page-relative-coordinate API response shape, independent of
  `pdomain_book_tools.ocr.word.Word`.

## 5. Change impact if re-exported from current locations

If a lightweight package re-exported today's symbols from their *current*
submodule paths (no renaming), most consumers need **zero code change** —
only a `pyproject.toml`/lockfile dependency swap:

- **No code change, dependency-file only:** `pdomain-ocr-cli`,
  `pdomain-ocr-simple-gui`, `pdomain-ocr-trainer-spa`, `pdomain-ops`,
  `pdomain-source-data`, `pd-ocr-trainer` — all import fully-qualified
  submodule paths (`pdomain_book_tools.ocr.page`, `.hf`, `.licenses`, etc.)
  that a re-export package could mirror exactly.
- **No code change, and no dependency at all today:**
  `pdomain-ocr-training` (declares the dependency but imports nothing).
- **Real edit required:**
  - `pdomain-pgdp-api-client` — the hardcoded absolute filesystem path breaks
    the moment `pgdp_results.py` moves to a new package; this consumer must
    switch to a real (lightweight) import.
  - `pdomain-ocr-labeler-spa` — its `text.normalize` try/except probe assumes
    a module that doesn't exist yet; if a lightweight package ships that
    functionality at a different path, the probe needs updating.
  - `pdomain-prep-for-pgdp` — imports private, underscore-prefixed
    `image_processing.cupy_processing._cupy_compat` directly; a lightweight
    extraction that dropped GPU-only internals (plausible, since a "light"
    package is unlikely to carry CuPy kernels) would break this repo outright
    and require it to keep depending on full `pdomain-book-tools` for that
    slice, or get those internals promoted to public API.
  - `pd-ocr-labeler` — out of scope for this extraction; it consumes a
    different, frozen package (`pd-book-tools` v0.9.0), not
    `pdomain-book-tools`.

## 6. Blast pattern of a coordinated version bump

Dependency order, closest to book-tools outward:

1. **`pdomain-book-tools`** (source of truth) — any extraction/re-export
   change lands here first.
2. **Direct consumers with no further in-workspace dependents on the same
   surface** — can bump independently, any order: `pdomain-ocr-cli`,
   `pdomain-ocr-simple-gui`, `pdomain-ocr-trainer-spa`, `pdomain-ocr-training`
   (no-op), `pdomain-ops`, `pd-ocr-trainer`.
3. **`pdomain-source-data`** and **`pdomain-ocr-labeler-spa`** — these two
   share the `typography.*`/`matching.*` contract surface tightly (both at
   exact-pin `0.26.1` today, both consuming `LabelingBundle`,
   `TypographyPageRecord`, etc.). They are not dependents of each other
   directly, but a breaking change to `typography.*` must land in both in the
   same coordinated step, since they are the two repos actually exercising
   that contract end-to-end (source-data produces labeler bundles that
   labeler-spa consumes as files, per `prepare_labeler_book.py`/
   `prepare_labeler.py`).
4. **`pdomain-prep-for-pgdp`** — widest and deepest surface (including
   private `cupy_processing` internals), so it is the highest-risk repo for
   *any* internal-path change; bump and verify it last among the active
   fleet, after the narrower consumers prove the new surface out.
5. **`pdomain-pgdp-api-client`** — not a real dependent today (filesystem
   load), but should be converted to a real lightweight-package import as
   part of (or immediately after) the extraction, since it is the strongest
   signal for *why* to extract in the first place.
6. **Before any of this is safe to automate:** the workspace's `dep-refresh`
   auto-land path is currently broken (see §3) — six repos are silently
   5+ months stale. A coordinated bump run manually today would still need
   each repo bumped by hand until that CI/branch-protection issue is fixed;
   otherwise the new package version will pile up in unmergeable PRs exactly
   like the current `0.21.0` staleness.
7. **Out of blast radius:** `pd-ocr-labeler` (different package,
   `pd-book-tools`), `ml-training`, `ml-validation`, `pdomain-index-npm`,
   `pdomain-index-pip`, `pdomain-ui`, `pdomain-ocr-synth`.

## Inactive / legacy repos (evidence)

- **`pd-ocr-labeler`** — self-declared in its own README: "supported legacy…
  of `pd-ocr-labeler-spa`." `pdomain-ocr-labeler-spa/AGENTS.md`: "FastAPI +
  React/Vite/TS replacement for the NiceGUI `pd-ocr-labeler`… The legacy
  `pd-ocr-labeler` is superseded." Still receives real commits (last
  2026-08-08), so it is maintained-but-frozen, not dead — but it runs on an
  entirely different, older package lineage (`pd-book-tools` v0.9.0, git tag,
  ConcaveTrillion's personal account) that predates the `pdomain` org rename.
  Its usage should not constrain a `pdomain-book-tools` extraction design.
- **`pd-ocr-trainer`** — not formally marked deprecated, but its commit
  history since 2026-05-28 contains only CI/chore fixes, no feature work,
  while its apparent successor lineage (`pdomain-ocr-training` +
  `pdomain-ocr-trainer-spa`) is under active development (commits as recent
  as 2026-09-01). Treat as low-signal for the extraction design.
- **`ml-training`, `ml-validation`** — placeholder directories (each contains
  only a stray `all` file), not functioning repos.
- **`pdomain-index-npm`, `pdomain-index-pip`** — package-registry
  infrastructure, not book-tools consumers by design.
- **`pdomain-ui`** — JS/TS repo; its `pyproject.toml` exists only for
  repo-maintenance scripts and explicitly is "not a published package."
