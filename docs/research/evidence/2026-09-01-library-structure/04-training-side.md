# Model-training side — structural analysis

Scope: `pdomain-ocr-training`, `pd-ocr-trainer`, `ml-training`, `ml-validation`,
`pdomain-ocr-trainer-spa`. Read-only. All paths absolute.

## 1. Repo identity and status

| Repo | Status | Evidence |
|---|---|---|
| `/workspaces/pdomain/pdomain-ocr-training` | **Active, current.** Owns all torch/DocTR training code. | `README.md` front matter `Status: active`; commits through 2026-09-01 (`5d7e03c`, same day as this analysis); `docs/architecture/00-overview.md` "Status: Current as of 2026-07-14". |
| `/workspaces/pdomain/pd-ocr-trainer` | **Superseded by `pdomain-ocr-training`, but not self-declared legacy.** | `pdomain-ocr-training/README.md`: *"Supersedes the legacy `pd-ocr-trainer` repo."* `pdomain-ocr-training/docs/architecture/00-overview.md:140` calls it "the legacy `pd-ocr-trainer` repo" and notes `detect.py`/`recog.py`/`datasets.py`/`utils.py` were "Verbatim-moved ... (legacy)" from it. `pdomain-ocr-training/pyproject.toml` per-file-ignores comment: *"Legacy modules moved verbatim from pd-ocr-trainer."* Yet `pd-ocr-trainer`'s own `README.md`/`docs/context/current-state.md` front matter still says `Status: active`, and it has commits as recent as 2026-08-08 (`9a074050`). Confirmed: **the claim that a repo is "described elsewhere as legacy and superseded" is true of `pd-ocr-trainer`**, described that way *by `pdomain-ocr-training`*, but `pd-ocr-trainer` itself has not been retired, does not self-describe as legacy, and its `pyproject.toml`/`src/pd_ocr_trainer/{train_detect,train_recog,dataset_store}.py` were never repointed to depend on `pdomain-ocr-training` — no `pdomain_ocr_training` reference exists anywhere in `pd-ocr-trainer`. Two independent, diverging copies of the same DocTR training code currently exist. |
| `/workspaces/pdomain/pdomain-ocr-trainer-spa` | **Active, current UI.** | `README.md` "Status: active"; replaces `pd-ocr-trainer`'s NiceGUI UI (its own README ambiguously hyperlinks "NiceGUI user interface" to `pdomain-ocr-training`, but the NiceGUI app is actually `pd-ocr-trainer`'s per that repo's own README — a doc-precision issue, not a code one) while consuming `pdomain-ocr-training`'s `ITrainingRunner`/`IEvalRunner` contracts. Commits through 2026-08-31 (`37fba68`). |
| `/workspaces/pdomain/ml-training`, `/workspaces/pdomain/ml-validation` | **Not repositories.** Each is `git`-untracked, contains only an empty `all/` directory, no `.git`. These are almost certainly a side effect of importing `pdomain_ocr_training/datasets.py` (or `pd-ocr-trainer`'s equivalent) from `/workspaces/pdomain` as cwd — that module runs `ML_TRAINING_DIR.mkdir(exist_ok=True)` / `(ML_TRAINING_DIR / "all").mkdir(...)` at **import time**, and both `ML_TRAINING_DIR`/`ML_VALIDATION_DIR` default to `<project_root>/ml-training` / `ml-validation`. The real, populated dataset trees live inside `pd-ocr-trainer/ml-training/all/{detection,recognition}/{images/,labels.json}` and `pd-ocr-trainer/ml-validation/all/...` — confirmed non-empty, real DocTR `images/`+`labels.json` layout, different inodes from the top-level stubs. Treat the top-level `ml-training`/`ml-validation` as noise, not part of this analysis. |

## 2. How `pdomain-ocr-training` achieves its torch-free contract boundary

**Package split (module layout, from `docs/architecture/00-overview.md` and
`pdomain_ocr_training/`):**

```
pdomain_ocr_training/
    __init__.py      # public API re-exports; lazy for LocalTrainingRunner/LocalEvalRunner
    protocols.py      # ITrainingRunner + IEvalRunner Protocols; ALL config + result pydantic models — torch-free
    local.py           # LocalTrainingRunner — callback→generator bridge (imports detect.py/recog.py → torch)
    local_eval.py      # LocalEvalRunner — torch-free shell; imports _eval_backend lazily inside each method
    _eval_backend.py  # real DocTR forward-pass eval code — torch/doctr live here
    detect.py           # verbatim-moved DocTR detection training (legacy, per-file lint-ignored)
    recog.py            # verbatim-moved DocTR recognition training (legacy, per-file lint-ignored)
    datasets.py         # ExportManager — on-disk dataset layout manager (legacy)
    utils.py            # shared training utilities (legacy)
```

**Torch-free modules:** `protocols.py`, `__init__.py`, `local_eval.py` (the
shell only — its real backend is elsewhere), and `datasets.py`/`utils.py` at
the interpreter level (they don't `import torch`, though they're not part of
the advertised contract surface).

**Torch-requiring modules:** `local.py`, `_eval_backend.py`, `detect.py`,
`recog.py`.

**Mechanism — three layers:**

1. **Optional extra** (`pyproject.toml`): base `dependencies` = `pdomain-book-tools`, `pydantic`, `tomli`, `tomli-w` (no torch). `[project.optional-dependencies].train` = `python-doctr`, `torch`, `torchvision`, `matplotlib`, `numpy`. Install as `pdomain-ocr-training[train]` for the heavy stack.
2. **Lazy attribute resolution at package level** (`__init__.py`): `LocalTrainingRunner` and `LocalEvalRunner` are *not* imported eagerly. A module-level `__getattr__(name)` resolves them only on first attribute access (`pdomain_ocr_training.LocalTrainingRunner`), importing `pdomain_ocr_training.local`/`local_eval` inside the function body. A `ModuleNotFoundError` from a missing torch is caught and re-raised as an `ImportError` with actionable install guidance ("Install it with: pip install 'pdomain-ocr-training[train]'").
3. **Lazy import inside function bodies, one layer deeper** (`local_eval.py` → `_eval_backend.py`): `local_eval.py` itself never imports torch/doctr; each of `evaluate_detection_from_config`/`evaluate_recognition_from_config` does `from pdomain_ocr_training import _eval_backend` *inside the function*, so `LocalEvalRunner` is fully constructible and Protocol-conformant without ever touching torch — only calling `.evaluate_*()` pulls in the real backend.

**Where the boundary is enforced/tested:**
`/workspaces/pdomain/pdomain-ocr-training/tests/test_torch_free_import.py`.
It runs each assertion in a **subprocess** with a custom `importlib.abc.MetaPathFinder`
(`_Blocker`) inserted at `sys.meta_path[0]` that raises `ModuleNotFoundError`
for `torch`/`doctr`/`torchvision`/`matplotlib`, simulating a base install even
though the dev environment has `[train]` installed. Tests assert: base import
succeeds and `"torch" not in sys.modules`; the torch-free public surface
(`DetectionConfig`, `RecognitionConfig`, `TrainingEvent`, `*EvalConfig`,
`*EvalResult`, `EvalSlice`, `GlyphFeatureSet`, `ITrainingRunner`,
`IEvalRunner`) imports and is usable; `pdomain_ocr_training.LocalTrainingRunner`
raises the guiding `ImportError`; `LocalEvalRunner` resolves without pulling
torch into `sys.modules`; and (outside the blocker, real venv) both runners
import fine with `[train]` installed. `pyproject.toml`'s `dev` dependency
group comment states explicitly: *"The torch-free import contract is verified
separately by tests/test_torch_free_import.py, which runs a subprocess with
torch hidden from sys.modules."*

Design precedent cited in `protocols.py`'s module docstring: this mirrors an
existing workspace idiom in `pdomain-ops` (`pdomain_ops.gpu.protocols`) —
`@runtime_checkable Protocol` + separately-shipped `Local*` implementation
(`StageDispatcher`/`LongJobRunner` in
`/workspaces/pdomain/pdomain-ops/pdomain_ops/gpu/protocols.py`). This is not
a novel pattern invented here — it's a second application of one already
established in `pdomain-ops`.

## 3. Task structure: `ITrainingRunner` / `IEvalRunner`

Both defined in `pdomain_ocr_training/protocols.py` as
`@runtime_checkable class X(Protocol)` (from `typing_extensions`). **Tasks are
hard-wired, not pluggable.** There is no registry, no discovery mechanism, no
`register_task()` call — the two task kinds (detection, recognition) are
fixed as named methods on each Protocol. Adding a third task (e.g. a
typeface classifier — flagged in `pdomain-ocr-trainer-spa`'s README as "not
implemented") means widening these two Protocols with new method pairs, or
introducing a third sibling Protocol; existing call sites and concrete
runners would all need updating. It is a closed, compile-time contract, not
an open plugin surface.

**`ITrainingRunner`** — two methods, config in / event stream out:

```python
def train_detection(self, profile: str, config: DetectionConfig) -> Iterator[TrainingEvent]: ...
def train_recognition(self, profile: str, config: RecognitionConfig) -> Iterator[TrainingEvent]: ...
```

**`IEvalRunner`** — two methods, config in / result object out (no epoch loop, so synchronous return rather than an iterator):

```python
def evaluate_detection(self, profile: str, config: DetectionEvalConfig) -> DetectionEvalResult: ...
def evaluate_recognition(self, profile: str, config: RecognitionEvalConfig) -> RecognitionEvalResult: ...
```

**A new task implementation must supply, at minimum:**
- A `*Config` pydantic `BaseModel` (training) and a `*EvalConfig` model (eval), following the existing pattern of `train_path`/`val_path`/`arch`/`epochs`/`batch_size`/`lr`/`weight_decay`/`optimizer`/`scheduler`/`input_size`/`workers`/`amp`/`early_stop*`/`output_dir`/`device`/`pretrained`/`name`.
- A `*EvalResult` model with overall metrics + `slices: list[EvalSlice] = Field(default_factory=list)`, `sample_count`, `excluded_count`, `duration_seconds`.
- Two new methods on both Protocols (or a new sibling Protocol pair), each concrete `Local*Runner` implementation updated to match, and a "verbatim-moved" or fresh torch-touching module analogous to `detect.py`/`recog.py`, called only from behind the lazy-import boundary described in §2.
- `TrainingEvent` reuse is free — `kind: Literal["log","epoch","metric","done","error"]`, `message: str`, `progress: float | None`, `data: dict[str, object] | None` — it's task-agnostic already.

`RecognitionEvalConfig` also demonstrates the model-validator idiom used for
cross-field constraints: a `@model_validator(mode="after")` raises
`ValueError` if `slice_glyph_features=True` but `glyph_annotations_path is None`.

## 4. Glyph-feature mechanism

**Origin/decoupling.** `GlyphFeatureSet` (`protocols.py`) is deliberately a
*thin, independent* model, not a re-export of `pdomain-book-tools`'s richer
`GlyphAnnotations`
(`/workspaces/pdomain/pdomain-book-tools/pdomain_book_tools/ocr/glyph_annotations.py`,
which carries `LigatureKind` enum values, ground-truth-text invariants, etc.,
and pulls in the whole book-tools/torch dependency graph). Docstring: *"Per-word
glyph feature presence, decoupled from pdomain-book-tools... The caller
(`pdomain-ocr-trainer-spa`) derives this from pdomain-book-tools
`GlyphAnnotations`; `pdomain-ocr-training` never imports `GlyphAnnotations`
itself — that would add a heavy foundation-lib dependency edge."*

**Exact fields (`GlyphFeatureSet`, per-crop, not richer than flags):**
```python
class GlyphFeatureSet(BaseModel):
    ligatures: list[str] = []   # ligature *kind strings*, e.g. ["fi", "long_st"] — per-kind, never lumped
    long_s: bool = False
    swash: bool = False
```
It is **per-crop presence flags plus a list of ligature-kind strings** — not
positions, not counts, not spans. No richer structure (no bounding boxes, no
confidence, no per-glyph identity) crosses this boundary.

**The JSON sidecar.** A file at `RecognitionEvalConfig.glyph_annotations_path`
(`Path | None`), only consulted when `slice_glyph_features: bool = True`
(also on `RecognitionEvalConfig`). Format: a flat JSON object,
`dict[str, GlyphFeatureSet-shaped-object]`, loaded in
`_eval_backend.evaluate_recognition_impl` via
`json.loads(...)` → `{k: GlyphFeatureSet.model_validate(v) for k, v in sidecar_raw.items()}`.

**Join to validation samples.** The key is the **recognition crop id** — "the
DocTR recognition val-set label key (the per-crop filename / relative path)".
`_run_recognition_inference` threads each sample's crop id alongside its
prediction/ground-truth strings (module docstring: "issue #8 — Crop-id
threading... Keying by crop id (not by iteration index) is robust to any
filtering or reordering of the val set"). `_emit_glyph_slices` then, per
crop id: if absent from the sidecar → counted in `n_excluded` for every
feature; if present → bucketed positive/negative per feature
(`long_s`, `swash`, and one `ligature:<kind>` per distinct kind observed
anywhere in the sidecar). Produces one `EvalSlice` per feature with
`n_pos`/`n_neg`/`n_excluded`, `cer_pos`/`cer_neg`, `wer_pos`/`wer_neg`,
`delta_cer = cer_pos - cer_neg`, `delta_wer` (both `None` if either side
empty), and `low_support = n_pos < 30` (the `_LOW_SUPPORT_THRESHOLD`).

**`EvalSlice` fields** (also used, empty, by detection — detection's
`slices` list is currently always `[]`):
```python
class EvalSlice(BaseModel):
    feature: str
    n_pos: int
    n_neg: int
    n_excluded: int = 0
    cer_pos: float | None = None
    cer_neg: float | None = None
    wer_pos: float | None = None
    wer_neg: float | None = None
    delta_cer: float | None = None
    delta_wer: float | None = None
    low_support: bool = False
```

**Open question — who writes the sidecar.** Explicitly unresolved.
`pdomain-ocr-training/docs/context/intent-map.md` under "Needs owner
decision": *"Glyph sidecar writer ownership. Decide whether dataset export or
the trainer SPA writes the glyph-feature JSON sidecar. Either producer must
use basenames matching DocTR validation labels."* (Evidence cited there:
`pdomain_ocr_training/_eval_backend.py`, `tests/test_glyph_slice_emission.py`,
commits `fccc594`, `ad904c3`.) Repeated verbatim in
`docs/context/decisions.md` under "Remaining work." Confirmed by search:
no writer of this sidecar format exists in `pdomain-ocr-trainer-spa`'s
`src/` (only an unrelated hit inside a minified frontend JS bundle) — the
consumer side (`_eval_backend.py` + its test) is built, but nothing in either
repo currently produces the file.

## 5. Dataset formats

**Current, shipped format — local filesystem, DocTR-native.** Both
`pdomain-ocr-training` (`detect.py`, `recog.py`, `_eval_backend.py`,
`datasets.py`) and `pd-ocr-trainer` (`src/pd_ocr_trainer/dataset_store.py`,
duplicate copy) require each split directory to contain:
```
<split_path>/
├── images/                # image files, referenced by filename
└── labels.json            # DocTR-native label map
```
consumed directly by DocTR's `DetectionDataset`/`RecognitionDataset`
(`img_folder=".../images"`, `label_path=`/`labels_path=".../labels.json"`).
For recognition, `labels.json` is DocTR's standard flat
`{filename: ground_truth_text}` map; for detection it's DocTR's polygon/
bbox-per-class map. A SHA-256 hash of `labels.json` is taken for cache/version
identity (`val_hash = hashlib.sha256(f.read()).hexdigest()` in both
`detect.py` and `recog.py`).

**Splits and profiles.** Data is organized by named "profile" directories
under two parallel roots (env-overridable, default `<project_root>/ml-training`
and `<project_root>/ml-validation`):
```
ml-training/<profile>/{detection,recognition}/{images/,labels.json}
ml-validation/<profile>/{detection,recognition}/{images/,labels.json}
```
Verified live on disk at `pd-ocr-trainer/ml-training/all/{detection,recognition}/{images/,labels.json}`
and the `ml-validation/all/` mirror. `pdomain_ocr_training/datasets.py`
(`ExportManager`, ported "verbatim" from `pd-ocr-trainer`) owns:
`normalize_profile_name` (lowercases, dashes-for-spaces/underscores, maps
legacy `base-ocr` → canonical `all`), `iter_export_profile_dirs` (scans an
export root for any subdir containing `<task>/labels.json` for
`DATASET_TASKS = ("detection", "recognition")`), and
`get_available_model_profiles` (unions profile names from training dir,
validation dir, shared model store, and the labeler export root).

**What a new dataset needs to be trainable today:** a directory with
`images/` + a DocTR-format `labels.json`, placed under
`ml-training/<profile>/<task>/` and mirrored under `ml-validation/<profile>/<task>/`
for eval — no manifest, no card, no split file beyond the directory
boundary itself. `pdomain-ocr-trainer-spa` additionally discovers
**labeler exports** via a shared `pdomain-ops` path registry and a JSON
manifest schema `pdomain.doctr-export-manifest`
(`pdomain_ops.schemas.doctr_export.DoctrExportManifest`, in
`/workspaces/pdomain/pdomain-ops/`) — described in
`pdomain-ocr-trainer-spa/docs/architecture/labeler-import-and-freshness.md`
as "a compatibility bridge between the labeler export tree and trainer
datasets," with per-profile freshness state in
`profiles/<profile>/freshness_state.json`. This manifest bridge is optional;
the SPA "still starts when pdomain-ops or the export is unavailable."

**Planned but NOT implemented — Hugging Face dataset contract.**
`pd-ocr-trainer/docs/specs/datasets.md` (front matter: `Status: active`,
"Disposition: Approved target contract; implementation has not started")
defines three target HF dataset shapes — `recognition/v1` (HF imagefolder +
`metadata.jsonl`, columns `image`/`text`/provenance),
`detection/v1` (parquet, columns `image`/`lines` (bbox+text+words)/`size`/
provenance), and `typeface-classification/v1` (imagefolder + `metadata.jsonl`,
columns `image`/`typeface` enum, requires ≥2 distinct `typeface` values) —
plus a required dataset-card `card_data` block (`task_categories`, `tags`,
`language` BCP-47, `typeface`, `pd-ocr-shape`, `pd-ocr-source`,
`pd-ocr-recipe-sha`). `pd-ocr-trainer/docs/context/current-state.md` is
explicit: *"The Hugging Face dataset roadmap and its five detailed specs
remain unimplemented intent, not current architecture."* Do not treat this
spec as shipped — it is aspirational and cross-project (`pd-ocr-labeler` /
`pd-ocr-synth` / `pd-ocr-trainer` roles), not something a new dataset needs
to satisfy today.

## 6. Shared vs. training-specific contracts

**Genuinely shared already (pattern precedent: `pdomain-ops`):**
- The `@runtime_checkable Protocol` + separately-shipped `Local*`
  implementation idiom is already established in
  `pdomain-ops/pdomain_ops/gpu/protocols.py` (`StageDispatcher`,
  `LongJobRunner`) — `pdomain-ocr-training` explicitly copies it rather than
  inventing something new. Any future lightweight-package extraction should
  follow this precedent, likely landing in `pdomain-ops` or a sibling
  contracts package, not `pdomain-book-tools`.
- `DoctrExportManifest` (`pdomain_ops.schemas.doctr_export`) is already a
  shared, torch-free schema consumed cross-repo (labeler export ↔ trainer
  SPA). It is the existing model for "shared contract lives outside the
  domain package."
- **`GlyphFeatureSet` is the strongest candidate for extraction.** It was
  purpose-built as a deliberately narrow, torch-free re-projection of
  `pdomain-book-tools`'s `GlyphAnnotations` specifically to avoid pulling
  book-tools' torch/doctr/transformers/opencv dependency graph
  (`pdomain-book-tools/pyproject.toml` declares `torch>=2.6`, `torchaudio`,
  `torchvision`, `transformers>=4.45`, `opencv-contrib-python`,
  `python-doctr` as unconditional `dependencies`, no optional-extra
  gating). If glyph-feature exchange needs to happen between more than these
  two repos, `GlyphFeatureSet`/`EvalSlice` are the pieces to lift into a
  shared lightweight package — they're already independent of both torch and
  of book-tools' richer `GlyphAnnotations`/`LigatureKind` model.
- `TrainingEvent` is task-agnostic (`kind`/`message`/`progress`/`data`) and
  could generalize beyond OCR training with no changes.

**Training-specific — should stay in `pdomain-ocr-training`:**
- `DetectionConfig`/`RecognitionConfig`/`*EvalConfig`/`*EvalResult`: tied to
  DocTR architecture names (`db_resnet50`, `crnn_vgg16_bn`), DocTR-specific
  knobs (`rotation`, `vocab`, `input_size` semantics differing by task), and
  DocTR's on-disk `images/`+`labels.json` convention.
  `ITrainingRunner`/`IEvalRunner` themselves are hard-wired to exactly these
  two DocTR tasks (§3) — not a generic training-task abstraction yet.
- `datasets.py`'s `ExportManager`/profile-normalization/`ml-training`+
  `ml-validation` layout: bespoke to this suite's local-disk conventions,
  duplicated (not shared) between `pdomain-ocr-training` and the still-active
  `pd-ocr-trainer`.
- The planned HF dataset-shape spec (`detection/v1`, `recognition/v1`,
  `typeface-classification/v1`) is itself already meant to be cross-project
  (`pd-ocr-labeler`/`pd-ocr-synth`/`pd-ocr-trainer`) per its own "Scope:
  cross-project" line — but it's unimplemented, so there is nothing to
  extract yet.

## Key file paths referenced

- `/workspaces/pdomain/pdomain-ocr-training/pdomain_ocr_training/protocols.py`
- `/workspaces/pdomain/pdomain-ocr-training/pdomain_ocr_training/__init__.py`
- `/workspaces/pdomain/pdomain-ocr-training/pdomain_ocr_training/local_eval.py`
- `/workspaces/pdomain/pdomain-ocr-training/pdomain_ocr_training/_eval_backend.py`
- `/workspaces/pdomain/pdomain-ocr-training/pdomain_ocr_training/datasets.py`
- `/workspaces/pdomain/pdomain-ocr-training/tests/test_torch_free_import.py`
- `/workspaces/pdomain/pdomain-ocr-training/pyproject.toml`
- `/workspaces/pdomain/pdomain-ocr-training/docs/architecture/00-overview.md`
- `/workspaces/pdomain/pdomain-ocr-training/docs/context/intent-map.md`
- `/workspaces/pdomain/pdomain-ocr-training/docs/context/decisions.md`
- `/workspaces/pdomain/pd-ocr-trainer/README.md`
- `/workspaces/pdomain/pd-ocr-trainer/docs/context/current-state.md`
- `/workspaces/pdomain/pd-ocr-trainer/docs/specs/datasets.md`
- `/workspaces/pdomain/pd-ocr-trainer/src/pd_ocr_trainer/{train_detect,train_recog,dataset_store}.py`
- `/workspaces/pdomain/pd-ocr-trainer/ml-training/all/{detection,recognition}/`
- `/workspaces/pdomain/pdomain-ocr-trainer-spa/README.md`
- `/workspaces/pdomain/pdomain-ocr-trainer-spa/docs/architecture/trainer-workflows.md`
- `/workspaces/pdomain/pdomain-ocr-trainer-spa/docs/architecture/labeler-import-and-freshness.md`
- `/workspaces/pdomain/pdomain-book-tools/pyproject.toml`
- `/workspaces/pdomain/pdomain-book-tools/pdomain_book_tools/ocr/glyph_annotations.py`
- `/workspaces/pdomain/pdomain-ops/pdomain_ops/gpu/protocols.py`
- `/workspaces/pdomain/pdomain-ops/pdomain_ops/schemas/doctr_export.py`
