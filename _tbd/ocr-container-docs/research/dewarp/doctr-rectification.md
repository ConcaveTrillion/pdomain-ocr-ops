# DocTr (Document Image Transformer)
- Category: dewarp (deep-learning)
- Paper + year: "DocTr: Document Image Transformer for Geometric Unwarping and Illumination Correction", Feng et al. — ACM MM 2021 (Oral)
- Repo / homepage: https://github.com/fh2019ustc/DocTr
- Pretrained weights public? Yes — GeoTr + IllTr checkpoints on Google Drive / Baidu Cloud (linked from README). WEIGHTS license: same repo non-commercial license below; commercial use requires written permission.
- Code license: custom **non-commercial** license (LICENSE.md). Free for academic/personal/non-profit; commercial use prohibited without permission from Prof. Wengang Zhou / Hao Feng (haof@mail.ustc.edu.cn).
- Framework / runtime: PyTorch. GPU recommended; CPU single-image inference feasible (transformer is moderate size).
- Maintenance: author actively maintains the family (DocTr → DocTr++ → DocGeoNet → DocScanner); repo stable, occasional updates.

## What it does
Two-stage correction: **GeoTr** (geometric unwarping transformer) flattens distortion; **IllTr** (illumination correction transformer) removes shadow/lighting. IllTr is optional and separable from geometry.

## Model / approach
GeoTr extracts CNN features, feeds them through a transformer encoder-decoder, and regresses a dense **backward displacement/flow map** (per-pixel sampling coordinates), applied via `F.grid_sample` to produce the flat image. Trained on Doc3D. DocUNet benchmark: MS-SSIM ≈ 0.51, LD ≈ 7.76 — a clear step over DewarpNet.

## Input-regime fit
Trained on synthetic phone-photo distortion (Doc3D). Assumes a warped single-page photo. On an already-flat flatbed scan GeoTr still predicts a non-identity flow and can inject mild warp; no built-in flat-input passthrough. Needs an upstream guard (e.g. only run when warp is detected) for scan-clean input.

## Even/odd (left vs right page) handling
Single-page only. The fixed-input-resolution transformer (288x288 feature grid) assumes one document fills the frame. A two-page book spread is out of distribution — the predicted flow distorts across the gutter. No left/right page concept.

## How it would back our Dewarp protocol
Strong fit on mechanics: GeoTr's native output IS a dense backward sampling grid. We can intercept it pre-`grid_sample`, convert to a `cv2.remap` map, and invert numerically. No official ONNX, but the transformer traces cleanly to ONNX with standard ops. Weights modest (GeoTr ~tens of MB; IllTr separate). PyTorch + timm-style deps.

## Strengths / weaknesses for book scans
Strengths: dense backward-map output, good accuracy, separable illumination stage, active author. Weaknesses: non-commercial license (blocker for any shipped commercial product — must clear with author), single-page only, no flat-input safety.

## Sources
- https://github.com/fh2019ustc/DocTr
- https://github.com/fh2019ustc/DocTr/blob/main/LICENSE.md
- https://dl.acm.org/doi/10.1145/3474085.3475658 (ACM MM 2021)
- https://github.com/fh2019ustc/Awesome-Document-Image-Rectification
