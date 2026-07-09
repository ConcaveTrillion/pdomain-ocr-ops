# DewarpNet
- Category: dewarp (deep-learning)
- Paper + year: "DewarpNet: Single-Image Document Unwarping With Stacked 3D and 2D Regression Networks", Das et al. — ICCV 2019 (NOT CVPR'18; that was DocUNet)
- Repo / homepage: https://github.com/cvlab-stonybrook/DewarpNet — https://sagniklp.github.io/dewarpnet-webpage/
- Pretrained weights public? Yes — final models + pre-end-to-end models on Google Drive (linked from README). WEIGHTS license: covered by the repo's MIT LICENSE (no separate weight terms).
- Code license: MIT (Copyright 2019 CVLab@StonyBrook).
- Framework / runtime: PyTorch (built on pytorch-semseg). GPU recommended for batch; single-image CPU inference is feasible but slow.
- Maintenance: last substantive update ~Sept 2021 (final models release). Effectively dormant but stable; the Doc3D dataset it introduced is still widely used.

## What it does
Single-image unwarping of a photographed document. Trained on the synthetic **Doc3D** dataset (100k+ renders with full 3D + UV + backward-map ground truth).

## Model / approach
Two stacked stages: a **Shape Network** regresses a dense 3D coordinate map of the document surface; a **Texture Mapping Network** converts that to a 2D backward-mapping (sampling grid) used to resample the input into a flat image. So internally it does produce a dense backward-map (`bm`), though `infer.py` emits the final rectified image. DocUNet benchmark (as later re-measured): MS-SSIM ≈ 0.47, LD ≈ 8.39 — the 2019 baseline that DocTr/DocGeoNet/UVDoc beat.

## Input-regime fit
Trained purely on synthetic phone-photo-style 3D paper distortion (Doc3D). Assumes a curled/folded sheet held in front of a camera. On an already-flat flatbed scan it has no "identity" prior — the shape net will still regress some surface and the resulting backward-map can introduce mild warp/cropping rather than passing the image through. Does NOT degrade gracefully on flat input; needs a guard.

## Even/odd (left vs right page) handling
Single-page assumption. A two-page book spread is out of distribution — the 3D shape net tries to fit one surface across the gutter, typically producing a smeared/incorrect map across both pages. No left/right awareness.

## How it would back our Dewarp protocol
Favourable: the architecture computes a dense backward-map (`bm`, an HxWx2 sampling grid) before texturing. With modest code surgery we can export that grid and apply it with `cv2.remap`, and invert it numerically. No official ONNX export; would need tracing. Weights are two stacked nets (tens of MB). PyTorch + numpy/scipy deps.

## Strengths / weaknesses for book scans
Strengths: permissive MIT (commercial-safe), public weights, the only major model that explicitly exposes a 3D + backward-map intermediate. Weaknesses: oldest/weakest accuracy, single-page only, no flat-input safety, dormant repo, older PyTorch pinning.

## Sources
- https://github.com/cvlab-stonybrook/DewarpNet
- https://github.com/cvlab-stonybrook/DewarpNet/blob/master/LICENSE
- https://openaccess.thecvf.com/content_ICCV_2019/papers/Das_DewarpNet_Single-Image_Document_Unwarping_With_Stacked_3D_and_2D_Regression_ICCV_2019_paper.pdf
- https://sagniklp.github.io/dewarpnet-webpage/
