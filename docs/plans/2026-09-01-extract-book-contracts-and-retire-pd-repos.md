---
Status: draft
Owner: CT
Created: 2026-09-01
Last verified: 2026-09-02
Kind: plan
---

# Extract Book Contracts and Retire the pd- Repos

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the light third of `pdomain-book-tools` into a package anything can depend on, and retire the two superseded `pd-` repositories.

**Architecture:** A new `pdomain-book-contracts` package holds the contracts, `pdomain-book-tools` keeps the engine and depends on it one way.

**Tech Stack:** Python `>=3.11,<3.14`, Pydantic v2, regex, shapely, pytest, Ruff, basedpyright, Docgraph, uv.

---

This plan does not authorize implementation. Begin each task only after explicit approval.

## Agent Index

- **Kind:** plan
- **Status:** draft
- **Owner:** CT
- **Last verified:** 2026-09-02
- **Read when:** extracting shared contracts, retiring the pd- repositories, or changing what depends on `pdomain-book-tools`.
- **Search terms:** book contracts, package extraction, pd-ocr-labeler retirement, import weight, canonical json bytes.

## Goal

Make the shared contracts usable without an imaging stack, and remove the two
repositories that fork or duplicate them.

Today a consumer that wants one pure-Python class pays for cv2, numpy and
shapely. One repository works around that by loading a source file from an
absolute path. Another forked the whole package and froze. A third rewrote the
parser rather than depend on it. Each is a symptom of the same cause.

## Architecture

`pdomain-book-contracts` holds the value types, contracts, and pure algorithms:
typography, matching, the box and point types, and the PGDP readers. Its
dependency set is pydantic, pydantic-core, shapely and regex.

`pdomain-book-tools` keeps everything that needs cv2, numpy, torch or doctr:
the OCR engine, image processing, geometry correction, the bounding-box
tightener, layout detection, and the Hugging Face helpers. It depends on the
contracts package and re-exports from it, so existing imports keep working.

Nothing depends on the contracts package in the other direction.

## Tech Stack

Python `>=3.11,<3.14` for both packages. Pydantic v2, pydantic-core, shapely
and regex for the contracts package. The existing heavy stack stays with
`pdomain-book-tools`. Tests with pytest, gates with Ruff and basedpyright,
documentation under Docgraph, packaging with uv.

## Global Constraints

- Do not implement, move files, retire a repository, delete data, or commit
  without explicit owner approval.
- Preserve unrelated working-tree changes. `pdomain-prep-for-pgdp` has
  uncommitted work; leave it alone.
- No behaviour change. This plan moves code and fixes two defects. It does not
  redesign a contract.
- Every task runs its repository's own gate before its checkpoint.
- Never combine changes to two repositories in one commit.

## What the evidence says

Six independent surveys of all eighteen workspace repositories produced the
figures below. The raw findings are in
`docs/research/evidence/2026-09-01-library-structure/`.

Roughly a third of `pdomain-book-tools` is already light. 13,032 lines across
six cohesive seams need only pydantic, pydantic-core, shapely and regex. The
remaining 26,061 lines genuinely need cv2, numpy or torch.

| Seam | Files | Lines |
| --- | --- | ---: |
| Contracts core | `typography/*`, `matching/*`, `geometry/{point,bounding_box}.py`, `ocr/ground_truth_matching_helpers/*`, `schemas/_helpers.py` | 9,328 |
| PGDP | `pgdp/pgdp_results.py`, `pgdp/f2/*` | 2,118 |
| OCR value types | `ocr/{blob_protocol,character,label_normalization,glyph_annotations,provenance,review,gt_orphans,text_normalize,__init__}.py` | 922 |
| Layout contracts | `layout/{types,geometry}.py` | 457 |
| Licensing and miscellaneous | `licenses.py`, `utility/timing.py` | 182 |

Each row was measured with `wc -l` over exactly the files named. The contracts
core total only reconciles when `ocr/ground_truth_matching_helpers/` is
included, which is why Task 4 moves it.

The weight is not torch. Torch and doctr are already lazy. Importing one
pure-Python class pulls in cv2, numpy and shapely and costs roughly 0.3 seconds,
because the root `__init__.py` eagerly re-exports `Page`, `Word`, `Block` and
`PGDPResults`. A re-export shim therefore fixes nothing. The files must move
and the root must stop importing the heavy chain.

Version discipline is already broken, so coordinating a bump is not a new cost.
One repository runs a frozen fork, five are lockfile-pinned at 0.21.0 while two
pin 0.26.1, one floats on a git commit, and one declares no dependency at all.

## Task 1: Fix the two defects that block a safe move

**Files:**

- Edit: `/workspaces/pdomain/pdomain-source-data/pdomain_source_data/hashing.py`
- Edit: `/workspaces/pdomain/pdomain-pgdp-api-client/tests/test_booktools_compat.py`

