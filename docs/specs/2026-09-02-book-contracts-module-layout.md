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
    text/            normalization.py, label_normalization.py, text_normalize.py
    typography/      labels.py, spans.py, records.py, annotations.py,
                     exchange.py, book_manifest.py, review.py
    matching/        alignment.py, engine.py, models.py, legacy_projection.py,
                     pgdp_continuations.py, match_type.py, character_groups.py
    ocr/             character.py, glyph_annotations.py, provenance.py,
                     review.py, gt_orphans.py, blob_protocol.py
    layout/          types.py, regions.py
    sources/pgdp/    results.py, f2/{tokens,parser,offsets,project_rules,warnings}.py
    licensing.py
    _schemas.py
```

## What moved and why

Three changes are deliberate. Everything else keeps its name.

**All alignment lives in `matching/`.** `typography/alignment.py`, 812 lines,
moves beside the matching engine. It aligns two texts, which is what `matching/`
is for, and it currently sits in `typography/` only because it was written for
typography's first consumer. The two stdlib enum modules it depends on,
`match_type.py` and `character_groups.py`, come from `ocr/` for the same reason:
they are matching vocabulary, not OCR results.

**Text transformation gets its own package.** `typography/normalization.py`
builds the comparison views alignment consumes, and `ocr/text_normalize.py` and
`ocr/label_normalization.py` do related work from a different neighbourhood.
None of them is about typography or OCR results specifically. `matching/`
imports `text/`; the reverse never happens.

**Two renames resolve collisions.** `layout/geometry.py` becomes
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
typography                   depends on geometry, text, _schemas
matching                     depends on geometry, text, typography
ocr                          depends on geometry, typography
layout                       depends on geometry
sources/pgdp                 depends on typography, text
licensing                    no internal dependencies
```

A module may not import from a package below it in that list. The lightness test
in the extraction plan enforces the external boundary; this rule keeps the
internal one honest, and a cycle here means something is in the wrong package.

## What this layout does not solve

`matching/legacy_projection.py` refers to `Block`, `Page` and `Word` under
`TYPE_CHECKING`, and those stay in `pdomain-book-tools`. The runtime boundary
holds, because a type-checking reference imports nothing at run time. The
package still cannot type-check alone until those annotations are dropped,
narrowed to a protocol, or satisfied some other way. Decide that during the
`matching/` step rather than before it.

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
