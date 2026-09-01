# Labeler/UI-side structural analysis

Read-only. Repos: `pd-ocr-labeler`, `pdomain-ocr-labeler-spa`,
`pdomain-ocr-simple-gui`, `pdomain-ui`. Nothing was modified.

## 1. Repo status and supersession

| Repo | Status | Role |
|---|---|---|
| `pd-ocr-labeler` | **Legacy, active-but-frozen.** README frontmatter says `status: active` but the banner reads: *"This maintained NiceGUI application is being phased out in favor of `pd-ocr-labeler-spa`. Use this repository for the supported legacy workflow..."* Depends on `pd-book-tools` (old package name, pinned to git tag `v0.9.0`, not `pdomain-book-tools`). | NiceGUI (server-rendered Quasar/websocket) labeler UI. |
| `pdomain-ocr-labeler-spa` | **Active, current.** README: *"Status (2026-05-21): Cut-over complete... legacy `pd-ocr-labeler` superseded."* Explicitly supersedes `pd-ocr-labeler`; git log shows active feature work through 2026-08 (lazy book manifests, typography review). Depends on `pdomain-book-tools==0.26.1` and `pdomain-ops`. | FastAPI + React/Vite/TS replacement for the NiceGUI labeler. Contract-first REST + SSE, single-wheel distribution (bundles built SPA). |
| `pdomain-ocr-simple-gui` | **Active, different purpose — not a labeler.** No correction/typography/ground-truth capability; drag-and-drop folder → OCR → `.txt`. Explicitly "Phase 3 reference consumer that validates `pdomain-ops`' `LocalStageDispatcher`." | Minimal OCR runner app, sibling in the suite, not part of the review chain. |
| `pdomain-ui` | **Active, shared library.** `@pdomain/pdomain-ui`, published to a private npm registry, version 0.11.0. "Every pdomain-* end-user SPA (labeler-spa, pgdp-prep, trainer-spa) imports ... instead of reimplementing." | Shared TS/React component/primitive/store library — the frontend-side extraction that has already happened. |

Confirmed pair: `pd-ocr-labeler` (superseded) → `pdomain-ocr-labeler-spa`
(supersedes it). `pdomain-ocr-simple-gui` and `pdomain-ui` are not older/newer
versions of either — separate concerns (a lightweight OCR-only app, and a
shared component library).

## 2. Contracts

### Canonical typography types — all sourced from `pdomain_book_tools.typography`

`src/pdomain_ocr_labeler_spa/api/typography.py` imports directly from
`pdomain_book_tools.typography`: `WordTypography`, `TypographyCorrection`,
`TypographySpan`, `TypographyTaxonomy`, `TypographyTaxonomyLabel`,
`ReviewState`, `LabelState`, `CorrectionDecision`, `StyleLabel`,
`PageGeometry`, `WordGeometry`, `CoordinateTransform`, `ModelRun`,
`ReplacementArtifact`, `LabelingBundle`, `CorrectionBundle`,
`TypographyReviewMetadata`, `split_graphemes`, plus version constants
`GRAPHEME_SEGMENTATION_VERSION` / `REVIEW_CONTRACT_VERSION`.

None of these are duplicated locally — the SPA imports the package's public
API and does not reach into internals (per
`docs/specs/2026-08-21-typography-review-and-training-export-design.md`).

`ReviewState`: `unreviewed | reviewed | reviewed_regular | quarantined | deferred`.
`LabelState` (per-label tri-state): `unknown | positive | negative`.
`CorrectionDecision`: `approved_edit | reviewed_regular | reject_source |
reject_alignment | unusable_image | defer | accept`
(`pdomain_book_tools/typography/review.py:38-73`, resolved via the venv at
`.venv/lib/python3.13/site-packages/pdomain_book_tools/typography/review.py`).

Taxonomy in use (`api/typography.py:60-79`): `italic, bold, small_caps,
letter_spaced, superscript, subscript, underline, font_blackletter,
font_antiqua, font_upright_in_italic, font_other_reviewed`. Only
`italic/bold/small_caps` are trainable; `underline`/`font_other_reviewed` are
audit-only; `drop_cap` is structural, handled outside the span editor.

