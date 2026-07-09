# OpenCV DIY deskew
- Category: deskew (DIY)
- Repo / homepage: https://docs.opencv.org/ (no dedicated project — composed from OpenCV primitives)
- License (code; and model weights if any): OpenCV is Apache 2.0 (was BSD pre-4.5); our DIY code is ours. No model weights.
- Language / runtime: Python (cv2) or C++; numpy
- Install: `pip install opencv-python-headless numpy`
- Interface: library (we write the function)
- Maintenance: OpenCV actively maintained; the DIY pipeline is code we own and maintain.

## What it does
A hand-rolled skew estimator built from OpenCV primitives. Several interchangeable strategies, all producing a single rotation angle that `cv2.warpAffine` then corrects.

## Algorithm
Common preprocessing: grayscale, Gaussian blur, Otsu threshold, morphological dilation to merge glyphs into text-line blobs. Then one of:
- minAreaRect: dilate text into one mask, `cv2.minAreaRect` over the foreground, take its rotation (mind the [-90,0) convention).
- HoughLines: `cv2.HoughLines`/`HoughLinesP` on edges; aggregate near-horizontal line angles.
- Projection-profile variance: rotate over candidate angles, sum pixels per row; the angle maximizing row-sum variance (sharpest peaks/troughs) is the skew.
- Radon transform: equivalent to projection-profile, computed via the Radon transform; angle of max projected energy.

## Input-regime fit
Flatbed scans: all four strategies work well with tuning. Phone photos: only as good as preprocessing; none model perspective or curl. Two-up spreads: a single global angle unless we split the page ourselves first.

## Leverages OCR or text-line detection?
No OCR. Uses morphology/edge geometry as a proxy for text lines. We can optionally feed it OCR word boxes (e.g. from docTR/Tesseract) to drive minAreaRect on text regions only.

## Even/odd (left vs right page) handling
Whatever we build. The natural DIY win: split the spread at the gutter (valley in the vertical projection profile), then run any strategy per half → independent left/right angles. This is the main reason to own the pipeline rather than vendor a single-angle library.

## How it would back our Deskew protocol
`estimate()` → preprocess + chosen strategy → float degrees (optionally per-region). `apply()` → `cv2.warpAffine` with an expanded canvas to avoid clipping. Dependencies: opencv-python-headless, numpy only. Full control over angle range, per-side handling, and confidence reporting.

## Strengths / weaknesses for book scans
Strengths: total control, per-page-side splitting, no model download, cheap deps, can fuse with OCR boxes. Weaknesses: we own the tuning and edge cases (illustrations, sparse text, borders fool minAreaRect; projection-profile is O(angles x rotations) so slower). More upfront engineering than dropping in deskew/jdeskew.

## Sources
- https://pyimagesearch.com/2017/02/20/text-skew-correction-opencv-python/
- https://www.dynamsoft.com/codepool/deskew-scanned-document.html
- https://felix.abecassis.me/2011/10/opencv-rotation-deskewing/
- https://docs.opencv.org/
