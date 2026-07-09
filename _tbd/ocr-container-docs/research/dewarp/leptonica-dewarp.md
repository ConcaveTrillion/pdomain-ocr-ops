# Leptonica dewarp.c (textline-disparity model)
- Category: dewarp (classical-geometry)
- Repo / homepage: https://github.com/DanBloomberg/leptonica (src/dewarp*.c; docs: https://tpgit.github.io/UnOfficialLeptDocs/leptonica/dewarping.html)
- License (code; and model weights if any): BSD-style (Leptonica 2-clause). No model weights.
- Language / runtime: C library. Python via wrappers (e.g. pyleptonica/leptonica bindings); also reachable through Tesseract, which embeds Leptonica.
- Install: build Leptonica from source or `apt install libleptonica-dev`; call `dewarp*` C API.
- Interface: C library (no standalone CLI; functions like `dewarpBuildPageModel`, `dewarpaApplyDisparity`).
- Maintenance: Actively maintained (Tesseract's image backend). Regular releases; Dan Bloomberg / community. Maintained: yes.

## What it does
Dewarps scanned book pages so textlines become horizontal and straight. Builds per-page disparity arrays from detected textlines and applies them to flatten the image. A multi-page model can share/extrapolate disparity across a book.

## Geometric model / algorithm
Detects long textlines, fits a least-squares quadratic to each line's vertical center, then builds a **vertical disparity** array: each textline is flattened to a reference y, samples are smoothed by a second quadratic fit in the vertical direction, and the sparse grid is interpolated to a full-resolution map that makes all textlines horizontal. A **horizontal disparity** model H(x,y)=H(x) (independent of y) is derived from the difference in vertical disparity at the top vs bottom of the page, correcting left/right line-end stretch. Both arrays are dense 2D maps applied per-pixel.

## Input-regime fit
Tuned for flatbed/overhead **scanned book pages** with curl near the spine. Corrects curl (vertical disparity) and in-plane horizontal stretch; it is not a full perspective/projective corrector — it assumes a near-frontal scan, not an oblique phone photo. Needs enough long textlines to fit.

## Leverages OCR or text-line detection?
Yes — it is fundamentally textline-driven. It estimates textline centers (no character recognition), so it depends on reasonably dense body text to build the model.

## Even/odd (left vs right page) handling
Explicitly even/odd aware: the horizontal disparity is referenced to the **minimum** line-end values for even pages and the **maximum** for odd pages, so left-hand and right-hand pages are handled with the correct sense. It still models one page at a time; a two-up spread should be split, with each half tagged even/odd.

## How it would back our Dewarp protocol
Produces dense backward disparity arrays (effectively map_x/map_y) before warping — a near-ideal fit for a map-based Dewarp protocol. Maps can be cached and re-applied; invertible to the limits of interpolation. Dependency cost is a C library link (or Python binding), heavier than pure-Python OpenCV options.

## Strengths / weaknesses for book scans
Strengths: mature, battle-tested (Tesseract), produces dense maps, even/odd aware, no external model. Weaknesses: needs dense textlines; not for strong perspective/oblique photos; C-binding integration overhead; tuning via many parameters.

## Sources
- https://tpgit.github.io/UnOfficialLeptDocs/leptonica/dewarping.html
- https://github.com/DanBloomberg/leptonica/blob/master/src/dewarp.h
- https://tpgit.github.io/Leptonica/dewarp_8c.html
