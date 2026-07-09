# OpenCV ThinPlateSplineShapeTransformer (TPS)
- Category: dewarp (warp-primitive)
- Repo / homepage: https://docs.opencv.org/4.x/dc/d18/classcv_1_1ThinPlateSplineShapeTransformer.html (module: opencv-contrib `shape`)
- License (code; and model weights if any): Apache-2.0 (OpenCV 4.x). No model weights.
- Language / runtime: C++ core with Python bindings. Runs anywhere OpenCV runs.
- Install: `pip install opencv-contrib-python` (the `shape` module is in contrib, not the base `opencv-python`).
- Interface: Library API. `cv2.createThinPlateSplineShapeTransformer(regularizationParameter=0)`, then `estimateTransformation(...)` + `warpImage(...)` / `applyTransformation(...)`.
- Maintenance: Maintained as part of OpenCV's regular release cadence (4.x). Maintained: yes. (Note: it is a generic primitive, not a document tool.)

## What it does
A general-purpose **non-rigid warp primitive**: given matched source/target control-point pairs, it fits a thin-plate spline and can warp an image or transform point sets. It carries no document or text logic — it only realizes a smooth deformation you supply.

## Geometric model / algorithm
Thin-plate spline interpolation (Bookstein 1989, "Principal Warps"). Given N control-point correspondences it minimizes bending energy to produce a globally smooth mapping that interpolates the points (optionally relaxed via the regularization parameter). `warpImage` builds a remap structure by sampling the continuous TPS function and calls `cv2.remap` to interpolate pixel colors.

## Input-regime fit
Regime-agnostic by itself: it will flatten curl, perspective, or arbitrary distortion **if** you provide the right control points. It does not find those points — something else (textline detection, mesh fitting) must supply them. So it handles phone photos, flatbed scans, and spreads only as well as the point-correspondences you feed it.

## Leverages OCR or text-line detection?
No, not on its own. In a document pipeline you would derive control points from detected textlines/baselines (e.g. sampled baseline points mapped to straight horizontal targets) and hand those to TPS.

## Even/odd (left vs right page) handling
No inherent page model. Even/odd handling depends entirely on how the control points are generated upstream; a two-up spread can be warped in one TPS if the control points span both pages, but per-page control sets are cleaner.

## How it would back our Dewarp protocol
Strong fit as the warp engine behind the protocol: `warpImage` internally constructs a dense remap, so map_x/map_y can be produced directly (sample the TPS over the full grid). Forward TPS is not closed-form invertible, but a backward map is what `remap` consumes anyway, and an inverse can be approximated by swapping source/target points. Dependency: opencv-contrib-python only — light. Pairs naturally with a textline-based control-point generator (e.g. derived from our OCR baselines or from Leptonica's disparity).

## Strengths / weaknesses for book scans
Strengths: smooth arbitrary deformation, dense map output, single light dependency, well documented. Weaknesses: needs an external control-point source (it solves no document problem itself); TPS with many control points can be slow and can overfit/ripple; no built-in even/odd or curl logic.

## Sources
- https://docs.opencv.org/4.x/dc/d18/classcv_1_1ThinPlateSplineShapeTransformer.html
- https://docs.opencv.org/3.0-beta/modules/shape/doc/shape_transformers.html
- https://answers.opencv.org/question/121616/how-to-access-thinplatespline-shapetransformer-functions-in-python/
