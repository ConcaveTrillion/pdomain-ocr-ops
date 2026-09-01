# Cross-repo duplication hunt — /workspaces/pdomain

Read-only survey of 18 repos. `ml-training/` and `ml-validation/` contain only
image data (`all/detection`, `all/recognition`), no source — excluded below.
Ranked by pain (drift severity x number of repos affected), worst first.

## 1. `pd-ocr-labeler` runs on a frozen fork of the whole shared library

**The single biggest duplication in the workspace, and it's not one concept —
it's an entire package.**

`pd-ocr-labeler/pyproject.toml` depends on `pd-book-tools>=0.1.0` (resolves to
v0.9.0), pulled from a *separate* GitHub repo
(`ConcaveTrillion/pd-book-tools`), not this workspace's `pdomain-book-tools`.
Confirmed installed at `/cache/uv/archive-v0/ObL8t1jLChJpz-f2/pd_book_tools`
(73 `.py` files). Its module tree (`geometry/`, `hf/`, `image_processing/`,
`layout/`, `ocr/`, `pgdp/`, `utility/`) mirrors `pdomain_book_tools` almost
exactly — it's the pre-rename predecessor. `pdomain_book_tools` has since
grown `matching/`, `schemas/`, `geometry_correction/`, `data/`, and
`typography/` submodules that `pd_book_tools` never got.

Every file under `pd_ocr_labeler/` (models, operations, state, views —
`import pd_book_tools...`, never `pdomain_book_tools`) runs against this
frozen snapshot: `Page`, `Word`, `Block`, `Document`, confidence handling,
review metadata, doctr parsing — all independently frozen at whatever
`pdomain_book_tools.ocr.*` looked like before the rename. One concrete
symptom: `pd-ocr-labeler/pd_ocr_labeler/models/word_match_model.py` and
`pdomain-ocr-labeler-spa/src/pdomain_ocr_labeler_spa/core/models.py` both
independently define an identical 5-value `MatchStatus` enum
(`exact/fuzzy/mismatch/unmatched_ocr/unmatched_gt`) because the labeler-spa
rewrite couldn't import the type from either package.

**Every other repo in the workspace correctly depends on `pdomain-book-tools`**
(`pdomain-source-data`, `pd-ocr-trainer`, `pdomain-ocr-cli`,
`pdomain-ocr-labeler-spa`, `pdomain-ocr-trainer-spa`, `pdomain-prep-for-pgdp`,
`pdomain-ops`) — `pd-ocr-labeler` is the sole holdout, apparently superseded
by `pdomain-ocr-labeler-spa` rather than migrated.

**Keep:** `pdomain-book-tools`. **Fix:** this isn't a "shared package"
problem — it's a "finish decommissioning `pd-ocr-labeler`" problem (or
migrate it onto `pdomain-book-tools` if it's still live).

## 2. `canonical_json_bytes` — same name, same intent, different bytes (verified live bug)

`pdomain-source-data/pdomain_source_data/hashing.py:76-84` and
`pdomain-book-tools/pdomain_book_tools/typography/review.py:76-84` each
define a function named `canonical_json_bytes(value) -> bytes` meant to
serialize JSON deterministically for hashing/signing. Verified side by side:

- book-tools: `json.dumps(value, allow_nan=False, ensure_ascii=False,
  separators=(",", ":"), sort_keys=True).encode("utf-8")` — **no trailing
  newline**.
- source-data: identical `json.dumps(...)` call, then
  `f"{encoded}\n".encode()` — **trailing `\n` appended**.

Same logical JSON in, different bytes out, different SHA-256 digest out. If a
record ever gets canonicalized by one implementation and compared against a
hash computed by the other over equivalent content, the digests silently
disagree. This is the one finding in the hunt that's an actual correctness
bug waiting to happen, not just style/shape drift — worth fixing before the
others on this list.

## 3. Bounding-box wire model — reinvented 3 times, 3 different shapes