**Locally defined** on top of the canonical types, in
`src/pdomain_ocr_labeler_spa/core/typography_review.py` — server-side
orchestration, not duplication: `TypographyBinding`, `TypographyJournalEnvelope`,
`ImportedTextBinding`, `ImportedTextValidationHead`, `ImportedTextValidationLog`,
`TypographyCorrectionLog`, `stable_word_id()`, `stable_page_id()`,
`StaleTypographyBindingError`, `StaleImportedTextValidationError`. This is the
append-only correction journal / hash-chain bookkeeping layer, appropriately
app-owned (it depends on the labeler's own persistence and lease model).

### Page/line/word/geometry — split between book-tools and locally-defined wire shapes

- `Page`, `Line`, `Word`, `Block` (paragraphs) — `pdomain_book_tools.ocr.page`
  / `.block` / `.word`. The labeler holds a live `Page` object in memory
  (`pstate.page_record.payload`) and calls its methods directly
  (`merge_lines`, `delete_paragraphs`, `finalize_page_structure`, etc. —
  cited by file:line throughout `api/words.py`, `api/lines_paragraphs.py`).
- `pdomain_ops.pages.PageRecord` — shared page-lifecycle type (rotation
  metadata etc.) imported from the suite plumbing package `pdomain-ops`, not
  book-tools, and not redefined locally. Labeler-only extension state lives
  in `PageRecord.extensions["labeler"]`, typed via
  `core/labeler_extension.py` — this namespacing is explicit so other suite
  apps don't inherit labeler concepts.
- `WordMatch`, `LineMatch`, `MatchStatus`, `BBox`, `EncodedDims`, `Selection`,
  `LineFilter`, `Project` — **locally defined** Pydantic models in
  `src/pdomain_ocr_labeler_spa/core/models.py`. `BBox` is a plain
  `{x, y, width, height}` int rectangle in source-image pixel space (not the
  book-tools `BoundingBox`, which supports normalized coordinates — see §3).
  These mirror the legacy `pd_ocr_labeler` models 1:1 (cited line numbers in
  `01-data-models.md`), i.e. this is a deliberate compatibility layer, not
  accidental duplication.
- `Corrections`/review-state at the word-match level (validated flags,
  match status) is separate from typography review state — text-match
  correctness (`WordMatch.is_validated`, `MatchStatus`) and typography review
  (`ReviewState`) are two independently-gated pipelines (see §4).

## 3. Bbox tightener / geometry correction

Lives in **`pdomain_book_tools`**, not in any of the four repos under
review — the labeler only orchestrates it.

- Algorithm: `pdomain_book_tools.ocr.image_utilities.refine_word_bbox`
  (called via `Word.refine_bbox()`, a documented back-compat wrapper — "the
  implementation lives in ... call that directly in new code";
  `pdomain_book_tools/ocr/word.py:514-530`). Tries `BoundingBox.refine`
  first, falls back to `crop_bottom`.
- `Word.expand_bbox(padding_px, page_width, page_height)` — uniform padding,
  clamps to page bounds (`word.py:532-585`).
- `Word.expand_then_refine_bbox(page_image)` — iterates expand+refine up to
  8 times until the bbox signature stabilizes (`word.py:587+`).

Orchestration in `pdomain-ocr-labeler-spa`:
`src/pdomain_ocr_labeler_spa/core/jobs/handlers/refine.py`
(`handle_refine_bboxes`), reached via `POST .../refine` and
`POST .../lines/refine-batch` (job type `refine_bboxes`,
`api/refine.py`), and via `NudgeBboxRequest.refine_after` in `api/words.py`
(manual nudge, then optionally re-refine).

- **Operates on**: the live cached `pdomain_book_tools.ocr.page.Page`'s
  `cv2_numpy_page_image` (the actual page pixels, opencv `ndarray`) and the
  target `Word.bounding_box`, scoped to `page | paragraph | line | word`.
- **Writes back**: mutates `word.bounding_box` in place on the in-memory
  `Page`; calls `page.finalize_page_structure()` to reset derived caches;
  bumps `pstate.generation`; persists the edited page content to the page
  store so refined bboxes survive a reload (`save_page_content_to_store`,
  logging a `{"type": "refine_bboxes", ...}` change record).
- Confirms the premise: **OCR detection boxes are adjusted post-recognition**,
  pixel-snapped against the source image, not just recomputed from text.

## 4. Correction / export contract

Two independent completion gates, both required for page completion
(`docs/specs/2026-08-21-typography-review-and-training-export-design.md`):
text/ground-truth review (existing `WordMatch`/`is_validated` machinery) and
typography review (`ReviewState` == `reviewed`/`reviewed_regular` for every
retained word, every `required_for_completion` label resolved to
positive/negative).

**On-disk shape leaving the labeler** (`docs/architecture/09-persistence.md`):
`UserPageEnvelope` v2.1 JSON — `schema{name,version}`, `provenance`
(who/when/app/toolchain/OCR model versions), `source` (project/page id,
image fingerprint), `payload` (`page: Page.to_dict()`, `original_page`,
`word_attributes`), `cached_images`. Written to the "labeled lane"
(`<data>/labeled-projects/<project_id>/<project_id>_<page:03d>.{png,json}`)
on Save, byte-compatible with the legacy `pd-ocr-labeler` reader/writer —
deliberately, since both apps can share a data root during transition.

**Two export paths, two consumers**:
1. **DocTR training export** — `Page.generate_doctr_detection_training_set` /
   `..._recognition_training_set` (both on `pdomain_book_tools`), filtered by
   style/component via a `WordFilter`. Output tree
   `<data>/doctr-export/<project_id>/<subfolder>/{detection,recognition}/`.
   A headless twin of the dialog ships as
   `pdomain-ocr-labeler-spa-export` (reads envelopes off disk directly, no
   server boot — same pattern legacy's `pd-ocr-labeler-export` used).
   Cross-app handoff: writes/merges `<data>/doctr-export/manifest.json`
   through `pdomain_ops.schemas.doctr_export`; a sibling "Trainer" app
   (pdomain-ocr-training / trainer-spa) is offered a "Send to Trainer"
   action when installed.
2. **Typography correction bundle export** — `CorrectionBundle` /
   `LabelingBundle` (book-tools types), produced by
   `export_typography_correction_bundle` in `api/typography.py`. Strict
   validation before export: every selected word's latest correction must
   have an `accepted` decision (`accept|approved_edit|reviewed_regular`), its
   replacement `review_state` in `{reviewed, reviewed_regular}`, and every
   required-for-completion label resolved (not `unknown`) — otherwise `409`.
   Also enforces hash-chain integrity (`base_page_sha256`,
   `base_image_sha256`, `page_head_sha256`, `base_text_sha256` must match the
   binding the review started from) — a stale-head reviewer submission is
   rejected rather than silently accepted.

## 5. What a headless (CLI/LLM) labeler would need

**Already exists and is reusable as-is:**
- A typed REST API (FastAPI, OpenAPI-generated) is the actual backend
  contract — the frontend is not the only client. `GET
  /api/typography/head`, `GET .../typography/review`, `GET
  .../typography/worklist`, `POST .../typography/correction` (append-only
  journal), `POST .../typography/correction-bundles/export` are all plain
  HTTP+JSON, independent of any browser.
- `TypographyWorklistResponse` is explicitly documented as "**geometry-free**
  review input" — per word: `text`, `graphemes[]`, `source_review_state`,
  `source_label_states{}`, `source_spans[]`, `warnings[]`,
  `current_correction`, and derived flags (`reviewed`,
  `typography_reviewed`, `text_reviewed`). This is close to exactly the
  shape an LLM reviewer needs to *decide* — it just doesn't carry geometry.
- `PagePayload` (regular page-load route) separately carries `image_url`,
  `overlay_urls`, and per-line `WordMatch.bbox` — so a CLI client can fetch
  the page image once and crop word/line context itself (PIL-level, no Konva
  needed) using the bboxes it already has from the page payload.
- The correction submission contract (`TypographyCorrectionSubmission`) is
  exactly the "record a decision" surface: `expected_head` (optimistic
  concurrency), `correction_id`, `taxonomy_version`/`taxonomy_hash`,
  `decision` (`CorrectionDecision`), optional `replacement: WordTypography`
  with spans/label_states, `metadata`. An LLM reviewer could emit this
  directly.
- A headless *export* CLI already exists
  (`pdomain-ocr-labeler-spa-export`) — precedent for "console script that
  bypasses the server," though it only handles export, not review.
- The `pd-ocr-labeler-driver` "driver agent" is referenced extensively in
  docs (`docs/architecture/13-driver-contract.md`,
  `docs/specs/behavior/component-driver-contract.md`) as the thing that
  operates the labeler for automation today — **but no such agent file or
  repo exists anywhere on this filesystem.** It's documented contract, not a
  shipped artifact, and — per the driver-contract doc — it works by driving
  the browser via Playwright against stable `data-testid`s, not by calling
  the REST API. So today's "automation" story is UI automation, not a
  headless client, even though the REST surface would support one.

**Tied to the GUI and would need rebuilding:**
- The two-view review surface itself (high-res word crop + short-line
  context + adjacent words + visible baselines/x-heights/char boxes,
  `docs/specs/2026-08-21-...md` "Review uses surrounding context") is a
  React/Konva rendering concern (`frontend/src/components/PageImageCanvas.tsx`,
  `docs/architecture/21-konva-renderer.md`). A CLI/LLM reviewer needs an
  equivalent — generate the crop+context images itself (straightforward: PIL
  crop from the already-available page image + bbox, no browser needed) or
  describe the surrounding text/geometry to the model in text form.
- Suggestion accept/edit UI, span drag-select, generic span-boundary
  adjustment are explicitly **not yet implemented even in the SPA**
  ("Suggestion acceptance/editing ... are not yet implemented"), so there's
  no existing suggestion-review flow to copy for the CLI case either — the
  taxonomy/label-state decision loop is the only piece that's actually live.
- `bind_page_labeling_lease` (a per-page lock/lease dependency wired into
  every mutating typography route) assumes a single interactive session per
  page; a CLI reviewer would need to acquire/release the same lease
  correctly, which is API-level but easy to get wrong non-interactively.

**Net assessment**: the *data model and API contract* for a CLI/LLM
typography reviewer already exist and are close to sufficient — worklist,
correction submission, hash-chain validation, and export are all plain
REST/JSON backed by pure-Python types. What's missing is (a) a client that
calls this API instead of a browser (nothing does today — the referenced
driver agent isn't present in the workspace and drives the DOM anyway), and
(b) the presentation layer that turns bbox+image+neighbour text into
something a model can review — pure image-cropping/prompt-assembly work, not
something requiring the React app.

## 6. Extraction candidates vs. genuine application code

**Good extraction candidates (already lightweight, already reused, or both):**
- `pdomain_book_tools.typography` submodule: pure Pydantic/StrEnum data
  model + grapheme segmentation (`WordTypography`, `TypographyCorrection`,
  `TypographySpan`, `TypographyTaxonomy`, `ReviewState`, `LabelState`,
  `CorrectionDecision`, `PageGeometry`/`WordGeometry`/`CoordinateTransform`,
  `LabelingBundle`/`CorrectionBundle`). Grepping the submodule found no
  direct `torch`/`cv2`/`doctr` imports. But the package's own `__init__.py`
  docstring warns: *"Importing this package eagerly imports the OCR / layout
  / geometry stack (cv2, numpy, DocTR, transformers). If you need a
  lightweight import surface... import the specific submodule directly —
  but be aware that even that path imports cv2 today."* Measured: `import
  pdomain_book_tools.typography` alone pulls in `cv2` and `numpy` (not
  torch/doctr in this run) and takes ~1s, confirming the premise in the task
  context — this is the strongest concrete case in these four repos for a
  standalone lightweight package (typography contract types, no image
  processing needed to define or validate them).
- `pdomain_ops.schemas.doctr_export` (the export manifest schema shared
  between labeler-spa and Trainer) and `pdomain_ops.pages.PageRecord` —
  already extracted into `pdomain-ops`, working as designed as a
  suite-plumbing package that multiple apps import without pulling in OCR.
- `@pdomain/pdomain-ui` on the frontend side is the equivalent extraction
  already done for React components (canvas, worklist, shell primitives,
  icons, store factories) — labeler-spa, simple-gui, and the (not-checked)
  trainer-spa/pgdp-prep all import from it instead of reimplementing.

**Genuinely application code — should stay put:**
- `core/typography_review.py`'s journal/lease/hash-chain machinery
  (`TypographyCorrectionLog`, `ImportedTextValidationLog`, stable-id
  derivation) — this is labeler-specific event-sourcing over the canonical
  types, tightly coupled to this app's persistence and concurrency model.
- `core/models.py`'s `WordMatch`/`LineMatch`/`BBox`/`Selection` — these
  exist specifically to stay byte-compatible with the legacy NiceGUI
  labeler's on-disk format; moving them to a shared package would decouple
  them from that compatibility requirement they exist to serve.
- The Konva/React rendering layer, job-runner wiring, and FastAPI routers
  themselves — UI/orchestration, not reusable contract.
- `pdomain-ocr-simple-gui` as a whole is small, self-contained, and not
  duplicating anything worth factoring out further; it's already a "reference
  consumer" of the shared pieces (`pdomain-book-tools`, `pdomain-ops`,
  `@pdomain/pdomain-ui`), which is the intended role.
