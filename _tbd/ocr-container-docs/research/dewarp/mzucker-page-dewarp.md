# mzucker/page_dewarp
- Category: dewarp (classical-geometry)
- Repo / homepage: https://github.com/mzucker/page_dewarp (writeup: https://mzucker.github.io/2016/08/15/page-dewarping.html)
- License (code; and model weights if any): MIT. No model weights.
- Language / runtime: Python (originally Python 2; one script). Needs scipy, OpenCV >= 3.0, PIL/Pillow.
- Install: clone the repo; no PyPI package. `python page_dewarp.py IMAGE.jpg`.
- Interface: CLI (single script).
- Maintenance: Original 2016 work; ~19 commits, no tagged releases, no active maintenance. Effectively frozen. Use the lmmx fork for a maintained version.

## What it does
Takes a photo of a curled book/document page, finds text spans, fits a 3D "cubic sheet" surface, and reprojects the page to a flat, deskewed, dewarped result. Also thresholds the output to clean bilevel text.

## Geometric model / algorithm
Models the page as a developable surface (a "cubic sheet"): a plane that bends along the spine, with the cross-curve described by two cubic polynomial coefficients (`alpha`, `beta`) pinned to zero at the page edges. It detects connected-component text "spans", samples keypoints along them, and runs `scipy.optimize` to jointly recover camera pose, focal length, page corners, and the cubic-curve parameters. The fitted surface is sampled to produce remap coordinates passed to `cv2.remap`.

## Input-regime fit
Designed for phone photos of a single page with spine curl plus mild perspective. Corrects both curl and perspective in one optimization. Flatbed scans (little curl) work but are overkill. It assumes a roughly rectangular single page; two-up spreads break the single-cubic-sheet assumption.

## Leverages OCR or text-line detection?
No OCR. It detects text by morphology/connected components to build "spans" of text used as fitting cues; it does not read characters.

## Even/odd (left vs right page) handling
No concept of left/right pages. It fits one cubic sheet to one page. A two-up spread must be pre-split into single pages before dewarping.

## How it would back our Dewarp protocol
Internally builds dense `cv2.remap` coordinate arrays, so a dense backward map (map_x/map_y) is recoverable, but the stock script only emits a rectified+thresholded image. Adapting it to return map_x/map_y requires forking the remap step. Forward model is parametric (invertible in principle). Dependencies: numpy, scipy, OpenCV.

## Strengths / weaknesses for book scans
Strengths: principled 3D model; good on single curled pages from phone photos; tiny dependency set. Weaknesses: unmaintained Py2-era code; brittle parameter tuning; single-page only; thresholding is baked in; no library API.

## Sources
- https://github.com/mzucker/page_dewarp
- https://mzucker.github.io/2016/08/15/page-dewarping.html
- https://github.com/mzucker/page_dewarp/blob/master/README.md
