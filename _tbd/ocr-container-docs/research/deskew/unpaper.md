# unpaper
- Category: deskew (CLI-pipeline)
- Repo / homepage: https://github.com/unpaper/unpaper
- License (code; and model weights if any): GPL-2.0-only; no model weights.
- Language / runtime: C (Meson build); optional ffmpeg/libav for some I/O.
- Install: `apt install unpaper`, `brew install unpaper`, or build from source with Meson/Ninja.
- Interface: CLI (`unpaper [options] input.pnm output.pnm`); no library API. Native input/output is PNM/PBM/PGM/PPM, so callers convert to/from PNG.
- Maintenance: latest 7.0.0 (Meson-build release, ~2022); low activity, open issues/PRs outstanding; maintained loosely / minimally.

## What it does
General post-processor for scanned sheets: removes dark scan edges, filters noise/specks, recenters content, splits two-up sheets, and deskews. Deskew is one stage in a broader cleanup pipeline (the same pipeline OCRmyPDF invokes for `--clean`).

## Algorithm
Mask-based rotation. unpaper first detects rectangular content "masks" on the sheet (mask-detection), then rotates each mask to straighten it. The deskew rotation is applied per detected mask rather than to the raw frame, found by sampling trial rotations and scoring content alignment within the mask region.

## Input-regime fit
Flatbed scans of text/line content: good, especially combined with its edge/noise cleanup. Phone photos: poor — no perspective correction, expects flat scanner geometry. Two-up spreads: a genuine strength — it can split a sheet into multiple sheets and process each independently.

## Leverages OCR or text-line detection?
No OCR. It works from page geometry / mask detection and pixel content, not recognized text.

## Even/odd (left vs right page) handling
Yes — better than the single-angle tools. unpaper can detect multiple content masks (and `--output-pages 2` / sheet-splitting) so a two-up spread is split and each side deskewed independently, yielding a per-side angle rather than one global angle.

## How it would back our Deskew protocol
Shell-out integration. `apply()` runs `unpaper --no-noisefilter ... in.pnm out.pnm` (or with split options for two-up), wrapped in PNG↔PNM conversion. unpaper does not cleanly emit a numeric angle, so `estimate()` is awkward — it is fundamentally an apply-style transformer; we would treat it as combined estimate+apply and infer angle only if needed by diffing. Dependency: the `unpaper` binary on PATH plus a PNM conversion shim. Best used when two-up splitting + cleanup is wanted, not for pure angle estimation.

## Strengths / weaknesses for book scans
Strengths: handles two-up spreads with independent per-side correction; bundles edge/noise/recenter cleanup; already the engine behind OCRmyPDF `--clean`. Weaknesses: GPL-2.0 (copyleft — affects distribution); PNM-only I/O (conversion overhead); no clean angle return; sparse maintenance; no perspective/dewarp.

## Sources
- https://github.com/unpaper/unpaper
- https://github.com/unpaper/unpaper/blob/main/doc/image-processing.md
- https://github.com/unpaper/unpaper/releases
- https://ocrmypdf.readthedocs.io/en/latest/advanced.html
