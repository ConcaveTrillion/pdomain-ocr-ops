---
Status: draft
Owner: CT
Created: 2026-09-02
Last verified: 2026-09-02
Kind: spec
---

# Book Contracts Module Layout

The new package groups its 12,998 lines by what each module is responsible for,
not by which package it happened to live in before.

## Agent Index

- **Kind:** spec
- **Status:** draft
- **Owner:** CT
- **Last verified:** 2026-09-02
- **Read when:** performing the reorganisation commits of the book-contracts extraction, or deciding where a new contract belongs.
- **Search terms:** book contracts layout, module structure, package reorganisation, extraction target.

## Why this exists

The [extraction plan](../plans/2026-09-01-extract-book-contracts-and-retire-pd-repos.md)
lands each move as two commits: the files moved verbatim, then reorganised. The
second commit needs something to reorganise toward. This is it.

Without a target layout, each step would invent one, and the package would end
up with the same accidental shape it has today.

## The layout

```text
pdomain_book_contracts/
    geometry/        point.py, bounding_box.py
    text/            label_normalization.py, text_normalize.py
    typography/      labels.py, spans.py, normalization.py, records.py,
                     annotations.py, exchange.py, book_manifest.py, review.py
    matching/        alignment.py, engine.py, models.py, legacy_projection.py,
                     pgdp_continuations.py, match_type.py, character_groups.py
    ocr/             character.py, glyph_annotations.py, provenance.py,
                     review.py, gt_orphans.py, blob_protocol.py
    layout/          types.py, regions.py
    sources/pgdp/    rounds.py, offsets.py,
                     f2/{tokens,parser,project_rules,warnings}.py
    licensing.py
    _schemas.py
```

## What moved and why

Four changes are deliberate. Everything else keeps its name.

**All alignment lives in `matching/`.** `typography/alignment.py`, 812 lines,
moves beside the matching engine. It aligns two texts, which is what `matching/`
is for, and it currently sits in `typography/` only because it was written for
typography's first consumer. The two stdlib enum modules it depends on,
`match_type.py` and `character_groups.py`, come from `ocr/` for the same reason:
they are matching vocabulary, not OCR results.

**Text transformation gets its own package, but normalization stays put.**
`ocr/text_normalize.py` and `ocr/label_normalization.py` move to `text/`. Both
import nothing but the standard library, so `text/` genuinely has no internal
dependencies.

`typography/normalization.py` stays in `typography/`. An earlier draft of this
spec moved it to `text/` on the grounds that it was not about typography
specifically. That was wrong. It imports `KnowledgeState` and `StyleLabel` from
`typography/labels.py`, and `CanonicalModel`, `StyleSpan` and `split_graphemes`
from `typography/spans.py`, while `typography/records.py` imports
`ComparisonOperation` back from it. Moving it created a genuine import cycle
that failed at run time with a partially initialized module. It is built out of
typography vocabulary, so `typography/` is where it belongs.

**The round container separates from the F2 markup.** `pgdp/f2/offsets.py`
contains no reference to F2 markup at all. It reads the round-JSON container, a
JSON object mapping page keys to page text, and tracks byte offsets into it.
Every PGDP round shares that container; only the markup inside differs.

`pdomain-source-data` already relies on this. It reads P3 with
`read_lexical_f2_index` and `read_lexical_f2_page`, then compares the two rounds
to decode words split across a page break. The functions are named for F2 and
used for P3.

So `offsets.py` moves up beside `rounds.py`, out of `f2/`, and its functions
lose the `f2` in their names. The `f2/` package keeps only what is genuinely
F2-specific: tokens, the markup parser, project rules, and warnings.

There is no `p3.py`. P3 carries no markup, so it needs nothing beyond the shared
container. A module for it would have no contents. A later round parser, or
another source with its own container, plugs in beside `f2/`.

`pgdp_results.py` becomes `rounds.py`, because it reads any round rather than
some thing called a result.

**Two further renames resolve collisions.** `layout/geometry.py` becomes
`layout/regions.py`, because it describes page regions and the name already
means spatial value types one level up. `schemas/_helpers.py` becomes
`_schemas.py` at the package root, since one shared pydantic constant does not
need a package.

`typography/review.py` and `ocr/review.py` keep their names. They are different
things in different packages, and the package prefix distinguishes them.

## Dependency direction

Imports flow one way, top to bottom:

```text
geometry, text, _schemas     no internal dependencies
typography                   depends on geometry, _schemas
matching                     depends on geometry, typography
ocr                          depends on geometry, typography
layout                       depends on geometry
sources/pgdp                 depends on typography
licensing                    no internal dependencies
```

A module may not import from a package below it in that list. The lightness test
in the extraction plan enforces the external boundary; this rule keeps the
internal one honest, and a cycle here means something is in the wrong package.

## What this layout does not solve

`matching/legacy_projection.py` used to refer to `Block`, `Page` and `Word`
under `TYPE_CHECKING`, and those classes stay in `pdomain-book-tools`. Resolved
during the `matching/` step with three module-private structural Protocols, so
the package type-checks alone. The surface stayed narrow: three attributes and
one method for words, three and one for lines, three for pages.

The line and page Protocols are generic in the word type. `Block.remove_item`
accepts `Word | Block` rather than `object`, which no non-generic Protocol
parameter can satisfy. This only surfaced when book-tools type-checked against
the concrete classes; the contracts package's own tests could not catch it.

`geometry/bounding_box.py` keeps three back-compat wrapper methods, `refine`,
`crop_top` and `crop_bottom`, whose implementations need cv2 and stay in
book-tools. The first attempt at the move had them import
`pdomain_book_tools.geometry.image_ops` at call time, which is the forbidden
direction and left the three methods raising `ImportError` for anyone who
installed the contracts package alone.

They now dispatch through a provider registry. `image_ops.py` registers itself
at its own import time, and an unregistered call raises a named error saying
what to install. Registration is in `image_ops.py` rather than in
`pdomain_book_tools/geometry/__init__.py` on purpose: putting it in the package
`__init__` would pull cv2 into every `import pdomain_book_tools.geometry`, which
is the weight Step 5 of the extraction plan exists to remove.

`ocr/ground_truth_matching.py`, 1,297 lines, is a legacy shim superseded by
`matching/engine.py` according to its own docstring. It is not part of this
extraction and stays behind. Retiring it is separate work.

## Verifying a reorganisation commit

Each reorganisation commit follows a verbatim move commit. To check one:

1. Every file present before is present after, under its new path.
2. Line counts match per file. A reorganisation renames and re-imports; it does
   not edit bodies.
3. The only content changes are import statements and `__init__` exports.
4. Both repositories pass their gates.
5. The internal dependency direction above still holds.
