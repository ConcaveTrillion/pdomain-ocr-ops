# docTR (mindee) page-straightening
- Category: deskew (OCR-engine-feature)
- Repo / homepage: https://github.com/mindee/doctr — PyPI: `python-doctr`
- License (code; and model weights if any): Apache 2.0 (code and the published model weights)
- Language / runtime: Python; PyTorch (or TensorFlow) backend; GPU optional
- Install: `pip install python-doctr[torch]`
- Interface: library (`ocr_predictor(...)`)
- Maintenance: actively maintained. Latest release 1.0.1 (2026-02-04); 1.0.0 (2025-07-09). Maintained: yes.

## NOT the DocTr dewarp transformer
This is docTR, Mindee's OCR library. It is NOT "DocTr" the document-image-dewarping transformer (that one removes page curl/warp and is documented separately under `dewarp/`). Here we borrow only docTR's in-plane page-rotation straightening — a rigid rotation, not a warp/unwarp.

## What it does
As part of OCR, docTR can estimate a page's overall rotation and rotate it upright before detection, improving results on rotated/skewed pages. Controlled by two `ocr_predictor` flags.

## Algorithm
With `assume_straight_pages=False`, the detection model fits rotated (oriented) boxes. With `straighten_pages=True`, docTR estimates the page's general orientation from the median text-line orientation of the segmentation map, rotates the whole page, then re-runs detection. There are also tiny classifier models — `mobilenet_v3_small_page_orientation` and `..._crop_orientation` — for page/crop orientation.

## Input-regime fit
Tuned for page-uniform rotation on document images (flatbed scans, clean photos). The straightening is a single global rigid rotation; it does not correct perspective or curl. Two-up spreads: one orientation for the whole image — divergent left/right skew is not handled.

## Leverages OCR or text-line detection?
Yes, directly. The angle comes from the deep-learning text-detection segmentation map (median text-line orientation) — it is fundamentally text-line-driven, unlike the classical Hough/Fourier libs.

## Even/odd (left vs right page) handling
Whole-image single-angle only ("page-uniform rotations"). No per-side estimation. Split the spread before the predictor for independent left/right angles.

## How it would back our Deskew protocol
Two paths. (1) Cheap angle-only: run `mobilenet_v3_small_page_orientation` to get a page-orientation class/angle for `estimate()`, then rotate ourselves. (2) Full: `ocr_predictor(assume_straight_pages=False, straighten_pages=True)` straightens internally and also returns oriented boxes we could reuse. Dependencies: python-doctr + a torch/TF backend (heavy; downloads weights; GPU helps). Best when we already run docTR for OCR — straightening comes nearly free and reuses the detection pass.

## Strengths / weaknesses for book scans
Strengths: text-aware angle robust to non-text clutter; reuses an OCR pass we may already run; well-maintained, Apache 2.0 weights. Weaknesses: heavy dependency (torch/TF + model download, GPU desirable); single global angle; overkill if OCR is not otherwise in the pipeline.

## Sources
- https://github.com/mindee/doctr
- https://github.com/mindee/doctr/discussions/1642
- https://mindee.github.io/doctr/latest/using_doctr/using_models.html
- https://github.com/mindee/doctr/releases
