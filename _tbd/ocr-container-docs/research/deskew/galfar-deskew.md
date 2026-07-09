# galfar/deskew (Marek Mauder)
- Category: deskew (CLI-pipeline)
- Repo / homepage: https://github.com/galfar/deskew — https://galfar.vevb.net/wp/projects/deskew/
- License (code; and model weights if any): Mozilla Public License 2.0 (MPL-2.0); no model weights.
- Language / runtime: Object Pascal (Free Pascal / Lazarus, uses the Imaging library). Ships as a self-contained native binary — no runtime needed.
- Install: download prebuilt binary (Win64/Win32, Linux x86_64, Linux aarch64, Linux ARMv7, macOS x86_64) from the releases page, or build with FPC/Lazarus.
- Interface: CLI (`deskew [options] input.png`); no library API.
- Maintenance: latest 1.33 (2025-06-02); low-frequency but ongoing single-maintainer activity; maintained yes.

## What it does
Standalone command-line deskewer for scanned text documents. Detects the skew angle and writes a rotated output image whose text lines are horizontal. Supports a configurable max angle, background fill color, output format/bit-depth control, and a `-o` output path.

## Algorithm
Hough-transform line detection. The image is thresholded to foreground pixels, edge/feature points are accumulated into Hough (angle, distance) space, and the angle bin with the strongest "text line" response gives the skew. Refinement runs over a bounded angle window (default ±10°, configurable via `-l`). Implemented in `RotationDetector.pas`.

## Input-regime fit
Flatbed scans of text: very good, including larger skews than the projection-profile tools (configurable max angle). Phone photos: limited — rotation only, no perspective/dewarp. Two-up spreads: processed as one image, single global angle.

## Leverages OCR or text-line detection?
Text-line detection via Hough transform, but no OCR — it finds line-like pixel structure, not recognized glyphs.

## Even/odd (left vs right page) handling
Whole-image single-angle only. A divergent two-up spread must be split into left/right images by the caller and deskewed separately; no per-region angle output.

## How it would back our Deskew protocol
Shell-out integration. `apply()` runs `deskew -a <max> -b <bg> -o out.png in.png`. For `estimate()` only, run with verbose/detect output to capture the reported angle (printed to stdout) and skip the write, or run apply and treat it as combined estimate+apply. Returns a rotated image (and a printed angle). Dependency: the bundled native `deskew` binary placed on PATH — no Python/Pascal runtime needed.

## Strengths / weaknesses for book scans
Strengths: zero-dependency static binary, MPL-2.0, handles larger skew angles than profile methods, multi-arch (incl. ARM), good output-format control. Weaknesses: CLI-only (no in-process API → process spawn per page); single global angle (no two-up support); no perspective correction; angle is recovered from stdout rather than a clean structured return.

## Sources
- https://github.com/galfar/deskew
- https://github.com/galfar/deskew/blob/master/Readme.md
- https://github.com/galfar/deskew/blob/master/RotationDetector.pas
- https://galfar.vevb.net/wp/projects/deskew/