- `pdomain-book-tools/pdomain_book_tools/geometry/bounding_box.py` (879 lines)
  + `point.py` (257 lines) — canonical, Shapely-backed `BoundingBox(top_left,
  bottom_right, is_normalized)` dataclass with area/overlap/split/union math
  and pixel-vs-normalized tracking. Correctly reused by
  `pdomain-source-data/pdomain_source_data/geometry/records.py` and
  `pdomain_book_tools/ocr/word.py` — composition, not duplication.
- `pdomain-prep-for-pgdp/src/pdomain_prep_for_pgdp/core/models.py:742` —
  `class BoundingBox(ApiModel)`: `left, top, width, height` (plain ints, no
  methods).
- `pdomain-ocr-labeler-spa/src/pdomain_ocr_labeler_spa/core/models.py:72` —
  `class BBox(BaseModel)`: `x, y, width, height` (plain ints).
- `pdomain-ocr-simple-gui/src/pdomain_ocr_simple_gui/routes/words.py:34` —
  `class Bbox(BaseModel)`: `x, y, w, h` (floats, normalized 0–1).

Three services, three field-naming conventions (`left/top` vs `x/y`,
`width/height` vs `w/h`) and three unit conventions (pixel-int, pixel-int,
normalized-float) — none built on `pdomain_book_tools.geometry.BoundingBox`.
A bbox validity fix (clamping, NaN-rejection) has to land three times and
plainly hasn't been kept in sync. The TS mirrors of these
(`pdomain-ocr-labeler-spa/frontend/src/lib/coords.ts` — `{x,y,width,height}`,
generated-schema-typed) are thin and self-consistent with their own backend,
not a new problem — but note `pdomain-ui/src/canvas/types.ts` defines yet a
*fourth* JS-side shape, `PageBBox {top_left, bottom_right}` (matching
`pdomain_book_tools.Word.bounding_box`'s corner convention), so the two React
frontends in this workspace disagree on bbox representation at the type
level (corner-pair vs xywh).

**Keep:** `pdomain_book_tools.geometry.BoundingBox` as the source of truth.
**Fix:** one shared pydantic wire type (or a serializer built on it) used by
all three API layers.

## 4. `pdomain-ocr-synth` reimplements PGDP F2 parsing from scratch

`pdomain-ocr-synth/src/pdomain_ocr_synth/pgdp/f2.py` (248 lines) parses the
same PGDP "F2" JSON block-control format (`/* */` local blocks, `/# #/`
continued blocks) as `pdomain-book-tools/pdomain_book_tools/pgdp/f2/`
(`parser.py` 490 + `offsets.py` + `tokens.py` + `project_rules.py` +
`warnings.py`, 2118 lines total) — but independently, with its own
`_BlockKind`/`_Control` enums and no shared types. `pdomain-ocr-synth` does
not depend on `pdomain-book-tools` at all (`pyproject.toml` deps: pydantic,
pyyaml, httpx, beautifulsoup4, freetype-py, uharfbuzz, pillow, numpy — no
`pdomain-book-tools`), so this can't be an oversight of a thin adapter; it's
a from-scratch second parser for the same wire format. Book-tools' version is
far more complete: it produces a full `TypographyPageRecord` with
`StyleLabel`, `Grapheme` spans, confidence tiers, and warning-blocks-training
flags; ocr-synth's version stops at raw block/control structure for its own
alignment pipeline.

This is directly actionable for this repo (`pdomain-ocr-synth`): either the
248-line F2 reader should be replaced with a thin adapter over
`pdomain_book_tools.pgdp.f2`, or the two must be reconciled so a PGDP markup
change doesn't silently diverge between the labeler pipeline and the synth
corpus pipeline.

## 5. Content-hashing / directory-manifest digest — 2 real implementations, converging job

- `pdomain-source-data/pdomain_source_data/hashing.py` (394 lines) — the
  serious one: race-resistant, fd-based (`os.open` with `O_NOFOLLOW`,
  before/after `fstat` snapshots) `sha256_file`/`sha256_directory`/
  `read_file_snapshot`, frame-length-prefixed hashing so renames change the
  digest. Built for provenance-grade manifests where a TOCTOU race must be
  provably impossible.
- `pdomain-ocr-synth/src/pdomain_ocr_synth/publish/content_sha.py` (332
  lines) — `compute_content_sha`: walks a directory with `Path.rglob`, hashes
  each file with plain `hashlib.sha256`, joins sorted
  `"<relpath>\n<file_sha>\n"` lines into one top digest. No race protection,
  different digest construction (line-joined vs length-framed), tightly
  coupled to HF-staging README front-matter idempotency.
- `pdomain-ops/pdomain_ops/blob_store.py` — simple single-blob
  `sha256(data).hexdigest()` content-addressed store; different scope
  (single-blob store, not directory digest) — legitimate, not counted as a
  duplicate of the above two.

Both #1 and #2 solve "produce a deterministic content digest over a
directory tree for idempotency/provenance," with genuinely different digest
algorithms — mixing them up (e.g. copy-pasting one repo's digest into the
other's manifest) would silently produce incompatible hashes. Not
attached to the biggest pain source in this list, but ~700 lines that could
collapse to one race-safe utility with two call conventions (streaming
digest vs directory digest).

## 6. Alignment / fuzzy-matching — one canonical engine, two other approaches beside it

- `pdomain-book-tools/pdomain_book_tools/matching/engine.py` (1136 lines) —
  the modern engine: "bounded deterministic matching over immutable physical
  token documents," a custom grapheme-level dynamic program
  (`_grapheme_alignment_operations`, monotonic-path retention), quarantine
  reasons, continuation references. This is the intended canonical aligner.
- `pdomain-book-tools/pdomain_book_tools/ocr/ground_truth_matching.py` (1297
  lines) and `matching/legacy_projection.py` (437 lines) still use
  `difflib.SequenceMatcher` — documented as an "opt-in compatibility
  projection" from the new match graph back to the legacy OCR page shape, so
  this is an acknowledged, in-progress migration, not silent drift.
- `pdomain-source-data/pdomain_source_data/matching/page_align.py` (359
  lines) — a **third**, independent aligner: also `difflib.SequenceMatcher`
  based (`SequenceMatcher(...).ratio()` similarity), reuses
  `pdomain_book_tools.typography.normalization.build_comparison_view` for
  text prep but does not call `matching.engine`'s DP aligner. It solves a
  different granularity (whole-page/segment global alignment vs
  `engine.py`'s token-level graph) but picked the *legacy* algorithm pattern
  rather than the intended-canonical one, so a future engine.py improvement
  (e.g. a better tie-break rule) won't propagate here.
- `pdomain-ocr-synth/src/pdomain_ocr_synth/pgdp/alignment_dp.py` (751 lines)
  — a fourth aligner, but for a distinct problem (aligning PGDP source lines
  to *scanned-image* line candidates by geometry/features, not text-to-text)
  — legitimate, not a duplicate.

**Keep:** `matching/engine.py`'s DP approach as canonical for text-to-text
alignment. **Fix:** either finish retiring the `SequenceMatcher` paths in
book-tools itself, or explicitly justify why `page_align.py` didn't build on
`engine.py`.

## 7. Style/typography vocabulary — 3–4 spellings of the same enum

- `pdomain-book-tools/pdomain_book_tools/typography/labels.py` — `StyleLabel`
  enum: `italic`, `bold`, `small_caps` (underscore) — canonical interchange
  contract.
- `pdomain-book-tools/pdomain_book_tools/ocr/label_normalization.py` —
  separate `ALLOWED_TEXT_STYLE_LABELS` set: `"small caps"` (space),
  `"italics"` (not `"italic"`), `"blackletter"` — a *second* canonical
  vocabulary inside the same package, unreconciled with `StyleLabel`.
- `pdomain-ocr-trainer-spa/src/pdomain_ocr_trainer_spa/core/enums.py:35-44` —
  `TypefaceEnum`: `italic`, `smallcaps` (no separator, a third spelling),
  doesn't import `StyleLabel` — cross-repo duplication, deliberately
  redefined per its own docstring reference to a spec, actively drifting.
- `pdomain-source-data/pdomain_source_data/tasks/typography/css_styles.py`
  (370 lines) — a real CSS-cascade engine (specificity, `!important`,
  inheritance) producing a fourth informal spelling (`italic`/`normal`/
  `oblique`, `small-caps`/`normal`) as *evidence* feeding into `StyleLabel` —
  legitimately a different job (deriving labels from markup vs storing
  them), not itself duplicative, but one more vocabulary variant to keep
  mapped correctly.

**Keep:** `StyleLabel`. **Fix:** collapse `ALLOWED_TEXT_STYLE_LABELS` and
`TypefaceEnum` into imports/mappings onto it — cheap, contained.

## 8. Review / correction state — 3 non-overlapping models, 2 in the same package

1. `pdomain_book_tools/ocr/review.py` (49 lines) — minimal
   `ReviewMetadata(validated: bool)`.
2. `pdomain_book_tools/typography/review.py` — richer `ReviewState` StrEnum
   (`UNREVIEWED/REVIEWED/REVIEWED_REGULAR/QUARANTINED/DEFERRED`) +
   `ReviewDecision`/`CorrectionDecision`/`TypographyReviewMetadata`. Two
   "review" vocabularies (bool vs lifecycle enum) coexist in one package;
   `ocr/review.py`'s own docstring flags this as a planned-but-unexecuted
   consolidation once a proofreader-app spec lands — acknowledged, not
   silent drift.
3. `pdomain-ocr-synth/src/pdomain_ocr_synth/pgdp/alignment_review.py` (682
   lines) — `ReviewCategory`/`ReviewGateResult` for PGDP alignment-quality
   gating. Different domain (machine gate, not human review), collides only
   on the word "review" — not duplication.

Provenance: `pdomain_book_tools/ocr/provenance.py` (141 lines,
`OCRProvenance`) vs `pdomain-ops/pdomain_ops/pages/provenance.py` (62 lines,
`ProvenanceGraph`/`ProvenanceNode`, a full pipeline DAG) — `document.py` has
active TODOs retiring the book-tools copy in favor of the ops DAG; a known,
in-flight migration, not a fresh problem.

## 9. Doctr-result parsing — one canonical converter, one deliberate re-parse

`pdomain_book_tools.ocr.document.Document.from_doctr_result` is the single
canonical doctr-output converter; `pdomain-ops/pdomain_ops/gpu/doctr_batch.py`
(205 lines) is a clean thin adapter around it. The one exception:
`pdomain-source-data/pdomain_source_data/geometry/doctr_recognizer.py` (239
lines) hand-writes its own `_DoctrWord`/`_DoctrLine`/`_DoctrBlock`
TypedDicts and a `_words_from_result` flattener instead of calling
`from_doctr_result`, feeding its own `RecognizedWord` model rather than
book-tools' `Word`/`OcrTokenRef`. The module docstring says this is
deliberate (a "silver tier" pre-alignment record, distinct on purpose from
the reviewed `OcrTokenRef`), so it's documented divergence — but it's still
a second doctr-parsing implementation that has to be hand-kept in sync if
doctr's `.export()` shape ever changes.

## 10. Small same-package duplication and one more god object

- `pdomain_book_tools/ocr/character.py` copy-pastes `_PointDict`/
  `_BoundingBoxDict` TypedDicts that already exist in `geometry/bounding_box.py`
  — trivial, same-package, easy fix.
- `pdomain_book_tools/ocr/reorganize_page_utils.py` — **4234 lines**, mixes
  five unrelated jobs (per the agent that found it) — a second, even larger
  split candidate alongside `page.py` (3906 lines) in the same subpackage.
- `pdomain-source-data/geometry/records.py`'s `PageGeometry`/`RecognizerInfo`
  vs. `pdomain_book_tools.typography.exchange`'s `PageGeometry`/`ModelRun`:
  confirmed as intentionally distinct pipeline stages (unreviewed batch vs.
  reviewed portable-bundle geometry) rather than accidental duplication, but
  the *reused class name* `PageGeometry` for two structurally different
  models, and the unlinked `RecognizerInfo`/`ModelRun` near-overlap, is a
  naming hazard worth a rename even though the logic itself isn't
  duplicated.

## 11. Minor / one-off duplication

- **Grapheme segmentation**: canonical `split_graphemes()` in
  `pdomain_book_tools/typography/spans.py` is correctly reused everywhere
  except `pdomain_book_tools/pgdp/f2/tokens.py:155`, which reimplements
  `regex.findall(r"\X", ...)` inline in a file that already imports other
  symbols from `spans` — trivial, same-package, one-line fix.
- **Text normalization** (dash/quote/diacritic tables) is genuinely
  single-sourced in `typography/normalization.py` — no duplicate found.
  `pdomain-ocr-synth/text_transforms/builtins.py`'s NFC/whitespace helpers
  serve a different job (synthetic corruption/augmentation, not
  ground-truth comparison) and are not duplication.
- **Image crop**: `pdomain-prep-for-pgdp/src/pdomain_prep_for_pgdp/core/pipeline/crop_for_ocr.py`
  (90 lines, raw numpy/cv2 slicing on PNG bytes) reimplements
  rectangle-cropping instead of calling
  `pdomain_book_tools/image_processing/cv2_processing/crop.py`'s
  `crop_to_rectangle`/`crop_edges` (121 lines). Small, low pain — the
  pipeline stage works on raw PNG bytes rather than book-tools' image
  wrapper, so a straight swap isn't free, but worth a look.
- **"Manifest" name reuse**: `book_manifest.py`, `splits/manifest.py`,
  `book_labeling_manifest.py`, doctr-export manifest, etc. — each is a
  distinct domain schema (not a shared generic manifest type reimplemented
  several times); this is naming-convention reuse, not logic duplication.

## God-object flag (opposite problem)

Two, not one, both in `pdomain_book_tools/ocr/`:

- `page.py` — **3906 lines**: doctr-result ingestion, review-state
  management, cv2-based rendering/drawing, ground-truth matching
  orchestration, and ID generation all in one module.
- `reorganize_page_utils.py` — **4234 lines**, mixing five unrelated jobs
  (see item 10 above).

Neither is duplicated elsewhere; both are strong split candidates on their
own merits, independent of the duplication hunt.

## What I'd consolidate first

1. Fix the `canonical_json_bytes` byte mismatch (item 2) — it's a live
   correctness bug, not just drift, and the fix is a one-line change in
   whichever side is wrong.
2. Decide `pd-ocr-labeler`'s fate (migrate off `pd-book-tools` onto
   `pdomain-book-tools`, or finish retiring it) — this single decision
   eliminates the largest and riskiest duplication in the workspace.
3. Bounding-box wire model: one shared pydantic type for
   `pdomain-prep-for-pgdp`, `pdomain-ocr-labeler-spa`, and
   `pdomain-ocr-simple-gui` to stop hand-rolling three incompatible shapes.
4. `pdomain-ocr-synth`'s standalone F2 parser — reconcile with
   `pdomain_book_tools.pgdp.f2` (directly actionable in this repo).
5. `StyleLabel` vocabulary sprawl (`ALLOWED_TEXT_STYLE_LABELS`,
   `TypefaceEnum`) — cheap, contained cleanup.
5. Content-hash/directory-digest duplication (`pdomain-source-data` vs
   `pdomain-ocr-synth`) — lower urgency, but ~700 lines of duplicate
   crypto-adjacent code worth a shared utility.