- [ ] **Step 1: Reconcile `canonical_json_bytes`**

Two implementations disagree. `pdomain_book_tools/typography/review.py` returns
`{"a":1,"b":2}`. `pdomain_source_data/hashing.py` returns the same with a
trailing newline. Same content, different digest.

The book-tools form wins: no trailing newline. Framing belongs to whatever
writes the bytes, not to the encoder, and that copy is the one moving into the
shared package. Make both call one implementation and add a test asserting the
bytes match across packages.

Source-data callers that relied on the newline must add it themselves. One
already does the opposite and appends a second newline, which produced a broken
JSON Lines file, so check every call site rather than assuming.

- [ ] **Step 2: Inventory the digests the change invalidates**

Any stored digest computed with the losing form becomes invalid. Search the
manifests, content-addressed directories, and test fixtures under
`/workspaces/pdomain-data/` and each repository for stored digest fields, and
write the list of artefacts needing a rebuild before changing either
implementation.

Run: `cd /workspaces/pdomain/pdomain-source-data && make ci`

Expected: source-data's gate passes with the reconciled implementation, and an
inventory file lists every artefact to rebuild. Rollback reverts one edit.

- [ ] **Step 3: Make the compatibility test fail rather than skip**

`test_booktools_compat.py` loads `pgdp_results.py` from a hard-coded absolute
path and calls `pytest.skip` when the file is missing or the spec fails to
load. Its own docstring calls it the most important test in the repository, and
it passes green when the file is absent. Replace both skips with failures, so
moving the file is caught.

Run: `cd /workspaces/pdomain/pdomain-pgdp-api-client && make ci`

Expected: the compat test fails loudly if book-tools is absent. Rollback
reverts two small edits; nothing has moved yet.

## Task 2: Rescue the training data, then retire the pd- repositories

**Depends on:** nothing. Can run in parallel with Task 1.

- [ ] **Step 1: Move the tracked datasets to a data root**

`pd-ocr-trainer` has 21,375 tracked files of training data committed into git:
98 MB under `ml-training/all/` and 13 MB under `ml-validation/all/`, split into
detection and recognition. Copy them to `/workspaces/pdomain-data/`, verify by
content hash, and only then remove them from the repository.

- [ ] **Step 2: Write a manifest recording what the data is and is not**

The layout is current. `pdomain-ocr-training` reads exactly this shape today.
What is dated is everything around it: no provenance beyond `img_hash`, no
confidence tier, no split manifest, no typography labels, and recognition crops
whose pixel coordinates are encoded in the filename. The detection set has 91
images against 21,282 recognition crops, so the two halves were probably not
generated together. Record all of that, so the data is not later mistaken for a
current, coherent set.

- [ ] **Step 3: Retire both repositories**

`pdomain-ocr-labeler-spa` supersedes `pd-ocr-labeler`, and
`pdomain-ocr-training` supersedes `pd-ocr-trainer`. Both last committed on
2026-08-08.

No repository imports either package, but four reference them, and two of
those references are load-bearing.

`pdomain-ocr-synth/src/pdomain_ocr_synth/output/recognition.py` names
`pd-ocr-trainer/dataset_store.py` as "the actual API contract" for the layout it
writes. `pdomain-ocr-labeler-spa/src/pdomain_ocr_labeler_spa/core/hf_probe.py`
names `pd_ocr_labeler/operations/ocr/model_selection_operations.py`, lines 169
to 205, as its source of truth. Both cite code that is about to disappear, so
each needs the behaviour it depends on captured before the source goes.

`pdomain-ocr-synth` also references `pd-ocr-trainer` across seventeen files
including its `README.md`, its `CLAUDE.md` instruction to confirm the output
contract from `../pd-ocr-trainer/`, `recipes/gaelic.yaml`, several specs and
plans, and a live cross-project test at
`tests/integration/test_trainer_dataset_contract.py`. Lower-stakes mentions also
sit in `pdomain-ocr-training/CLAUDE.md` and `pdomain-ops/docs/context/decisions.md`.

That test locks the synthetic writer's output against DocTR's own
`RecognitionDataset` and `DetectionDataset` readers, not against
`pd-ocr-trainer` code, so the contract survives the retirement. Repoint every
reference at `pdomain-ocr-training` and confirm the test still passes before
archiving anything.

Mark both repositories retired in place first, with a notice naming the
superseding repository, and stop work in them. Leave them readable until the two
load-bearing references are repointed and the behaviour they cite is captured
elsewhere. Move them out of the workspace only after that.

Follow the `doc-retirer` route for their documentation and record the
supersession.

Expected: two repositories archived, their data preserved and manifested, and
`pd-book-tools` no longer referenced by anything. Rollback restores from the
archive; the data copy is independent and stays.

