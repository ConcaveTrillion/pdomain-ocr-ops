# Alyn (kakul)
- Category: deskew (python-lib)
- Repo / homepage: https://github.com/kakul/Alyn
- License (code; and model weights if any): MIT; no model weights (classical, no ML)
- Language / runtime: Python; numpy, scipy, scikit-image, matplotlib. Originally Python 2 — Python 3 support exists only via an unmerged community PR (ralic PR #5, 2017).
- Install: clone the repo (PyPI presence is stale/unreliable); run the scripts directly
- Interface: library (`SkewDetect`, `Deskew` classes) + CLI scripts (`skew_detect.py`, `deskew.py`)
- Maintenance: unmaintained. ~22 commits total, last meaningful activity 2017; open Python-3 PR never merged. Maintained: no.

## What it does
Detects the text skew angle of an image (`SkewDetect`) and writes a corrected image (`Deskew`). CLI supports single-file and batch (`-b`) modes, optional Hough plotting, and tunable Gaussian `sigma` (`-s`) and Hough peak count (`-n`).

## Algorithm
Canny edge detection followed by the (straight) Hough transform; collects the top-N Hough peaks, derives candidate line angles, and aggregates them (mean/median grouping) to a single skew estimate. `Deskew` then rotates by that angle.

## Input-regime fit
Reasonable on clean flatbed scans with prominent straight text lines. Phone photos: weak — Canny+Hough is sensitive to noise, lighting, perspective, and curl. Two-up spreads: single global angle, no awareness of two columns. Notably, GitHub issues report incorrect deskewing on some inputs, so output should be validated.

## Leverages OCR or text-line detection?
No OCR. Edge + Hough geometry only; no text-line segmentation beyond Hough peaks.

## Even/odd (left vs right page) handling
Whole-image single-angle only. No per-region/per-side estimation. Two-up spreads with divergent skew require manual splitting upstream.

## How it would back our Deskew protocol
`estimate()` → instantiate `SkewDetect(input_file=...)` and read the estimated angle from its result dict. `apply()` → `Deskew(...).run()` or reuse the angle with our own rotate. Caveats: Python-2-era code needs the Py3 patches vendored in; heavier dep chain (scipy + scikit-image + matplotlib) than sbrunner/deskew, which was explicitly written as Alyn's better-maintained successor. Given the lack of maintenance, prefer sbrunner/deskew unless a specific Alyn behavior is required.

## Strengths / weaknesses for book scans
Strengths: simple, transparent classical pipeline; batch mode built in. Weaknesses: unmaintained, Python-2 baseline, known accuracy issues, heavy deps, single global angle, matplotlib pulled in for plotting. Effectively superseded by sbrunner/deskew.

## Sources
- https://github.com/kakul/Alyn
- https://github.com/kakul/Alyn/pull/5
- https://github.com/kakul/Alyn/issues/4
