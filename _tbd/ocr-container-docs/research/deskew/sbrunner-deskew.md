# sbrunner/deskew
- Category: deskew (python-lib)
- Repo / homepage: https://github.com/sbrunner/deskew — PyPI: https://pypi.org/project/deskew/
- License (code; and model weights if any): MIT; no model weights (classical, no ML)
- Language / runtime: Python (pure-Python, >=3.10)
- Install: `pip install deskew` (optional `deskew[debug_images]` for diagnostics)
- Interface: library + CLI (`deskew input.png`, `deskew --output out.png input.png`)
- Maintenance: actively maintained. Latest release 1.6.0 (2026-04-13); 85 releases, frequent commits. Maintained: yes.

## What it does
Estimates the dominant text-line skew angle of a scanned document and (via CLI) rotates the image to correct it. Library form returns just the angle; rotation is left to the caller.

## Algorithm
Hough-line transform on the image edges (scikit-image `hough_line`). It bins detected line angles, scores them by accumulated Hough strength, and returns the most-supported angle. Default search range is -45..+45 degrees; `angle_pm_90=True` extends to +/-90. Depends on numpy + scikit-image.

## Input-regime fit
Best on flatbed scans with strong straight horizontal text lines and clean margins. Phone photos work if reasonably flat (Hough is sensitive to perspective/curl, which it cannot model). Two-up spreads: treated as one image, so a single global angle is returned — poor when the two halves differ.

## Leverages OCR or text-line detection?
No OCR. It works purely from edge/line geometry via the Hough transform; it has no notion of words or text-line segmentation beyond the edge response.

## Even/odd (left vs right page) handling
Whole-image single-angle only. No per-region or per-page-side estimation. To handle a two-up spread with divergent left/right skew you must split the page first, then call `determine_skew` on each half.

## How it would back our Deskew protocol
`estimate()` → call `determine_skew(grayscale_ndarray, angle_pm_90=..., max_angle=...)`, returning a float degrees. `apply()` → rotate with our own `warpAffine`/PIL rotate (the library's CLI does this but the API does not), expanding the canvas to avoid corner clipping. Dependencies: numpy, scikit-image. Clean, lightweight, no GPU.

## Strengths / weaknesses for book scans
Strengths: tiny dependency footprint, deterministic, no model download, well-maintained, simple float-angle output that drops straight into a protocol. Weaknesses: single global angle (no per-side split), Hough cost grows with resolution, degrades on sparse-text or heavily illustrated pages and on perspective/curl from phone photos.

## Sources
- https://github.com/sbrunner/deskew
- https://pypi.org/project/deskew/
- https://github.com/sbrunner/deskew/blob/master/pyproject.toml