## Task 3: Create the contracts package

**Depends on:** Task 1.

- [ ] **Step 1: Create the package with its gate**

New repository `pdomain-book-contracts`, Python `>=3.11,<3.14`, dependencies
pydantic, pydantic-core, shapely and regex only. Add the standard Makefile
targets, Ruff and basedpyright configuration, and Docgraph context to match its
siblings.

- [ ] **Step 2: Add a test that the package stays light**

Assert in a subprocess, with a meta-path blocker hiding cv2, numpy, torch and
doctr, that importing the package succeeds. `pdomain-ocr-training` already does
exactly this in `tests/test_torch_free_import.py`; copy that pattern rather
than inventing one.

Run: `cd /workspaces/pdomain/pdomain-book-contracts && make ci`

Expected: an empty package whose gate passes and whose lightness is enforced by
a test. Rollback deletes the repository.

## Task 4: Move the contracts, lowest layer first

**Depends on:** Task 3.

Move in dependency order so the package is never broken between steps. After
each step, `pdomain-book-tools` re-exports the moved names from their old
locations and depends on the new package.

Module paths are reorganised as part of the move rather than left for a later
pass. That removes the plain diff as a safety net, so each step lands as two
commits: first the files moved verbatim, then the reorganisation. The first
commit is verifiable by content hash, the second reads as an ordinary rename.
Never combine them.

- [ ] **Step 1: Move the box and point types**

`geometry/point.py` and `geometry/bounding_box.py`, 1,136 lines, plus the
`schemas/_helpers.NUMBER_SCHEMA` constant they need. Seventeen production
modules inside book-tools import `BoundingBox` or `Point`, and seventy more
counting tests; none should change, because `pdomain_book_tools.geometry`
re-exports them. `image_ops.py` stays behind with cv2.

- [ ] **Step 2: Move the typography and matching contracts**

`typography/` at 4,301 lines and `matching/` at 3,732. Note that
`typography/alignment.py`, 812 lines, has no callers inside book-tools at all.
It was built for consumers, which is precisely why it belongs in the contracts
package.

`matching/legacy_projection.py` imports `MatchType` at module level from
`ocr/ground_truth_matching_helpers/`. Move that directory, 74 lines of
stdlib-only enums and character groups, in the same step. Without it the
contracts package either fails its lightness test or depends back on
book-tools, which the architecture forbids.

The same file also references `Block`, `Page` and `Word` under `TYPE_CHECKING`,
and those stay behind. Decide before moving whether to drop the annotations,
narrow them to a protocol, or keep a type-checking-only dependency. A
type-checking-only edge does not break the runtime boundary, but it does mean
the contracts package cannot type-check alone.

- [ ] **Step 3: Move the PGDP readers**

`pgdp/pgdp_results.py` and `pgdp/f2/*`, 2,118 lines. These are two different
formats, not an old and a new version of one thing: the first is a plain-text
export, the second is F2's lossless token format. Both move.

- [ ] **Step 4: Move the remaining value-type seams**

OCR value types at 941 lines, layout contracts at 457, licensing and
miscellaneous at 188.

- [ ] **Step 5: Trim the root `__init__.py`**

This step is what makes the move worth doing. The root eagerly re-exports
`Page`, `Word`, `Block` and `PGDPResults`, so any submodule import loads
cv2, numpy and shapely. Make those lazy through a module-level `__getattr__`,
following the pattern in `pdomain_ocr_training/__init__.py`.

Run: `cd /workspaces/pdomain/pdomain-book-tools && make ci`

Expected: after each step both repositories pass their gates, and after step 5
importing a contract costs no imaging stack.

Rollback proceeds in strict reverse step order. Each move depends on the ones
before it, so reverting an earlier step while a later one stands breaks the
re-export chain rather than restoring it.

## Task 5: Repoint the consumers

**Depends on:** Task 4.

Nine repositories remain after the retirements. Most need no change, because
the re-exports hold.

- [ ] **Step 1: Repoint the repositories that were working around the weight**

`pdomain-pgdp-api-client` depends on the contracts package and deletes its
absolute-path loader. Done on 2026-09-02.

`pdomain-ocr-synth` does **not** delete its 248-line F2 parser. Investigated on
2026-09-02 and rejected: the two parsers do different work.

`src/pdomain_ocr_synth/pgdp/f2.py` takes a mapping of every page at once and
carries block state across page boundaries, so a `/# #/` block opening on one
page and closing several pages later has its body stitched onto each page it
spans. Two tests cover exactly that. The contracts parser takes a single
`page_key` and has no concept of page order, so it would emit an unclosed-block
warning and drop the body instead.

The output shapes differ too. This repo's parser returns raw markup text that
`features.py` runs regexes over and `ranking.py` builds diagnostics from. The
contracts parser returns a decoded `TypographyPageRecord` with graphemes and
resolved style spans. Adopting it means rewriting three callers against a
different contract, which is the redesign this plan's own constraints forbid.

