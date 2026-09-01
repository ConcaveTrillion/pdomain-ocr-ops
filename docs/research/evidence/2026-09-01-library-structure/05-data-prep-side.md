# Data-prep side: structural analysis

Read-only survey of `pdomain-source-data`, `pdomain-prep-for-pgdp`,
`pdomain-pgdp-api-client`, `pdomain-ops`, `pdomain-ocr-cli`,
`pdomain-ocr-synth`, plus `pdomain-book-tools` as the shared contract
anchor. No files were modified.

## 1. What each repo owns, and activity status

| repo | owns | status | evidence |
|---|---|---|---|
| `pdomain-source-data` | Prepares public-domain source data: source identity, cross-corpus evidence, reviewed corrections, audits, labeler bundles, training manifests. Explicitly *not* model training/inference/acquisition. | **Active** | HEAD `a004538` dated 2026-09-01 ("add batch page geometry from fine-tuned OCR models"); recent history includes a merged `feature/pgdp-whole-book` branch. No deprecated/legacy markers. |
| `pdomain-prep-for-pgdp` | FastAPI + React/XState web app that turns scanned book images into a PGDP-ready **submission** package (proofing images, OCR text, upload zip for pgdp.net). One-directional: produces submissions, does not consume PGDP round exports. | **Active** | Commits up to today; extensive `docs/architecture`, `docs/plans`, `docs/decisions`, tests, e2e tests. Uncommitted work in-flight is confined to the zip-tool area (`frontend/src/machines/tools/zipTool.ts` and siblings) — cosmetic/in-progress, not touched. |
| `pdomain-pgdp-api-client` | Library + CLI (`pgdp-fetch`) that mirrors Distributed Proofreaders projects to local disk (`<root>/<projectid>/{001.png, pages.json, rounds/*.json, project.json, inventory.json}`) before they become unreachable. Fetches bytes only; does not interpret them. | **Active** | HEAD `c94e38d` dated 2026-08-31/09-01. |
| `pdomain-ops` | Shared ops library for the pd-* suite: install registry, UI prefs, sibling-app launcher, GPU dispatch (`StageDispatcher`, `ModalStageDispatcher`), `schemas.emit` codegen. Imported by every pd-* SPA backend. | **Active**, stable | Recent commits are docs/issue housekeeping, not churn — consistent with a settled shared library, not staleness. |
| `pdomain-ocr-cli` | User-facing CLI (`pdomain-ocr`) that OCRs scanned pages to `.txt` with layout-aware reading order and auto-rotation, wrapping book-tools OCR/layout primitives. | **Active** | Recent commits are dependency/CI maintenance. |
| `pdomain-ocr-synth` | Recipe-driven synthetic OCR training-data generator (this repo). Independently builds a full PGDP F2 parse → align → style-span pipeline (see §6). | **Active**, M00–M10 shipped | This session's own repo state. |
| `pdomain-book-tools` | Shared contract package: OCR/layout/image primitives (heavy: torch, doctr, transformers, opencv) plus lightweight typography/PGDP data contracts. | **Active**, foundation lib | Every other pd-* repo pins it. |

No repo carries an explicit "legacy"/"superseded" marker. `pdomain-ops` and `pdomain-ops` is not a deploy orchestrator: no docker-compose/Dockerfile/infra-as-code found; its GitHub workflows only self-checkout, so no repo here proves deployment wiring across the suite.

## 2. PGDP handling by repo

Two PGDP formats exist, both wrapped by book-tools:

- **Plain proofread-text export** (e.g. one JSON `{png_filename: page_text}`, historically the `P3`-style round) — read by `pdomain_book_tools/pgdp/pgdp_results.py` (`PGDPExport`, `PGDPResults`).
- **Lossless per-character F2 token stream** (`F2.json`, in-line markup like `/*i*/…/*/`) — read by `pdomain_book_tools/pgdp/f2/` (`F2Parser`, `read_lexical_f2_page`, etc).

