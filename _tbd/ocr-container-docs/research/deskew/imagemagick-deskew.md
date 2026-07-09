# ImageMagick -deskew
- Category: deskew (CLI-pipeline)
- Repo / homepage: https://imagemagick.org/ — https://github.com/ImageMagick/ImageMagick
- License (code; and model weights if any): ImageMagick License (OSI-approved, near-identical to Apache-2.0); no model weights.
- Language / runtime: C; CLI plus bindings (PHP Imagick, Python Wand, MagickWand C API).
- Install: `apt install imagemagick`, `brew install imagemagick`, or prebuilt binaries; Python via `pip install Wand` (wraps MagickWand).
- Interface: CLI (`magick ... -deskew`) and library (MagickWand / Imagick `deskewImage`).
- Maintenance: latest 7.1.2-24 (2025); very active, frequent point releases; maintained yes.

## What it does
Straightens an image scanned or photographed at a slight angle. `-deskew {threshold}%` detects the skew angle, rotates the image to correct it, and records the angle in the `deskew:angle` artifact (readable via `%[deskew:angle]`). Optional `-set option:deskew:auto-crop true` trims the resulting border.

## Algorithm
Projection-profile based. The image is binarized against the supplied threshold (e.g. `40%`), then candidate rotation angles are scored by the peakedness/variance of horizontal pixel-count profiles; the angle giving the sharpest row separation wins. Effective only for small skews (roughly ±5°).

## Input-regime fit
Flatbed scans of text: good for small angles. Phone photos: poor — affine rotation only, no perspective/dewarp, and threshold binarization struggles with uneven lighting. Two-up spreads: handled as one frame, single global angle.

## Leverages OCR or text-line detection?
No OCR. Pure pixel-statistics on a thresholded raster; the threshold percentage tunes what counts as foreground text.

## Even/odd (left vs right page) handling
Whole-image single-angle only. A two-up spread would need to be `-crop`-split into halves and each half deskewed separately; ImageMagick offers no per-region angle.

## How it would back our Deskew protocol
Two integration styles. (1) Shell out: run `magick in.png -deskew 40% -set option:deskew:auto-crop true out.png` and parse `deskew:angle` for `estimate()`; `apply()` reuses the rotated output. (2) In-process via Wand: `img.deskew(threshold)` then read `img.artifacts['deskew:angle']`. Returns both an angle and a rotated image. Dependency: system ImageMagick (+ Wand for Python).

## Strengths / weaknesses for book scans
Strengths: ubiquitous, trivial to invoke, fast, gives an explicit angle artifact, optional auto-crop. Weaknesses: small-angle ceiling (~5°); binarization threshold is a tuning knob that can misfire on low-contrast or illustrated pages; single global angle (no two-up support); no perspective correction.

## Sources
- https://imagemagick.org/script/command-line-options.php
- https://imagemagick.org/license/
- https://github.com/ImageMagick/ImageMagick/releases
- https://www.php.net/manual/en/imagick.deskewimage.php
- https://github.com/ImageMagick/ImageMagick/discussions/6063
