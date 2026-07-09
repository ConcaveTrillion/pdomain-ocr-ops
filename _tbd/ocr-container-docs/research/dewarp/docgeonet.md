# DocGeoNet
- Category: dewarp (deep-learning)
- Paper + year: "Geometric Representation Learning for Document Image Rectification", Feng et al. — ECCV 2022 (arXiv 2210.08161)
- Repo / homepage: https://github.com/fh2019ustc/DocGeoNet
- Pretrained weights public? Yes — Google Drive folder linked from README (put in `model_pretrained/`). WEIGHTS license: same non-commercial terms; commercial use → contact haof@mail.ustc.edu.cn.
- Code license: custom **non-commercial** license (fh2019ustc family; commercial use prohibited without written permission).
- Framework / runtime: PyTorch. GPU recommended; CPU single-image inference feasible.
- Maintenance: part of the actively maintained fh2019ustc family; stable.

## What it does
Single-image geometric rectification that injects explicit document **geometry priors** — 3D shape and textlines — to constrain the predicted unwarping.

## Model / approach
Three parts: a **structure encoder** (predicts 3D shape, global unwarping cue), a **textline extractor** (explicit local geometric constraints from text rows), and a **rectification decoder** that fuses both to regress a dense **backward displacement map** applied via `grid_sample`. Trained on Doc3D. Benchmark scores: DocUNet MS-SSIM 0.5040, LD 7.71; DIR300 MS-SSIM 0.6380, LD 6.40 — among the strongest in this set, particularly on text-dense pages thanks to the textline branch.

## Input-regime fit
Trained on synthetic phone-photo distortion (Doc3D). The textline prior makes it especially suited to text-heavy book pages. But the same priors mean it actively predicts a warp field for any input — on an already-flat scan it can still introduce displacement; no identity passthrough. Guard before applying to clean scans.

## Even/odd (left vs right page) handling
Single-page. The 3D-shape branch assumes one continuous surface; a two-page spread spans two surfaces with a gutter, which is out of distribution and degrades the predicted map across the fold. The textline branch may partially anchor each page's rows but does not split pages. Pre-split at the gutter and feed each page separately.

## How it would back our Dewarp protocol
Good mechanical fit: decoder emits a dense backward map (interceptable for `cv2.remap` + numeric inversion). The textline-anchored geometry should keep book text rows straight, which matters for downstream OCR. No official ONNX; traceable with standard ops. Weights modest (tens of MB). PyTorch deps.

## Strengths / weaknesses for book scans
Strengths: strongest text-line-aware accuracy in this set, dense backward-map output, DIR300 + DocUNet validated, active family. Weaknesses: non-commercial license (commercial blocker), single-page only, no flat-input safety, more moving parts (3 sub-nets) than UVDoc.

## Sources
- https://github.com/fh2019ustc/DocGeoNet
- https://arxiv.org/pdf/2210.08161
- https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136970466.pdf
- https://dl.acm.org/doi/abs/10.1007/978-3-031-19836-6_27