The duplication is real but it is not this plan's to remove. Doing it needs a
decision about whether the contracts parser should grow a document-scoped mode,
and that is separate work.

- [ ] **Step 2: Check dynamic imports**

`pdomain-ocr-cli` and parts of `pdomain-ocr-labeler-spa` reach book-tools
through `importlib.import_module()` with string names, which no static search
finds. Search for import strings, not just import statements.

- [ ] **Step 0: Pin the contracts package to the index in every consumer**

Do this before releasing book-tools, not after. Every consumer declares the
private index with `explicit = true`, which tells uv to use that index only for
packages explicitly pinned to it. Book-tools now depends on
`pdomain-book-contracts`, so the first release carrying that dependency makes
uv look for the contracts package on PyPI, fail to find it, and refuse to
resolve.

Verified on 2026-09-02. The failure is
`Because pdomain-book-contracts was not found in the package registry ...
unsatisfiable`. The fix is one line per consumer under `[tool.uv.sources]`:

```toml
pdomain-book-contracts = { index = "pdomain-index-pip" }
```

Note that `pdomain-source-data` names its index `pdomain` rather than
`pdomain-index-pip`, so match each repo's own name.

Do not fix this by dropping `explicit = true`. That would make uv search the
private index for every package, which invites dependency confusion.

The pin changes no lockfile until book-tools is released, so it is inert when
landed and load-bearing afterwards.

- [ ] **Step 3: Bump the paired contract consumers together**

`pdomain-source-data` and `pdomain-ocr-labeler-spa` are the two ends of the
typography contract and both pin exactly. They move in one coordinated bump.

- [ ] **Step 4: Leave the stale pins alone for now**

Five repositories are lockfile-frozen at 0.21.0 because dependency-refresh
pull requests cannot land, tracked in
`docs/issues/2026-08-08-dep-refresh-cannot-auto-land.md`. They keep working
through the re-exports. Fixing that mechanism is separate work and should not
gate this.

Expected: no consumer loads book-tools by filesystem path, and no consumer
parses F2 itself. Rollback repins the previous versions.

## Follow-up work this plan deliberately excludes

Three items came out of the same investigation but do not belong here. Two are
unrelated to extraction, and the third changes behaviour, which this plan
forbids. They need their own plan.

Delete `pdomain_source_data/geometry/records.py`, which defines `PageGeometry`,
`RecognizedWord` and `RecognizerInfo` while book-tools already exports
`PageGeometry`, `WordGeometry` and `ModelRun` covering the same ground with
coordinate spaces, orientation and transform chains it lacks.

Fold the seed, parse, align, project glue into one entry point. It now exists in
`prepare_labeler`, `prepare_labeler_book`, and `tasks/typography/crops.py`.

Make the alignment acceptance margin mapping-aware. The current rule compares
raw path cost, so a tie in where whitespace falls may read the same as a
wholesale misalignment.

A session measurement on 2026-09-01 reported 57 of 58 pages rejected at margin
0.0 while placing 97.1 percent of tokens, with the two tied paths differing by
0 to 2 tokens. That measurement was not preserved and does not reproduce from
anything in this repository, so treat it as a lead rather than evidence and
measure again before acting. This is a behaviour change and needs its own
evidence, including a deliberately misaligned page proving the new measure
separates error from ambiguity.

## Acceptance criteria

Task 1 passes when both packages produce identical canonical bytes for the same
value, and the compatibility test fails when book-tools is absent.

Task 2 passes when the datasets exist under the data root, verify by content
hash, carry a manifest stating what they lack, and both repositories are
archived with their supersession recorded.

Task 3 and 4 pass when importing any contract loads no imaging stack, every
existing import path still resolves, and both repositories pass their gates
after every step.

Task 5 passes when no consumer loads book-tools by path, none parses F2
itself, and every repository it touches passes its own gate.

The excluded follow-up work has no acceptance criteria here, by design.

## Decisions taken on 2026-09-02

- The canonical `canonical_json_bytes` form is the book-tools one, without a
  trailing newline. Source-data's stored digests must be rebuilt; Task 1 Step 2
  inventories them.
- Module paths are reorganised during the move, with each step landing as a
  verbatim move commit followed by a reorganisation commit.
- Both retired repositories are marked retired in place and moved out of the
  workspace later, once their load-bearing references are repointed.
- The package is named `pdomain-book-contracts`.

The target module layout the reorganisation commits follow is specified in
[the book contracts module layout](../specs/2026-09-02-book-contracts-module-layout.md).

## Human decisions this plan still needs

- Review the module layout before Task 4 lands its first reorganisation commit.
  It is cheap to revise while the package has no consumers and expensive after.
