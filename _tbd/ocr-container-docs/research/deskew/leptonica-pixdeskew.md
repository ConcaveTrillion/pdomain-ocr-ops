# Leptonica pixDeskew / pixFindSkewAngle
- Category: deskew (classical)
- Repo / homepage: http://www.leptonica.org/ — https://github.com/DanBloomberg/leptonica
- License (code; and model weights if any): Custom BSD-style permissive ("Leptonica" license, OSI-approved as `Leptonica`); no model weights.
- Language / runtime: C; callable from Python via `leptonica` ctypes wrappers, `tesserocr`, or OCRmyPDF's bundled bindings.
- Install: build from source (`autoconf`/`make`), or via system package (`apt install libleptonica-dev`), Homebrew (`brew install leptonica`), or as a transitive dep of Tesseract.
- Interface: library (C API); `prog/deskew_it.c` is a sample CLI built from source.
- Maintenance: latest 1.85.0 (2024-10-16); active, single-maintainer (Dan Bloomberg); maintained yes.

## What it does
Estimates the dominant skew angle of a binary text image and optionally returns a rotated (deskewed) copy. Top-level entry points: `pixDeskew()`, `pixFindSkew()`, `pixFindSkewAndDeskew()`, `pixDeskewGeneral()`.

## Algorithm
Projection-profile / "variance of line sums" (Postl's method). The image is vertically sheared by a series of trial angles; for each shear, pixel sums are accumulated along raster lines and the variance of those sums is scored. The angle maximizing the differential variance is the skew. Uses a coarse sweep (`pixFindSkewSweep`) followed by a binary search refinement (`pixFindSkewSweepAndSearch`) for sub-degree precision, with a confidence score gate.

## Input-regime fit
Flatbed scans of single-column text: excellent. Phone photos: poor unless dewarped/binarized first (assumes affine skew, not perspective). Two-up spreads: treated as one image — a single global angle, so it cannot separate differing left/right skews.

## Leverages OCR or text-line detection?
No OCR. It relies on the statistical signature of horizontal text rows in the pixel-sum profile, not on detected glyphs or layout.

## Even/odd (left vs right page) handling
Whole-image single-angle only. To handle a two-up spread with divergent page skews, the caller must split the image into left/right halves and run `pixFindSkew` on each independently.

## How it would back our Deskew protocol
`estimate()` would call `pixFindSkew(pix, &angle, &conf)` and return the angle (degrees) plus confidence; low confidence → return 0/identity. `apply()` would call `pixDeskew()` (or `pixRotate` with the cached angle). Dependencies: liblept + a Pix conversion layer (numpy/PIL ↔ Leptonica Pix). Per-side handling requires splitting before estimate.

## Strengths / weaknesses for book scans
Strengths: fast, deterministic, well-proven on scanned print; confidence score lets us skip uncertain pages. Weaknesses: binary-only (binarizes internally, may misjudge low-contrast scans); small angle range in practice; no perspective correction; single global angle unsuitable for raw two-up spreads.

## Sources
- http://www.leptonica.org/
- http://www.leptonica.org/source/version-notes.html
- https://github.com/DanBloomberg/leptonica/blob/master/src/skew.c
- https://tpgit.github.io/Leptonica/skew_8c.html
- https://fossies.org/linux/leptonica/prog/deskew_it.c