| repo | reads PGDP round files? | which reader | reimplements locally? |
|---|---|---|---|
| `pdomain-source-data` | Yes — `pdomain_source_data/sources/pgdp.py` (179 lines) discovers `project.json`/`rounds/F2.json`/page images but only hashes/records `F2.json` as an opaque `SourceArtifact`; it never parses the content itself. | Delegates parsing entirely to `pdomain_book_tools.pgdp.f2` (`F2Parser`, `read_lexical_f2_index`, `read_lexical_f2_page`) — imports in `tasks/typography/prepare_labeler.py:12` and `prepare_labeler_book.py:24-29`. Zero hits for `pgdp_results`/`PGDPExport`/`PGDPResults`. | No. Clean consumer of the newer `f2/` parser. |
| `pdomain-prep-for-pgdp` | No. Zero occurrences of `P3.json`/`F2.json`/`pgdp_results`/`PGDPExport`/`.pgdp.*` anywhere. It authors an outbound `pgdp.json` submission manifest (`core/packaging.py:175`) and validates outbound filenames against DP's naming rules (`core/pipeline/pgdp_naming.py`, 218 lines) — production side, not round-file consumption. | n/a | No. |
| `pdomain-pgdp-api-client` | Fetches raw round bytes (`rounds/P3.json`, `rounds/F2.json`) but does not parse them at runtime. Its **test suite** parses them, to verify its own mirror output stays readable. | `PGDPExport.from_json_file` from `pgdp_results.py`, loaded straight from the book-tools **source tree** by absolute path (see §3). | No production reimplementation; test-only, and loaded by unusual means for a stated reason (§3). |
| `pdomain-ops` | No PGDP round-file reads. All "pgdp" hits are naming references to the sibling repo (e.g. cherry-pick provenance comments), not parsing. | n/a | No. |
| `pdomain-ocr-cli` | No PGDP round-file reads. Two comments cross-reference `pdomain-prep-for-pgdp` for illustration serialization / shared HF model config, nothing more. | n/a | No. |
| `pdomain-ocr-synth` | Yes — reads `F2.json`-shaped page maps. | **Neither.** It has its own from-scratch parser: `src/pdomain_ocr_synth/pgdp/f2.py` (248 lines, `load_f2`, `parse_f2_pages`, `_scan_page`, handling the identical `/* */` / `/# #/` control-block syntax as book-tools' `f2/tokens.py`). | **Yes — full reimplementation.** See §5–§6. |

Net picture: every other consumer either delegates cleanly to book-tools' readers or doesn't touch PGDP round files at all. `pdomain-ocr-synth` is the sole repo that reimplements PGDP F2 parsing independently.

## 3. `pdomain-pgdp-api-client`: absolute-path load of `pgdp_results.py`

File: `/workspaces/pdomain/pdomain-pgdp-api-client/tests/test_booktools_compat.py`.

Module docstring (lines 1–10):

```python
"""The mirror's on-disk output must stay readable by pdomain-book-tools.

This is the most important test in the repo. If it fails, every corpus already
mirrored under pdomain-data/source-pgdp-data/output/ has been invalidated, and
so has every downstream consumer of that layout.

``PGDPExport`` is loaded straight from the sibling source tree rather than from
an installed package. ``pgdp_results.py`` needs only the standard library and
``regex``, whereas installing pdomain-book-tools would drag in torch, doctr,
and opencv for a single pure-Python class.
"""
```

Loader (lines 32–50):

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

`pyproject.toml` (lines 33–36) echoes the same rationale: `regex` is a dev
dependency "Only so tests can import `pdomain_book_tools.pgdp.pgdp_results`
directly from the sibling source tree... Importing the installed book-tools
package would drag in torch, doctr, and opencv."

**What breaks if the file moves.** The path is a literal absolute string —
no `sys.path` manipulation, no relative resolution from this repo, no
checked-in copy or version pin. It assumes (a) `pdomain-book-tools` is
checked out as a workspace sibling under `/workspaces/pdomain/`, and (b) the
file sits at exactly `pdomain_book_tools/pgdp/pgdp_results.py` inside it. If
`pgdp_results.py` is extracted to a new package/location, `BOOK_TOOLS_PGDP.is_file()`
returns `False` and the test **skips silently** rather than failing —
the self-described "most important test in the repo" would stop verifying
the `pages.json` contract with no visible CI signal. `pdomain-book-tools`
is not a runtime or declared dependency of this repo at all (`pyproject.toml`
`[project.dependencies]` = `httpx`, `pydantic`, `typing-extensions` only) —
the whole point of the path hack is to avoid adding it.

## 4. `pdomain-source-data` vs `pdomain-prep-for-pgdp`: not duplicates

Despite similar-sounding names, these are opposite ends of the same
pipeline, not overlapping implementations:

- `pdomain-prep-for-pgdp` runs **before** DP round-trips exist: scan → OCR →
  submission package for upload to pgdp.net. It never reads P3/F2 round
  files — it produces the material DP will eventually round-trip.
- `pdomain-source-data` runs **after** DP has produced rounds: it discovers
  `project.json`/`F2.json`/page images already mirrored locally (via
  `pdomain-pgdp-api-client`'s output layout), and builds OCR-training
  ground truth/labeler bundles from them (`tasks/typography/prepare_labeler*.py`).

Neither repo's docs reference the other by name; no cross-repo call graph
was found. No supersession — genuinely different pipeline stages.
`pdomain-prep-for-pgdp` does depend on book-tools (`pyproject.toml:16`,
`pdomain-book-tools>=0.21.0`) for OCR/layout/image processing
(`core/ocr.py`, `core/illustrations.py`, `core/pipeline/stage_registry.py`),
but never touches `pdomain_book_tools.pgdp.*`.

## 5. `pdomain-ocr-synth`: no book-tools dependency, confirmed

`pyproject.toml` `[project.dependencies]` = `pydantic`, `pyyaml`, `httpx`,
`beautifulsoup4`, `freetype-py`, `uharfbuzz`, `pillow`, `numpy`. No
`pdomain-book-tools` entry anywhere (`grep -rn "book_tools\|book-tools"`
across `*.py`/`*.toml`/`*.md` returns only doc mentions of a **future**
coupling — `CLAUDE.md:62` calls it "potential future dependency";
`docs/specs/12-glyph-annotations-emission.md:274` says outright "this repo
has no runtime dependency or confirmed current shared-model contract" with
book-tools; `docs/specs/13-dev-local-mode-and-deps.md:55-57` states its only
current workspace coupling is the **output** contract with `pd-ocr-trainer`,
not book-tools).

**What it would need to adopt book-tools' contracts** (see §6/§7 for the
specific overlap):

- `pdomain_book_tools.pgdp.f2` (`F2Parser`, `read_lexical_f2_*`) in place of
  its own `src/pdomain_ocr_synth/pgdp/f2.py`.
- `pdomain_book_tools.typography.spans` (`CanonicalModel`, `SourceSlice`,
  `StyleSpan`) and `.labels` (`StyleLabel`, `ConfidenceTier`, etc.) in place
  of its own `pgdp/models.py` / `pgdp/profile_models.py` style-kind types.
- `pdomain_book_tools.typography.alignment` (`align_tokens`,
  `project_token_ranges`, `project_style_span`, `OcrTokenRef`,
  `TokenAlignmentResult`) in place of its own `alignment_dp.py` /
  `alignment_source.py` / `alignment.py` DP-alignment-and-projection code.
- Transitively, `pdomain_book_tools.geometry.bounding_box`, which pulls in
  **shapely** (the one non-stdlib dep in this chain — no torch/doctr/opencv).

This is a real but bounded cost: shapely, not the ML stack.

## 6. The glue pattern: seed tokens → parse → align → project spans

**In `pdomain-ocr-synth`** (`src/pdomain_ocr_synth/pgdp/`, total package
9,539 lines):

| file | lines | role |
|---|---|---|
| `f2.py` | 248 | Parses F2 JSON page maps: `load_f2`, `parse_f2_pages`, `_scan_page`, `_handle_opener`/`_handle_closer` for `/* */`/`/# #/` control blocks. |
| `alignment_source.py` | 1,110 | Tokenizes source text and extracts style runs: `tokenize_source_page`, `tokenize_f2_pages`, `StyleRun`, `NormalizationOperation` — the "seed tokens + recognize style spans" stage, independently reimplementing the same `/* */`, `/# #/`, `i`/`b`/`sc`/`f`/`g`/`tb` tag grammar as book-tools' `f2/tokens.py`. |
| `alignment_dp.py` | 751 | `align_sequences`, `assess_alignment`, `to_feature_page` — dynamic-programming alignment of source lines against OCR line candidates. |
| `alignment.py` | 710 | Orchestrates: builds `AlignmentReport`/`PageAlignment`/`ProjectAlignment` from the above, snapshot-hashes images. |
| `alignment_models.py` | 1,293 | Wire-format models: `AlignmentDiagnostic`, `AlignmentOperation`, `WireFormattingSpan`, `WireStyleRun`, etc. |
| `alignment_image.py` | 1,039 | `extract_line_candidates` — pulls OCR line candidates from page images (this piece is genuinely synth-specific: it works against rendered/synthetic images, not scans). |

Core reimplemented chain (parse F2 → tokenize/seed → align → project style
spans as wire spans), excluding the image-specific and training-quality
pieces (`alignment_image.py`, `profiling.py`, `ranking.py`,
`page_templates.py`, `image_measurement.py`): **f2.py + alignment_source.py
+ alignment_dp.py + alignment.py + alignment_models.py ≈ 4,112 lines.**

**In `pdomain-book-tools`**, the equivalent chain already exists and is
explicitly built for exactly this use:

| file | lines | role |
|---|---|---|
| `pgdp/f2/tokens.py` | 708 | Byte-preserving F2 tokenization: same `/* */`, `/# #/`, `i`/`b`/`sc`/`g`/`f`/`u` tag grammar. |
| `pgdp/f2/offsets.py` | 400 | Lossless lexical access to F2 JSON strings (`DecodedF2Character`, `LexicalF2Page`). |
| `pgdp/f2/parser.py` | 490 | `F2Parser.parse_page` → `TypographyPageRecord`. |
| `pgdp/f2/project_rules.py` + `warnings.py` | 93 + 47 | Per-project rule overrides and parse-warning gating. |
| `typography/alignment.py` | 812 | `align_tokens` (DP-align source text to OCR tokens), `project_token_ranges`, `project_style_span` — token seeding, alignment, and span projection in one module. Per its own `__init__.py` exports, this is consumer-facing API with **no in-repo callers** — i.e., it exists specifically for downstream repos like ocr-synth to use, and currently nothing in the workspace calls it. |
| `typography/spans.py`, `labels.py`, `normalization.py` | 121 + 47 + 277 | `CanonicalModel`, `SourceSlice`, `StyleSpan`, `StyleLabel`, `ComparisonView`/`ComparisonOperation` — the span/label contracts and text-diff primitives the alignment code sits on. |

Book-tools equivalent core: **f2/\* (2,109 lines across offsets/parser/tokens/project_rules/warnings/\_\_init\_\_) + typography/alignment.py (812) + spans.py/labels.py/normalization.py (445) ≈ 3,366 lines**, all pure pydantic/stdlib/regex except one transitive shapely import (`typography/records.py` → `geometry/bounding_box.py`). No torch/doctr/opencv/pandas anywhere in this chain.

**Duplication finding:** `pdomain-ocr-synth` independently rebuilt
~4,100 lines of F2-parse → tokenize → DP-align → project-style-spans glue
that has a ~3,400-line equivalent already shipped in book-tools, purpose-built
for downstream use and currently unused by anyone. `pdomain-source-data`
took the opposite path — it imports book-tools' `f2.F2Parser` directly
(§2) and, per its own docstrings, treats OCR-token seeding and F2-span
projection as separate concerns that book-tools' contracts are meant to
join, referencing book-tools' `matching` module for whole-book alignment.
ocr-synth is the outlier both in reimplementing the parser and in not
using the alignment/projection API that was seemingly built for it.

## 7. Contracts this side needs vs. application logic that stays

**Needs from a lightweight package** (all confirmed pure pydantic/stdlib/regex, no torch/doctr/transformers/opencv):

- PGDP readers: `pgdp/pgdp_results.py` (317 lines, `PGDPExport`/`PGDPResults`,
  plain-text export) and `pgdp/f2/*` (2,109 lines, lossless F2 token format)
  — genuinely different input formats, not duplicate versions of one
  another (book-tools' own `f2/parser.py:422` docstring calls the
  `pgdp_results.py` path "legacy" relative to F2, but nothing marks it
  deprecated; both are still exported from the package `__init__` and
  documented in the public API).
- Span/label/token data contracts: `typography/spans.py`, `labels.py`,
  `normalization.py` (445 lines combined) — no heavy or shapely deps at all.
- The alignment glue: `typography/alignment.py` (812 lines,
  `align_tokens`/`project_token_ranges`/`project_style_span`/`OcrTokenRef`/
  `TokenAlignmentResult`) — only shapely as a transitive dependency (via
  `records.py` → `geometry/bounding_box.py`), not the ML stack.

**Stays as application logic** (repo-specific, not contract material):

- `pdomain-ocr-synth`'s `alignment_image.py` (1,039 lines) — extracting OCR
  line candidates from rendered/synthetic page images is specific to this
  repo's synthetic-image pipeline, not a shared contract.
- `pdomain-ocr-synth`'s `profiling.py`/`ranking.py`/`page_templates.py`/
  `image_measurement.py`/`features.py` (373+385+325+442+134 = 1,659 lines)
  — training-data quality scoring and page-template fitting, specific to
  choosing which PGDP pages are good synth training candidates.
- `pdomain-source-data`'s `geometry/recognize.py`/`doctr_recognizer.py`
  (100+239 lines) — batch OCR recognition orchestration, and
  `tasks/typography/prepare_labeler*.py`/`page_ground_truth.py`/
  `materialize.py` (620+1046+527+835 lines) — multi-source ground-truth
  merging with confidence tiers, specific to this repo's labeler-bundle
  business logic even though it calls book-tools contracts underneath.
- `pdomain-prep-for-pgdp`'s OCR/packaging pipeline (`ocr.py`,
  `pipeline/steps/*`, `pgdp_naming.py`, `packaging.py`) — DP submission
  packaging rules, not a parsing contract.
- `pdomain-pgdp-api-client`'s mirror/index/CLI layers — fetch-and-store
  orchestration; it correctly avoids taking book-tools as a runtime
  dependency at all, given it needs only one lightweight class for tests.

Bottom line: extracting `pgdp_results.py` + `pgdp/f2/*` + `typography/{spans,labels,normalization,alignment}.py` into a lightweight package (stdlib + regex + pydantic + shapely, no ML stack) would let `pdomain-pgdp-api-client` import normally instead of path-hacking, and would give `pdomain-ocr-synth` a real alternative to its ~4,100 lines of independently reimplemented parse/align/project glue — the shapely dependency is the only added weight, and it's already present via `pdomain-book-tools`' current callers.
