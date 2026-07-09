# jdeskew (phamquiluan)
- Category: deskew (python-lib)
- Repo / homepage: https://github.com/phamquiluan/jdeskew — PyPI: https://pypi.org/project/jdeskew/
- License (code; and model weights if any): MIT; no model weights (signal-processing, no ML)
- Language / runtime: Python; numpy + opencv-python-headless
- Install: `pip install jdeskew` (Docker image and REST/Cog wrapper also published)
- Interface: library (`from jdeskew.estimator import get_angle`, `from jdeskew.utility import rotate`); Docker REST endpoint; no first-class CLI
- Maintenance: maintained. Latest release v0.3.0 (2025-05-14); CI in place. Maintained: yes.

## What it does
Estimates the dominant skew angle of a document image and provides a `rotate` helper to correct it. Implements the ICIP 2022 paper "Adaptive Radial Projection on Fourier Magnitude Spectrum for Document Image Skew Estimation."

## Algorithm
Takes the 2D Discrete Fourier Transform of the page; the magnitude spectrum shows energy concentrated along the direction perpendicular to text lines. An adaptive radial projection over the magnitude spectrum finds the angle that maximizes projected energy, yielding the skew. Frequency-domain, so it is robust to text density and does not need explicit line detection.

## Input-regime fit
Strong on flatbed scans and clean document images; evaluated on DISE 2021 with angles up to 45 degrees. Phone photos: tolerant of noise/text-sparsity but, like all global-angle methods, cannot model perspective or page curl. Two-up spreads: a single spectrum → single global angle, so divergent left/right skew is not resolved.

## Leverages OCR or text-line detection?
No. Operates entirely in the Fourier magnitude domain; no OCR, no per-line segmentation.

## Even/odd (left vs right page) handling
Whole-image single-angle only. No per-side support. A two-up spread must be split before estimation to get distinct left/right angles.

## How it would back our Deskew protocol
`estimate()` → `get_angle(image)` returns float degrees. `apply()` → `rotate(image, angle)` (OpenCV warpAffine under the hood). Dependencies: numpy, opencv-python-headless — light, CPU-only, no model download. Note the angle convention/range from the paper (~+/-45); clamp/validate before rotating.

## Strengths / weaknesses for book scans
Strengths: robust to sparse or noisy text because it uses global frequency content; small deps; permissive license; published, peer-reviewed method. Weaknesses: global single angle (no per-side split); FFT cost on large pages; magnitude spectrum can be skewed by strong non-text periodic structure (halftone images, ruled tables).

## Sources
- https://github.com/phamquiluan/jdeskew
- https://pypi.org/project/jdeskew/
- https://ieeexplore.ieee.org/document/9897910/
