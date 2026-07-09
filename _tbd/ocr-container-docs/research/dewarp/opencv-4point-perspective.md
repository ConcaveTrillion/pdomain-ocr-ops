# OpenCV 4-point perspective "document scanner"
- Category: dewarp (perspective-only)
- Repo / homepage: https://docs.opencv.org/4.x/da/d54/group__imgproc__transform.html (canonical tutorial: https://pyimagesearch.com/2014/08/25/4-point-opencv-getperspective-transform-example/)
- License (code; and model weights if any): Apache-2.0 (OpenCV). No model weights. (It is a technique built from base OpenCV functions, not a separate package.)
- Language / runtime: Any OpenCV runtime; commonly Python.
- Install: `pip install opencv-python` (base module; no contrib needed).
- Interface: Library functions — `cv2.getPerspectiveTransform(src4, dst4)` then `cv2.warpPerspective(img, M, size)`. Often wrapped in a `four_point_transform()` helper.
- Maintenance: Core OpenCV, fully maintained. The "document scanner" recipe itself is a stable, widely copied pattern. Maintained: yes.

## What it does
Given the four corner points of a quadrilateral document region, computes the homography that maps them to a rectangle and warps the image to a top-down ("birds-eye") fronto-parallel view. The classic phone "scan this receipt/page" rectifier.

## Geometric model / algorithm
Pure projective transform. Four point correspondences fully determine a 3x3 homography (`getPerspectiveTransform`). `warpPerspective` applies it. Corner detection is separate (edge detection + contour approximation, or manual/UI corner picking); the transform itself is exact and parameter-free.

## Input-regime fit
For **flat documents under perspective** — phone photos of a flat page, receipt, card. Corrects perspective only; it CANNOT remove page curl (a homography is planar by construction). Flatbed scans need no perspective fix. On a curled book page it straightens the outer quad but leaves the bowed interior textlines warped.

## Leverages OCR or text-line detection?
No. Corner finding is geometric (contours/edges) or manual. No text awareness.

## Even/odd (left vs right page) handling
No page model. One quad → one rectangle. A two-up spread would be rectified as a single flat quad, ignoring the spine; for per-page results you must detect two quads (split first) and transform each.

## How it would back our Dewarp protocol
Yields a single 3x3 homography. To satisfy a dense map_x/map_y protocol, expand it to a full grid (sample warpPerspective coordinates). Perfectly invertible (matrix inverse / `WARP_INVERSE_MAP`). Lightest possible dependency (base OpenCV). But perspective-only — it can serve as the corner-rectification front stage of a two-stage dewarper (perspective then curl), never the curl corrector.

## Strengths / weaknesses for book scans
Strengths: trivial, exact, fast, invertible, zero extra deps, ubiquitous. Weaknesses: no curl correction; depends on reliable 4-corner detection; single flat plane only; poor on bound spreads without splitting.

## Sources
- https://pyimagesearch.com/2014/08/25/4-point-opencv-getperspective-transform-example/
- https://docs.opencv.org/4.x/da/d54/group__imgproc__transform.html
- https://docs.opencv.org/4.x/da/d6e/tutorial_py_geometric_transformations.html
