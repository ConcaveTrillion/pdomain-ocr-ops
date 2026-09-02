---
Status: active
Owner: CT
Created: 2026-09-02
Last verified: 2026-09-02
Kind: handoff
scope: book-contracts-extraction
worktree: /workspaces/pdomain/pdomain-ops
base_commit: "6b6467d0814b7513c49353a9746c032bd6ab7118"
---

# Book Contracts Extraction — Task 4 Complete

## Agent Index

- **Kind:** handoff
- **Status:** active
- **Owner:** CT
- **Last verified:** 2026-09-02
- **Read when:** resuming the book-contracts extraction, or deciding whether to publish the contracts package.
- **Search terms:** book contracts, extraction, task 4, task 5, private index, import weight.

## Goal

Split the light third of `pdomain-book-tools` into `pdomain-book-contracts`,
then repoint consumers and retire the two superseded `pd-` repositories. Plan:
[extraction plan](../plans/2026-09-01-extract-book-contracts-and-retire-pd-repos.md).

## Current state

Tasks 1, 3 and 4 are done. Task 2 and Task 5 are not started. Nothing is pushed.

`pdomain-book-contracts` exists locally with 13 commits and holds every
contract: geometry, text, typography, matching, ocr, layout, sources/pgdp,
licensing and `_schemas`. `pdomain-book-tools` re-exports all of them from
their old paths, so no consumer has changed yet.

Both gates are green. Book-tools runs 2,918 passed and 5 xfailed at 89.84%
coverage with a clean typechecker. Contracts runs 12 tests, builds, and passes
`docgraph check --strict`.

Importing a pure contract through book-tools no longer loads cv2. Measured cold,
it went from about 330ms to about 250ms. Importing the same contract straight
from `pdomain_book_contracts` costs about 170ms.

## What blocks Task 5

`pdomain-book-contracts` is not published to the private package index at
`https://pdomain.github.io/pdomain-index-pip/simple/`. Book-tools currently
depends on it through an editable local path in `[tool.uv.sources]`.

That is fine on this machine and broken everywhere else. Book-tools cannot be
published as it stands, and no consumer can repoint at the contracts package
until it is on the index. Publish it before starting Task 5.

## Decisions taken while executing

The layout spec was corrected twice against the code, in `3f1b53e` and
`43615bc`. Three of its dependency-table rows were wrong and `normalization.py`
was assigned to the wrong package, which produced a real import cycle. Every row
in that table is now measured rather than predicted.

`BoundingBox`'s three cv2-backed wrapper methods dispatch through a provider
registry. `image_ops.py` registers itself at its own import time. Registration
is deliberately not in `pdomain_book_tools/geometry/__init__.py`, because that
would pull cv2 into every `import pdomain_book_tools.geometry`.

`legacy_projection.py`'s references to `Page`, `Block` and `Word` are
structural Protocols, generic in the word type because `Block.remove_item`
accepts `Word | Block` rather than `object`.

`licenses.py` reads a vendored `spdx_licenses.json` at import time. The plan's
seam table counted only `.py` files, so that data file was invisible in it. It
moved with the module and book-tools' copy was deleted.

## Resume steps

1. Decide whether to publish `pdomain-book-contracts` to the private index. Task
   5 cannot start until you do, and book-tools cannot ship in the meantime.
2. Then Task 5: repoint `pdomain-ocr-synth` and `pdomain-pgdp-api-client`, check
   the `importlib.import_module()` string imports in `pdomain-ocr-cli` and
   `pdomain-ocr-labeler-spa`, and bump `pdomain-source-data` and
   `pdomain-ocr-labeler-spa` together.
3. Task 2 is independent and can run at any time: rescue the training data, then
   retire the `pd-` repositories.

## Pointers

- [extraction plan](../plans/2026-09-01-extract-book-contracts-and-retire-pd-repos.md)
- [module layout spec](../specs/2026-09-02-book-contracts-module-layout.md)
