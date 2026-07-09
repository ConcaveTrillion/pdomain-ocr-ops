# lmmx/page-dewarp
- Category: dewarp (classical-geometry)
- Repo / homepage: https://github.com/lmmx/page-dewarp (PyPI: https://pypi.org/project/page-dewarp/, docs: https://page-dewarp.vercel.app/)
- License (code; and model weights if any): MIT. No model weights.
- Language / runtime: Python >= 3.10 (supports 3.10-3.14). Depends on numpy, scipy, OpenCV.
- Install: `pip install page-dewarp`. CLI entry point `page-dewarp`.
- Interface: CLI plus an importable library (modularized from the original single script).
- Maintenance: Actively maintained. Latest release 0.3.4 on 2026-05-12, with frequent 2025-2026 releases. PyPI classifies it "Mature". Maintained by Louis Maddox (lmmx).

## What it does
A packaged, modernized rewrite of mzucker/page_dewarp. Same goal: take a curled-page photo, fit a cubic-sheet surface, and emit a flattened, optionally thresholded page. Restructured into modules with a real CLI and config options.

## Geometric model / algorithm
Identical "cubic sheet" model to mzucker's: detect text spans, sample keypoints, and `scipy.optimize` to recover camera pose, focal length, page corners, and the two cubic curl coefficients pinned at the edges. The fitted developable surface is sampled into `cv2.remap` coordinates.

## Input-regime fit
Best on phone photos of single curled pages; corrects both spine curl and perspective. Flatbed scans work but gain little. A single rectangular page is assumed; two-up spreads violate the single-sheet model.

## Leverages OCR or text-line detection?
No OCR. Uses morphological text-span detection as fitting cues only.

## Even/odd (left vs right page) handling
No left/right page modeling. One cubic sheet per page. Two-up spreads must be split first.

## How it would back our Dewarp protocol
Same internals as the original: dense `cv2.remap` arrays exist under the hood. The public API/CLI currently returns rectified images, but because it is a clean, importable package with separated modules, exposing map_x/map_y (or computing them from the fitted surface) is far more tractable than in mzucker's monolith. Parametric forward model, invertible in principle. Pure-Python deps (numpy/scipy/OpenCV) make it the most integration-friendly cubic-sheet option.

## Strengths / weaknesses for book scans
Strengths: maintained, pip-installable, modular, current Python; same proven algorithm. Weaknesses: still single-page only; still needs a span/threshold-friendly page; the cubic-sheet fit can fail on heavy curl or sparse text; map extraction needs minor adaptation.

## Sources
- https://github.com/lmmx/page-dewarp
- https://pypi.org/project/page-dewarp/
- https://libraries.io/pypi/page-dewarp
